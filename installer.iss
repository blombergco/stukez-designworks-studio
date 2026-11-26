; Inno Setup script: the installer of StukeZ Designworks Studio. Built by build_installer.ps1 (passes /DAppVersion=x.y.z).
; Installs per user (no administrator rights) into %LocalAppData%\Programs. The AppId never changes, so a newer
; installer replaces the older version in place and your workspace (a separate folder) is never touched.
#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif
#ifndef Channel
  #define Channel ""
#endif
; build_installer.ps1 passes the build folder and output folder (outside the vault); these are the defaults for running ISCC by hand
#ifndef BuildDir
  #define BuildDir "dist\StukeZ Designworks Studio"
#endif
#ifndef OutDir
  #define OutDir "dist\installer"
#endif
#define AppName "StukeZ Designworks Studio"
#define AppExe "StukeZ Designworks Studio.exe"

[Setup]
AppId={{2CE284F2-5A08-4245-9127-C294A5039D13}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}{#Channel}
AppPublisher=StukeZ Designworks
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
PrivilegesRequired=lowest
OutputDir={#OutDir}
OutputBaseFilename=StukeZ-Designworks-Studio-{#AppVersion}{#Channel}-Setup
SetupIconFile=assets\icon.ico
UninstallDisplayIcon={app}\{#AppExe}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64compatible
CloseApplications=yes
RestartApplications=yes
DisableProgramGroupPage=yes

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Shortcuts:"; Flags: unchecked

[Files]
Source: "{#BuildDir}\*"; DestDir: "{app}"; Flags: recursesubdirs ignoreversion createallsubdirs

[Icons]
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\{#AppExe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExe}"; Description: "Start {#AppName}"; Flags: nowait postinstall skipifsilent
