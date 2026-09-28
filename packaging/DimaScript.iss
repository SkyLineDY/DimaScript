#define AppSource "..\dist\DimaScript"

[Setup]
AppId={{5EBD713F-A2D4-4866-8439-5952C79EFA28}
AppName=DimaScript
AppVersion=2.0.0
AppVerName=DimaScript 2.0
VersionInfoDescription=DimaScript Setup
VersionInfoProductName=DimaScript
DefaultDirName={localappdata}\Programs\DimaScript
DefaultGroupName=DimaScript
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
OutputDir=..\dist
OutputBaseFilename=DimaScript-Setup
SetupIconFile=..\assets\app.ico
UninstallDisplayIcon={app}\DimaScript.exe
Compression=lzma2/fast
SolidCompression=yes
WizardStyle=modern
WizardImageFile=..\assets\installer\wizard.bmp
WizardSmallImageFile=..\assets\installer\wizard-small.bmp
DisableWelcomePage=no
DisableProgramGroupPage=yes
CloseApplications=yes
RestartApplications=no
SetupLogging=yes
DiskSpanning=no
UninstallDisplayName=DimaScript

[Languages]
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; Flags: checkedonce

[Files]
Source: "{#AppSource}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\DimaScript"; Filename: "{app}\DimaScript.exe"; WorkingDir: "{userdocs}"
Name: "{autodesktop}\DimaScript"; Filename: "{app}\DimaScript.exe"; WorkingDir: "{userdocs}"; Tasks: desktopicon

[Run]
Filename: "{app}\DimaScript.exe"; Description: "{cm:LaunchProgram,DimaScript}"; Flags: nowait postinstall skipifsilent

