# Builds the installer:  dist\installer\StukeZ-Designworks-Studio-<version>-Setup.exe  (+ a .sha256 file next to it).
# Run from this folder:  powershell -File build_installer.ps1            (add -RefreshStarter to rebuild starter\ from the vault first)
param([switch]$RefreshStarter)
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

function Check($what) { if ($LASTEXITCODE -ne 0) { throw "$what failed (exit code $LASTEXITCODE)" } }

if ($RefreshStarter) { py -3 make_starter.py; Check "make_starter" }
if (-not (Test-Path "starter\VERSION")) { throw "starter\ is missing: run with -RefreshStarter on the machine that has the vault" }
if (-not (Test-Path "legal\THIRD_PARTY_NOTICES.txt")) { throw "legal\ is missing: run with -RefreshStarter" }

$version = (py -3 -c "from stukez_studio import __version__; print(__version__)").Trim(); Check "version"
$channel = (py -3 -c "from stukez_studio import __channel__; print(__channel__)").Trim(); Check "channel"
$suffix = if ($channel) { "-$channel" } else { "" }    # the installer's name carries the channel, e.g. ...-1.2.2-beta-Setup.exe
$starter = (Get-Content "starter\VERSION" -Raw).Trim()
if ($starter -ne $version) { throw "starter\ is for version $starter but the program is ${version}. Run with -RefreshStarter" }

py -3 -m pip install --quiet -r requirements.txt; Check "pip install"
py -3 make_icon.py; Check "icon"

$excludes = "QtWebEngineCore","QtWebEngineWidgets","QtWebEngineQuick","QtQml","QtQuick","QtQuickWidgets","Qt3DCore","Qt3DRender",
            "QtMultimedia","QtMultimediaWidgets","QtCharts","QtDataVisualization","QtSql","QtTest","QtBluetooth","QtNfc","QtSensors",
            "QtSerialPort","QtPdf","QtPdfWidgets","QtOpenGL","QtOpenGLWidgets","QtNetwork","QtDesigner","QtHelp","QtSvgWidgets",
            "QtRemoteObjects","QtPositioning","QtLocation","QtScxml","QtStateMachine","QtTextToSpeech","QtWebChannel","QtWebSockets"
$exArgs = $excludes | ForEach-Object { "--exclude-module"; "PySide6.$_" }

# a folder (not one big file): starts faster, triggers fewer virus scanners, and keeps the Qt libraries replaceable (LGPL)
py -3 -m PyInstaller --noconfirm --clean --onedir --windowed --name "StukeZ Designworks Studio" `
    --icon "assets\icon.ico" --collect-submodules markdown `
    --add-data "starter;starter" --add-data "legal;legal" --add-data "stukez_studio\builtin;stukez_studio\builtin" `
    --hidden-import argparse --hidden-import dataclasses --hidden-import datetime --hidden-import shutil --hidden-import collections `
    --hidden-import unicodedata --hidden-import zipfile --hidden-import csv `
    @exArgs run_studio.py
Check "PyInstaller"

$iscc = @("$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe", "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe", "$env:ProgramFiles\Inno Setup 6\ISCC.exe") |
        Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $iscc) { throw "Inno Setup 6 is not installed (winget install JRSoftware.InnoSetup)" }
& $iscc "/DAppVersion=$version" "/DChannel=$suffix" installer.iss; Check "Inno Setup"

$setup = "dist\installer\StukeZ-Designworks-Studio-$version$suffix-Setup.exe"
$hash = (Get-FileHash $setup -Algorithm SHA256).Hash.ToLower()
"$hash  $(Split-Path $setup -Leaf)" | Out-File -FilePath "$setup.sha256" -Encoding ascii -NoNewline
Write-Host "Done: $PSScriptRoot\$setup"
Write-Host "SHA-256: $hash"
