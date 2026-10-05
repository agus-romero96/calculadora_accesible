[Setup]
; NOTE: The value of AppId uniquely identifies this application.
; Do not use the same AppId value in installers for other applications.
AppId={{F4D4B88C-9A25-4B3A-9A2E-4989A8A815D4}}
AppName=Calculadora Accesible
AppVersion=1.0.0
AppPublisher=Jansen
AppPublisherURL=https://github.com/jansen-dev/calculadora_accesible
AppSupportURL=https://github.com/jansen-dev/calculadora_accesible
AppUpdatesURL=https://github.com/jansen-dev/calculadora_accesible/releases
DefaultDirName={autopf}\Calculadora Accesible
DefaultGroupName=Calculadora Accesible
DisableProgramGroupPage=yes
OutputBaseFilename=setup-calculadora-accesible-v1.0.0
Compression=lzma
SolidCompression=yes
WizardStyle=modern

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "build\exe.win-amd64-3.12\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
; NOTE: Don't use "Flags: ignoreversion" on any shared system files

[Icons]
Name: "{group}\Calculadora Accesible"; Filename: "{app}\CalculadoraAccesible.exe"
Name: "{autodesktop}\Calculadora Accesible"; Filename: "{app}\CalculadoraAccesible.exe"; Tasks: desktopicon
