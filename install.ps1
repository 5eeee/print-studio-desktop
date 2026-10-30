$ErrorActionPreference = 'Stop'
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
$releaseBase = 'https://github.com/5eeee/print-studio-desktop/releases/download/v0.4.2'
$installRoot = Join-Path $env:LOCALAPPDATA 'PrintStudio\0.4.2'
$downloadRoot = Join-Path ([IO.Path]::GetTempPath()) ('PrintStudio-' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Force -Path $downloadRoot | Out-Null
$zipFile = Join-Path $downloadRoot 'PrintStudio.zip'
$hashFile = Join-Path $downloadRoot 'PrintStudio.zip.sha256'
Write-Host 'Downloading Print Studio...'
if (Get-Command curl.exe -ErrorAction SilentlyContinue) {
    & curl.exe --fail --location --retry 2 --connect-timeout 20 --max-time 600 --output $zipFile "$releaseBase/PrintStudio.zip"
    if ($LASTEXITCODE -ne 0) { throw 'Archive download failed' }
    & curl.exe --fail --location --retry 2 --connect-timeout 20 --max-time 60 --output $hashFile "$releaseBase/PrintStudio.zip.sha256"
    if ($LASTEXITCODE -ne 0) { throw 'Checksum download failed' }
} else {
    $ProgressPreference = 'SilentlyContinue'
    Invoke-WebRequest -UseBasicParsing -Uri "$releaseBase/PrintStudio.zip" -OutFile $zipFile -TimeoutSec 600
    Invoke-WebRequest -UseBasicParsing -Uri "$releaseBase/PrintStudio.zip.sha256" -OutFile $hashFile -TimeoutSec 60
}
$expectedHash = (Get-Content -LiteralPath $hashFile -Raw).Trim()
if ($expectedHash -notmatch '^[A-Fa-f0-9]{64}$') { throw 'Invalid checksum file' }
if ((Get-FileHash -LiteralPath $zipFile -Algorithm SHA256).Hash -ne $expectedHash) { throw 'Checksum mismatch. Installation stopped.' }
New-Item -ItemType Directory -Force -Path $installRoot | Out-Null
Expand-Archive -LiteralPath $zipFile -DestinationPath $installRoot -Force
$exePath = Join-Path $installRoot 'PrintStudio\PrintStudio.exe'
if (-not (Test-Path -LiteralPath $exePath)) { throw 'Application executable missing' }
$shortcutShell = New-Object -ComObject WScript.Shell
$shortcut = $shortcutShell.CreateShortcut((Join-Path ([Environment]::GetFolderPath('Desktop')) 'Print Studio.lnk'))
$shortcut.TargetPath = $exePath
$shortcut.WorkingDirectory = Split-Path -Parent $exePath
$shortcut.Save()
Write-Host 'Installed. Desktop shortcut: Print Studio'
Start-Process -FilePath $exePath
