# Builds "StukeZ Designworks Studio.exe" (one file, no console). Run from this folder:  powershell -File build_exe.ps1
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

function Check($what) { if ($LASTEXITCODE -ne 0) { throw "$what failed (exit code $LASTEXITCODE)" } }

py -3 -m pip install --quiet PySide6 markdown pillow pyinstaller; Check "pip install"
py -3 make_icon.py; Check "icon"
if (-not (Test-Path "assets\icon.ico")) { throw "assets\icon.ico was not created" }

$excludes = "QtWebEngineCore","QtWebEngineWidgets","QtWebEngineQuick","QtQml","QtQuick","QtQuickWidgets","Qt3DCore","Qt3DRender",
            "QtMultimedia","QtMultimediaWidgets","QtCharts","QtDataVisualization","QtSql","QtTest","QtBluetooth","QtNfc","QtSensors",
            "QtSerialPort","QtPdf","QtPdfWidgets","QtOpenGL","QtOpenGLWidgets","QtNetwork","QtDesigner","QtHelp","QtSvg","QtSvgWidgets",
            "QtRemoteObjects","QtPositioning","QtLocation","QtScxml","QtStateMachine","QtTextToSpeech","QtWebChannel","QtWebSockets"
$exArgs = $excludes | ForEach-Object { "--exclude-module"; "PySide6.$_" }

py -3 -m PyInstaller --noconfirm --clean --onefile --windowed --name "StukeZ Designworks Studio" `
    --icon "assets\icon.ico" --collect-submodules markdown --add-data "starter;starter" --add-data "legal;legal" --add-data "stukez_studio\builtin;stukez_studio\builtin" `
    --hidden-import argparse --hidden-import dataclasses --hidden-import datetime --hidden-import shutil --hidden-import collections `
    @exArgs run_studio.py
Check "PyInstaller"

try {
    Copy-Item "dist\StukeZ Designworks Studio.exe" "StukeZ Designworks Studio.exe" -Force -ErrorAction Stop
    Write-Host "Done: $PSScriptRoot\StukeZ Designworks Studio.exe"
} catch {   # the running program keeps its exe locked
    Copy-Item "dist\StukeZ Designworks Studio.exe" "StukeZ Designworks Studio (new).exe" -Force
    Write-Host "StukeZ Designworks Studio.exe is in use. The new build is saved as 'StukeZ Designworks Studio (new).exe'; close the app and rename it."
}
