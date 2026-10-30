$ErrorActionPreference='Stop'
python -m pip install -r (Join-Path $PSScriptRoot 'requirements.txt')
$helperFile=Join-Path $PSScriptRoot 'native_print.ps1'
$sourceFile=Join-Path $PSScriptRoot 'print_studio.py'
$distPath=Join-Path $PSScriptRoot 'dist'
python -m PyInstaller --noconfirm --windowed --onedir --name PrintStudio --distpath $distPath --add-data "$helperFile;." --exclude-module numpy --exclude-module scipy --exclude-module pandas --exclude-module matplotlib --exclude-module numba --exclude-module IPython $sourceFile
if($LASTEXITCODE -ne 0) { throw 'Build failed' }
# Qt's Windows build imports the OS ICU API. A separately collected ICU 78 DLL
# has versioned exports and shadows that API. Never alter the OS installation.
$shadowIcu=Join-Path $distPath 'PrintStudio\_internal\icuuc.dll'
if(Test-Path -LiteralPath $shadowIcu) { Remove-Item -LiteralPath $shadowIcu }
