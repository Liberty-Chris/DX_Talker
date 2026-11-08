#define AppVersion "0.2.0a21"
#ifndef AppArch
#define AppArch "x64"
#endif
#if AppArch == "x86"
#define AppSuffix " (x86)"
#define AppFolder "DXTalker-x86"
#else
#define AppSuffix ""
#define AppFolder "DXTalker"
#endif
[Setup]
#if AppArch == "x86"
AppId={{E3D3F26F-0E62-4C2E-B21C-22A7EBEE1102}
#else
AppId={{90179E0C-5656-45D9-A6D9-12AB1E254F66}
#endif
AppName=DX Talker{#AppSuffix}
AppVersion={#AppVersion}
AppPublisher=DX Talker
DefaultDirName={localappdata}\Programs\{#AppFolder}
DefaultGroupName=DX Talker{#AppSuffix}
PrivilegesRequired=lowest
#if AppArch == "x64"
ArchitecturesAllowed=x64os
ArchitecturesInstallIn64BitMode=x64os
#else
ArchitecturesAllowed=x86compatible
#endif
MinVersion=10.0.19045
OutputDir=..\dist
OutputBaseFilename=DXTalker-Setup-Windows-{#AppArch}
SetupIconFile=..\assets\brand\dxt.ico
UninstallDisplayIcon={app}\DXTalker.exe
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
CloseApplications=yes
RestartApplications=no
DisableProgramGroupPage=yes
#ifdef StableRelease
LicenseFile=..\docs\legal\TERMS.txt
InfoBeforeFile=..\docs\legal\PRIVACY.txt
#endif

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; Flags: checkedonce; Check: NeedsDesktopShortcut

[Files]
Source: "..\dist\DXTalker\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\DX Talker{#AppSuffix}"; Filename: "{app}\DXTalker.exe"; WorkingDir: "{app}"
Name: "{autodesktop}\DX Talker{#AppSuffix}"; Filename: "{app}\DXTalker.exe"; WorkingDir: "{app}"; Tasks: desktopicon; Check: NeedsDesktopShortcut

[Run]
Filename: "{app}\DXTalker.exe"; Description: "Launch DX Talker"; Flags: nowait postinstall skipifsilent

[Code]
function DesktopHasAppShortcut(const Folder: String): Boolean;
var
  Entry: TFindRec;
  Shell, Shortcut: Variant;
  Target: String;
begin
  Result := False;
  if FindFirst(AddBackslash(Folder) + '*.lnk', Entry) then
  begin
    try
      Shell := CreateOleObject('WScript.Shell');
      repeat
        try
          Shortcut := Shell.CreateShortcut(AddBackslash(Folder) + Entry.Name);
          Target := Shortcut.TargetPath;
          if CompareText(Target, ExpandConstant('{app}\DXTalker.exe')) = 0 then
          begin
            Result := True;
            Break;
          end;
        except
          Log('Could not inspect a desktop shortcut; leaving it unchanged.');
        end;
      until not FindNext(Entry);
    finally
      FindClose(Entry);
    end;
  end;
end;

function NeedsDesktopShortcut: Boolean;
begin
  Result := not (DesktopHasAppShortcut(ExpandConstant('{userdesktop}')) or
    DesktopHasAppShortcut(ExpandConstant('{commondesktop}')));
end;
