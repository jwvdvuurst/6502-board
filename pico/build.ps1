param([switch]$HostTests)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path $PSScriptRoot -Parent
$toolsRoot = Join-Path $projectRoot 'firmware/tools'
$cmake = Join-Path $toolsRoot 'cmake-3.31.6-windows-x86_64/bin/cmake.exe'
$ninja = Join-Path $toolsRoot 'ninja.exe'
if (-not (Test-Path $cmake)) { $cmake = 'cmake' }
if (-not (Test-Path $ninja)) { $ninja = 'ninja' }
$savedPath = $env:PATH
try {
    if ($HostTests) {
        $buildDir = Join-Path $PSScriptRoot 'build-host'
        & $cmake -S $PSScriptRoot -B $buildDir -G Ninja "-DCMAKE_MAKE_PROGRAM:FILEPATH=$ninja" -DBRIDGE_HOST_TESTS=ON -DCMAKE_C_COMPILER=gcc
    } else {
        $env:PATH = (Join-Path $toolsRoot 'bin') + ';' + $env:PATH
        $buildDir = Join-Path $PSScriptRoot 'build'
        $cmakeArgs = @('-S', $PSScriptRoot, '-B', $buildDir, '-G', 'Ninja', "-DCMAKE_MAKE_PROGRAM:FILEPATH=$ninja", '-DPICO_BOARD=pico')
        $picotool = Join-Path $toolsRoot 'picotool'
        if (Test-Path $picotool) { $cmakeArgs += "-Dpicotool_DIR:PATH=$picotool" }
        & $cmake @cmakeArgs
    }
    if ($LASTEXITCODE) { throw 'CMake configure failed' }
    & $cmake --build $buildDir -j 4
    if ($LASTEXITCODE) { throw 'Build failed' }
    if ($HostTests) {
        & (Join-Path $buildDir 'bridge_tests.exe')
        if ($LASTEXITCODE) { throw 'Tests failed' }
    }
} finally { $env:PATH = $savedPath }
