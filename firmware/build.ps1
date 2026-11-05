$ErrorActionPreference = 'Stop'
Push-Location $PSScriptRoot
try {
    node prepare-basic.js
    if ($LASTEXITCODE) { throw 'BASIC preparation failed' }
    $toolDir = Join-Path $PSScriptRoot 'tools/cc65/bin'
    & "$toolDir/ca65.exe" -I build -l build/rom.lst -o build/rom.o rom.s
    if ($LASTEXITCODE) { throw 'Assembly failed' }
    & "$toolDir/ld65.exe" -C rom.cfg -m build/rom.map -Ln build/rom.lbl -o build/rom.bin build/rom.o
    if ($LASTEXITCODE) { throw 'Link failed' }
    & "$toolDir/ca65.exe" -o build/hello.o examples/hello.s
    if ($LASTEXITCODE) { throw 'Example assembly failed' }
    & "$toolDir/ld65.exe" -C examples/ram.cfg -o build/hello.bin build/hello.o
    if ($LASTEXITCODE) { throw 'Example link failed' }
    node bin-to-hex.js build/hello.bin 0400 | Set-Content -Encoding ASCII build/hello.hex
    node verify.js
    if ($LASTEXITCODE) { throw 'Verification failed' }
} finally { Pop-Location }
