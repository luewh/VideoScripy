param(
    [string]$PythonExecutable = "python",
    [string]$OutputDirectory = (Join-Path $PSScriptRoot "dist")
)

$ErrorActionPreference = "Stop"
$root = (Resolve-Path $PSScriptRoot).Path
$pythonCommand = Get-Command $PythonExecutable -ErrorAction SilentlyContinue
if ($null -eq $pythonCommand) {
    throw "Python executable not found: $PythonExecutable. Install 64-bit Python 3.13 to build the portable folder."
}
$PythonExecutable = $pythonCommand.Source

$pythonInfo = & $PythonExecutable -c "import json, struct, sys; print(json.dumps({'version': list(sys.version_info[:3]), 'prefix': sys.base_prefix, 'bits': struct.calcsize('P') * 8}))"
if ($LASTEXITCODE -ne 0) {
    throw "Could not inspect the selected Python interpreter."
}
$pythonInfo = $pythonInfo | ConvertFrom-Json
if ($pythonInfo.version[0] -ne 3 -or $pythonInfo.version[1] -ne 13 -or $pythonInfo.bits -ne 64) {
    throw "The portable bundle requires a 64-bit Python 3.13 build interpreter. Found $($pythonInfo.version -join '.') ($($pythonInfo.bits)-bit)."
}

$version = $pythonInfo.version -join "."
$embeddedUrl = "https://www.python.org/ftp/python/$version/python-$version-embed-amd64.zip"
$tools = Join-Path $root "tools"
$OutputDirectory = [System.IO.Path]::GetFullPath($OutputDirectory)
$portableDirectory = Join-Path $OutputDirectory "VideoScripyWebUI"
$runtimeDirectory = Join-Path $portableDirectory "python"
$sitePackages = Join-Path $runtimeDirectory "Lib\site-packages"
$temporaryRuntimeZip = Join-Path ([System.IO.Path]::GetTempPath()) "python-$version-embed-amd64-$([guid]::NewGuid().ToString('N')).zip"

foreach ($requiredPath in @(
    (Join-Path $root "VideoScripyWebUI.py"),
    (Join-Path $root "VideoScripy.py"),
    (Join-Path $root "VideoScripyCLI.py"),
    (Join-Path $root "webui"),
    (Join-Path $root "videoscripy"),
    (Join-Path $root "requirements.txt"),
    (Join-Path $root "LICENSE"),
    (Join-Path $root "assets"),
    (Join-Path $tools "ffmpeg-full_build\bin\ffmpeg.exe"),
    (Join-Path $tools "ffmpeg-full_build\bin\ffprobe.exe"),
    (Join-Path $tools "Real-ESRGAN\realesrgan-ncnn-vulkan.exe"),
    (Join-Path $tools "Ifrnet\ifrnet-ncnn-vulkan.exe"),
    (Join-Path $tools "NVEncC\NVEncC64.exe")
)) {
    if (-not (Test-Path $requiredPath)) {
        throw "Required portable release input not found: $requiredPath"
    }
}

if (Test-Path $portableDirectory) {
    Remove-Item -LiteralPath $portableDirectory -Recurse -Force
}
New-Item -ItemType Directory -Path $runtimeDirectory | Out-Null

try {
    Write-Output "Downloading embeddable Python $version..."
    & curl.exe --fail --location --silent --show-error --output $temporaryRuntimeZip $embeddedUrl
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to download the Python embeddable package from $embeddedUrl"
    }
    Expand-Archive -LiteralPath $temporaryRuntimeZip -DestinationPath $runtimeDirectory

    $basePrefix = $pythonInfo.prefix
    $runtimeLib = Join-Path $runtimeDirectory "Lib"
    $runtimeDlls = Join-Path $runtimeDirectory "DLLs"
    New-Item -ItemType Directory -Path $sitePackages -Force | Out-Null
    New-Item -ItemType Directory -Path $runtimeDlls -Force | Out-Null
    Copy-Item -LiteralPath (Join-Path $basePrefix "Lib\tkinter") -Destination $runtimeLib -Recurse
    Copy-Item -LiteralPath (Join-Path $basePrefix "DLLs\_tkinter.pyd") -Destination $runtimeDlls
    Copy-Item -LiteralPath (Join-Path $basePrefix "DLLs\tcl86t.dll") -Destination $runtimeDlls
    Copy-Item -LiteralPath (Join-Path $basePrefix "DLLs\tk86t.dll") -Destination $runtimeDlls
    Copy-Item -LiteralPath (Join-Path $basePrefix "DLLs\zlib1.dll") -Destination $runtimeDlls
    New-Item -ItemType Directory -Path (Join-Path $runtimeDirectory "tcl") -Force | Out-Null
    Copy-Item -LiteralPath (Join-Path $basePrefix "tcl\tcl8.6") -Destination (Join-Path $runtimeDirectory "tcl") -Recurse
    Copy-Item -LiteralPath (Join-Path $basePrefix "tcl\tk8.6") -Destination (Join-Path $runtimeDirectory "tcl") -Recurse

    $pythonPathFile = Get-ChildItem -LiteralPath $runtimeDirectory -Filter "python*._pth" | Select-Object -First 1
    if ($null -eq $pythonPathFile) {
        throw "The Python embeddable package did not contain a python._pth file."
    }
    @(
        "$($pythonPathFile.BaseName).zip",
        "..",
        ".",
        "DLLs",
        "Lib",
        "Lib\site-packages",
        "import site"
    ) | Set-Content -LiteralPath $pythonPathFile.FullName -Encoding Ascii
    @(
        "import os",
        "import sys",
        "runtime = os.path.dirname(sys.executable)",
        "_dll_directory = os.add_dll_directory(os.path.join(runtime, 'DLLs'))",
        "os.environ.setdefault('TCL_LIBRARY', os.path.join(runtime, 'tcl', 'tcl8.6'))",
        "os.environ.setdefault('TK_LIBRARY', os.path.join(runtime, 'tcl', 'tk8.6'))"
    ) | Set-Content -LiteralPath (Join-Path $runtimeLib "sitecustomize.py") -Encoding Ascii

    Write-Output "Installing Python dependencies into the embedded runtime..."
    & $PythonExecutable -m pip install --disable-pip-version-check --no-warn-script-location --target $sitePackages -r (Join-Path $root "requirements.txt")
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to install Python dependencies into the portable runtime."
    }

    foreach ($sourceFile in @("VideoScripy.py", "VideoScripyCLI.py", "VideoScripyWebUI.py", "LICENSE")) {
        Copy-Item -LiteralPath (Join-Path $root $sourceFile) -Destination $portableDirectory
    }
    Copy-Item -LiteralPath (Join-Path $root "videoscripy") -Destination $portableDirectory -Recurse
    Copy-Item -LiteralPath (Join-Path $root "webui") -Destination $portableDirectory -Recurse
    Copy-Item -LiteralPath (Join-Path $root "assets") -Destination $portableDirectory -Recurse
    Copy-Item -LiteralPath $tools -Destination $portableDirectory -Recurse

    $launcher = @"
@echo off
setlocal
cd /d "%~dp0"
set "TCL_LIBRARY=%~dp0python\tcl\tcl8.6"
set "TK_LIBRARY=%~dp0python\tcl\tk8.6"
set "VIDEOSCRIPY_PORTABLE=1"
set "PATH=%~dp0python;%~dp0python\DLLs;%~dp0tools\ffmpeg-full_build\bin;%~dp0tools\Real-ESRGAN;%~dp0tools\Ifrnet;%~dp0tools\NVEncC;%PATH%"
"%~dp0python\python.exe" "%~dp0VideoScripyWebUI.py"
if errorlevel 1 pause
"@
    Set-Content -LiteralPath (Join-Path $portableDirectory "Run VideoScripyWebUI.bat") -Value $launcher -Encoding Ascii

    $portableReadme = @"
VideoScripy portable for Windows x64

Run "Run VideoScripyWebUI.bat". This folder includes the embeddable Python
runtime, application dependencies, Tcl/Tk, assets, and required tools.
Python does not need to be installed on the target PC.

Keep the complete folder together when moving it. NVIDIA GPU features require
a compatible NVIDIA driver; the bundled AI tools may also require Vulkan support.
"@
    Set-Content -LiteralPath (Join-Path $portableDirectory "README_PORTABLE.txt") -Value $portableReadme -Encoding Ascii

    $runtimePython = Join-Path $runtimeDirectory "python.exe"
    $previousPath = $env:PATH
    $previousTclLibrary = $env:TCL_LIBRARY
    $previousTkLibrary = $env:TK_LIBRARY
    $env:PATH = "$runtimeDirectory;$runtimeDlls;$env:SystemRoot\System32;$env:SystemRoot"
    $env:TCL_LIBRARY = Join-Path $runtimeDirectory "tcl\tcl8.6"
    $env:TK_LIBRARY = Join-Path $runtimeDirectory "tcl\tk8.6"
    & $runtimePython -c "import dash, dash_bootstrap_components, plotly, tkinter; print('Embedded runtime and dependencies verified')"
    $validationExitCode = $LASTEXITCODE
    $env:PATH = $previousPath
    if ($null -eq $previousTclLibrary) {
        Remove-Item Env:TCL_LIBRARY -ErrorAction SilentlyContinue
    }
    else {
        $env:TCL_LIBRARY = $previousTclLibrary
    }
    if ($null -eq $previousTkLibrary) {
        Remove-Item Env:TK_LIBRARY -ErrorAction SilentlyContinue
    }
    else {
        $env:TK_LIBRARY = $previousTkLibrary
    }
    if ($validationExitCode -ne 0) {
        throw "The embedded Python runtime could not import its packaged dependencies."
    }

    Write-Output "Portable folder created at: $portableDirectory"
}
finally {
    if (Test-Path $temporaryRuntimeZip) {
        Remove-Item -LiteralPath $temporaryRuntimeZip -Force
    }
}
