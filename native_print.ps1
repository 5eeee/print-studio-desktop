param([Parameter(Mandatory=$true)][string]$Request)
$ErrorActionPreference='Stop'
Add-Type -AssemblyName ReachFramework
Add-Type -AssemblyName System.Printing
Add-Type -AssemblyName PresentationFramework
Add-Type -AssemblyName WindowsBase
$config=Get-Content -LiteralPath $Request -Raw -Encoding UTF8 | ConvertFrom-Json
$resultPath=Join-Path (Split-Path -Parent $Request) 'result.json'
$utf8=New-Object System.Text.UTF8Encoding($false)
function Save-Result($value) { [IO.File]::WriteAllText($resultPath,($value | ConvertTo-Json -Depth 20),$utf8) }
function Ticket-Xml($ticket) {
    $stream=$ticket.GetXmlStream(); $reader=New-Object IO.StreamReader($stream)
    try { return [xml]$reader.ReadToEnd() } finally { $reader.Dispose(); $stream.Dispose() }
}
function Ns-Manager($xml) {
    $ns=New-Object Xml.XmlNamespaceManager($xml.NameTable)
    $ns.AddNamespace('psf','http://schemas.microsoft.com/windows/2003/08/printing/printschemaframework')
    return ,$ns
}
function QName-Key($node,$attribute) {
    $value=$node.GetAttribute($attribute); $parts=$value.Split(':')
    if ($parts.Count -eq 2) { return '{'+$node.GetNamespaceOfPrefix($parts[0])+'}'+$parts[1] }
    return '{}'+$value
}
function Features($xml) {
    $ns=Ns-Manager $xml
    $list=@()
    foreach($feature in $xml.SelectNodes('//psf:Feature',$ns)) {
        $options=@()
        foreach($option in $feature.SelectNodes('./psf:Option',$ns)) {
            $properties=@{}
            foreach($prop in $option.SelectNodes('./psf:ScoredProperty',$ns)) {
                $v=$prop.SelectSingleNode('./psf:Value',$ns)
                if($v) { $properties[(QName-Key $prop 'name')]=$v.InnerText }
            }
            $options+=@{key=(QName-Key $option 'name'); properties=$properties}
        }
        $list+=@{key=(QName-Key $feature 'name'); options=$options}
    }
    return ,$list
}
function Select-Option($capXml,$ticketXml,$featureLocal,$optionLocal) {
    $ns=Ns-Manager $capXml
    $matches=@($capXml.SelectNodes('//psf:Feature',$ns) | Where-Object { (QName-Key $_ 'name').EndsWith('}'+$featureLocal) })
    if($matches.Count -ne 1) { throw "Driver does not expose an unambiguous feature: $featureLocal" }
    $feature=$matches[0]
    $options=@($feature.SelectNodes('./psf:Option',$ns) | Where-Object { (QName-Key $_ 'name').EndsWith('}'+$optionLocal) })
    if($options.Count -ne 1) { throw "Driver does not expose option: $featureLocal / $optionLocal" }
    $tns=Ns-Manager $ticketXml
    foreach($old in @($ticketXml.SelectNodes('//psf:Feature',$tns))) {
        if((QName-Key $old 'name') -eq (QName-Key $feature 'name')) { $null=$old.ParentNode.RemoveChild($old) }
    }
    # Copy all namespace declarations because private Xerox option QNames use vendor prefixes.
    foreach($attribute in $capXml.DocumentElement.Attributes) {
        if($attribute.Prefix -eq 'xmlns' -or $attribute.Name -eq 'xmlns') {
            if(-not $ticketXml.DocumentElement.HasAttribute($attribute.Name)) { $ticketXml.DocumentElement.SetAttribute($attribute.Name,$attribute.Value) }
            elseif($ticketXml.DocumentElement.GetAttribute($attribute.Name) -ne $attribute.Value) { throw 'Namespace prefix collision in driver capabilities' }
        }
    }
    $copy=$ticketXml.CreateElement('psf','Feature',$feature.NamespaceURI)
    $copy.SetAttribute('name',$feature.GetAttribute('name'))
    $null=$copy.AppendChild($ticketXml.ImportNode($options[0],$true))
    $null=$ticketXml.DocumentElement.AppendChild($copy)
    return @{feature=(QName-Key $feature 'name'); option=(QName-Key $options[0] 'name')}
}
function Has-Selection($xml,$selection) {
    $ns=Ns-Manager $xml
    foreach($f in $xml.SelectNodes('//psf:Feature',$ns)) {
        if((QName-Key $f 'name') -eq $selection.feature) {
            foreach($o in $f.SelectNodes('./psf:Option',$ns)) { if((QName-Key $o 'name') -eq $selection.option) { return $true } }
        }
    }
    return $false
}
try {
    $server=New-Object System.Printing.LocalPrintServer
    $queue=$server.GetPrintQueue([string]$config.queue)
    $base=$queue.UserPrintTicket
    if(-not $base) { $base=$queue.DefaultPrintTicket }
    $stream=$queue.GetPrintCapabilitiesAsXml($base)
    $reader=New-Object IO.StreamReader($stream)
    try { $capXml=[xml]$reader.ReadToEnd() } finally { $reader.Dispose(); $stream.Dispose() }
    $report=@{ok=$false; queue=$queue.Name; features=(Features $capXml); message=''}
    if($config.action -eq 'scan') {
        $report.ok=$true; $report.message='Capabilities read; no documents or private ticket payloads exported.'; Save-Result $report; exit 0
    }
    if($queue.QueueDriver.Name -notmatch 'C7000.*V4 PS') { throw 'Automatic mode requires Xerox VersaLink C7000 V4 PS.' }
    if($config.media -eq 'glossy170' -and [int]$config.duplex -ne 0) { throw '170 gsm glossy cannot use automatic duplex on C7000.' }
    $ticketXml=Ticket-Xml $base
    $mediaOption=if($config.media -eq 'glossy170') { 'cardstock-glossy' } else { 'Plain' }
    $mediaSelection=Select-Option $capXml $ticketXml 'PageMediaType' $mediaOption
    # Enhanced is vendor-specific in some Xerox releases. Never treat High, Auto,
    # opaque blobs or a UI label as proof that Xerox Enhanced was selected.
    $qualitySelection=Select-Option $capXml $ticketXml 'PageOutputQuality' 'Enhanced'
    $buffer=New-Object IO.MemoryStream
    $bytes=$utf8.GetBytes($ticketXml.OuterXml); $buffer.Write($bytes,0,$bytes.Length); $buffer.Position=0
    try { $ticket=New-Object System.Printing.PrintTicket($buffer) } finally { $buffer.Dispose() }
    $ticket.PageResolution=New-Object System.Printing.PageResolution(1200,2400)
    $ticket.PageMediaSize=New-Object System.Printing.PageMediaSize([double]$config.width*96/25.4,[double]$config.height*96/25.4)
    $ticket.PageOrientation=[System.Printing.PageOrientation]::Portrait
    $ticket.Duplexing=@([System.Printing.Duplexing]::OneSided,[System.Printing.Duplexing]::TwoSidedLongEdge,[System.Printing.Duplexing]::TwoSidedShortEdge)[[int]$config.duplex]
    $ticket.CopyCount=[int]$config.copies
    $ticket.PageOutputColor=[System.Printing.OutputColor]::Color
    $validation=$queue.MergeAndValidatePrintTicket($base,$ticket)
    $validated=$validation.ValidatedPrintTicket
    $validatedXml=Ticket-Xml $validated
    if(-not (Has-Selection $validatedXml $mediaSelection)) { throw 'Driver substituted the requested media type. Printing stopped.' }
    if(-not (Has-Selection $validatedXml $qualitySelection)) { throw 'Driver substituted Enhanced quality. Printing stopped.' }
    if($validated.PageResolution.X -ne 1200 -or $validated.PageResolution.Y -ne 2400) { throw 'Driver did not retain explicit 1200 x 2400. No silent fallback is allowed.' }
    if($validated.Duplexing -ne $ticket.Duplexing -or $validated.CopyCount -ne $ticket.CopyCount -or $validated.PageOutputColor -ne $ticket.PageOutputColor) { throw 'Driver substituted sides, copies or color. Printing stopped.' }
    if([Math]::Abs($validated.PageMediaSize.Width-$ticket.PageMediaSize.Width) -gt 0.5 -or [Math]::Abs($validated.PageMediaSize.Height-$ticket.PageMediaSize.Height) -gt 0.5) { throw 'Driver substituted sheet dimensions. Printing stopped.' }
    $report.ok=$true; $report.resolution=@{x=1200;y=2400}; $report.media=$mediaSelection; $report.quality=$qualitySelection
    $report.message='Driver retained media, Enhanced, 1200 x 2400, size, sides and copies.'
    if($config.action -eq 'validate') { Save-Result $report; exit 0 }
    if($config.action -ne 'print') { throw 'Unknown action' }
    $xps=New-Object System.Windows.Xps.Packaging.XpsDocument([string]$config.xps,[IO.FileAccess]::Read)
    try {
        $sequence=$xps.GetFixedDocumentSequence()
        $writer=[System.Printing.PrintQueue]::CreateXpsDocumentWriter($queue)
        $writer.Write($sequence,$validated)
    } finally { $xps.Close() }
    $report.message='Job submitted with validated PrintTicket. Physical print quality is not measured by the application.'
    Save-Result $report
} catch {
    if(-not $report) { $report=@{} }
    $report.ok=$false; $report.message=$_.Exception.Message
    Save-Result $report
    exit 1
}
