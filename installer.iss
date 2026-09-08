[Setup]
AppName=RSInstaller
AppVersion=0.1.0
AppPublisher=RSG Software
DefaultDirName={autopf}\RSInstaller
DefaultGroupName=RSG Software
OutputDir=Output
OutputBaseFilename=RSInstallerSetup
Compression=lzma
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest

[Files]
Source: "dist\RSInstaller.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\RSInstaller"; Filename: "{app}\RSInstaller.exe"
Name: "{autodesktop}\RSInstaller"; Filename: "{app}\RSInstaller.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Extra shortcuts:"

[Run]
Filename: "{app}\RSInstaller.exe"; Description: "Launch RSInstaller"; Flags: nowait postinstall skipifsilent