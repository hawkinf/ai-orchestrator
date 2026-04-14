#define MyAppName "AI Orchestrator"
#define MyAppVersion "__APP_VERSION__"
#define MyAppPublisher "Hawk Informatica"
#define MyAppURL "https://github.com/hawkinf/ai-orchestrator"
#define MyAppExeName "AIOrchestrator.exe"
#define MyBuildCommit "__BUILD_COMMIT__"

[Setup]
AppId={{D11C09B4-8D1E-402D-B6CF-1CCB95A6CE3A}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}/releases
DefaultDirName={autopf}\AI Orchestrator
DefaultGroupName=AI Orchestrator
DisableProgramGroupPage=yes
OutputDir=__OUTPUT_DIR__
OutputBaseFilename=AI-Orchestrator-Setup-__APP_VERSION__
SetupIconFile=__APP_ICON__
Compression=lzma
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=admin
UninstallDisplayIcon={app}\{#MyAppExeName}

[Languages]
Name: "brazilianportuguese"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"

[Tasks]
Name: "desktopicon"; Description: "Criar atalho na area de trabalho"; GroupDescription: "Atalhos:"; Flags: unchecked

[Files]
Source: "__APP_EXE__"; DestDir: "{app}"; Flags: ignoreversion
Source: "__SOURCE_ROOT__\CHANGELOG.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "__SOURCE_ROOT__\update_config.json"; DestDir: "{app}"; Flags: ignoreversion
Source: "__SOURCE_ROOT__\version.json"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\AI Orchestrator"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\AI Orchestrator"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Iniciar AI Orchestrator agora"; Flags: nowait postinstall skipifsilent

[Code]
procedure InitializeWizard;
begin
  WizardForm.WelcomeLabel2.Caption :=
    'Build commit: {#MyBuildCommit}' + #13#10 +
    'Este instalador configura a versao desktop distribuivel do AI Orchestrator.';
end;