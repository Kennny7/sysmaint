; Inno Setup Script for SysMaint (Kennny7 Microservices)
; Builds a clickable Windows .exe installer with default PATH setup & shortcuts.

#define MyAppName "SysMaint"
#define MyAppVersion "3.0.0"
#define MyAppPublisher "Kennny7 Microservices"
#define MyAppURL "https://github.com/Kennny7/sysmaint"
#define MyAppExeName "sysmaint.exe"

[Setup]
AppId={{8F4B9C2A-3E7D-4A1B-9C6E-7D2F5A8B1C30}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
OutputDir=..\..\dist
OutputBaseFilename=SysMaint-Setup-v{#MyAppVersion}
SetupIconFile=..\..\assets\sysmaint-icon.ico
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
ChangesEnvironment=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"
Name: "addtopath"; Description: "Add SysMaint to your PATH (recommended for terminal use)"; GroupDescription: "System Integration:"

[Files]
Source: "..\..\dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\..\assets\sysmaint-icon.ico"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Parameters: "tui"; IconFilename: "{app}\sysmaint-icon.ico"
Name: "{group}\{#MyAppName} Background Service"; Filename: "{app}\{#MyAppExeName}"; Parameters: "serve"; IconFilename: "{app}\sysmaint-icon.ico"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Parameters: "tui"; IconFilename: "{app}\sysmaint-icon.ico"; Tasks: desktopicon

[Registry]
Root: HKCU; Subkey: "Environment"; ValueType: expandsz; ValueName: "Path"; ValueData: "{olddata};{app}"; Tasks: addtopath; Check: NeedsAddPath(ExpandConstant('{app}'))

[Run]
Filename: "{app}\{#MyAppExeName}"; Parameters: "tui"; Description: "Launch SysMaint now"; Flags: nowait postinstall skipifsilent

[Code]
function NeedsAddPath(Param: string): boolean;
var
  OrigPath: string;
begin
  if not RegQueryStringValue(HKEY_CURRENT_USER, 'Environment', 'Path', OrigPath) then
  begin
    Result := True;
    exit;
  end;
  Result := Pos(';' + Uppercase(Param) + ';', ';' + Uppercase(OrigPath) + ';') = 0;
end;
