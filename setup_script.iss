; Instalador de Windows (Inno Setup 6).
;
; No lo compile a mano: use  python compilar.py , que lee la versión de _version.py
; y la pasa con /DMyAppVersion=... (así la versión está definida en un solo lugar).

#ifndef MyAppVersion
  #define MyAppVersion "0.0.0-dev"
#endif
#define MyAppName "Calculadora Accesible"
#define MyAppExeName "CalculadoraAccesible.exe"
#define MyAppURL "https://github.com/agus-romero96/calculadora_accesible"
; Carpeta generada por setup.py (cx_Freeze)
#define CarpetaBuild "build\CalculadoraAccesible"

[Setup]
; NOTE: The value of AppId uniquely identifies this application.
; Do not use the same AppId value in installers for other applications.
; No cambiarlo (ni siquiera las llaves finales "}}", que vienen del instalador 1.0.0):
; es lo que permite que una versión nueva actualice a la instalada.
AppId={{F4D4B88C-9A25-4B3A-9A2E-4989A8A815D4}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher=Jansen
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}/releases
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir=Output
OutputBaseFilename=setup-calculadora-accesible-v{#MyAppVersion}
UninstallDisplayIcon={app}\{#MyAppExeName}
Compression=lzma
SolidCompression=yes
WizardStyle=modern

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "{#CarpetaBuild}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
; NOTE: Don't use "Flags: ignoreversion" on any shared system files

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon
