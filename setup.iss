; HamsterDancer - Inno Setup 설치 스크립트
; 빌드 후 이 파일을 Inno Setup Compiler로 컴파일하세요.
; 다운로드: https://jrsoftware.org/isdl.php

[Setup]
AppId={{A3F7C2E1-8B4D-4F6A-9E2C-1D5B7A3F8C2E}
AppName=HamsterDancer
AppVersion=1.1.0
AppPublisher=HamsterDancer
DefaultDirName={autopf}\HamsterDancer
DefaultGroupName=HamsterDancer
OutputDir=installer
OutputBaseFilename=HamsterDancer_Setup_v1.1.0
Compression=lzma
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={app}\HamsterDancer.exe

[Languages]
Name: "korean"; MessagesFile: "compiler:Languages\Korean.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "startup"; Description: "Windows 시작 시 자동 실행 (권장)"; GroupDescription: "추가 옵션:"; Flags: checkedonce
Name: "desktopicon"; Description: "바탕화면 바로가기 생성"; GroupDescription: "추가 옵션:"; Flags: unchecked

[Files]
Source: "dist\HamsterDancer\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\HamsterDancer"; Filename: "{app}\HamsterDancer.exe"
Name: "{group}\제거 (Uninstall)"; Filename: "{uninstallexe}"
Name: "{commondesktop}\HamsterDancer"; Filename: "{app}\HamsterDancer.exe"; Tasks: desktopicon

[Registry]
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "HamsterDancer"; ValueData: """{app}\HamsterDancer.exe"""; Flags: uninsdeletevalue; Tasks: startup

[Run]
Filename: "{app}\HamsterDancer.exe"; Description: "HamsterDancer 지금 실행"; Flags: nowait postinstall skipifsilent

[UninstallRun]
Filename: "taskkill"; Parameters: "/f /im HamsterDancer.exe"; Flags: runhidden; RunOnceId: "KillApp"

[Code]
procedure CurStepChanged(CurStep: TSetupStep);
var
  ResultCode: Integer;
begin
  if CurStep = ssInstall then
    Exec('taskkill', '/f /im HamsterDancer.exe', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
end;
