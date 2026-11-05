#define AppVersion "0.2.0a5"
[Setup]
AppId={{90179E0C-5656-45D9-A6D9-12AB1E254F66}
AppName=DX Talker
AppVersion={#AppVersion}
AppPublisher=DX Talker
DefaultDirName={localappdata}\Programs\DXTalker
DefaultGroupName=DX Talker
PrivilegesRequired=lowest
ArchitecturesAllowed=x64os
ArchitecturesInstallIn64BitMode=x64os
MinVersion=10.0.19045
OutputDir=..\dist
OutputBaseFilename=DXTalker-Setup-Windows-x64
SetupIconFile=..\assets\brand\dxt.ico
UninstallDisplayIcon={app}\DXTalker.exe
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
CloseApplications=yes
RestartApplications=no
DisableProgramGroupPage=yes

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; Flags: checkedonce; Check: NeedsDesktopShortcut

[Files]
Source: "..\dist\DXTalker\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\DX Talker"; Filename: "{app}\DXTalker.exe"; WorkingDir: "{app}"
Name: "{autodesktop}\DX Talker"; Filename: "{app}\DXTalker.exe"; WorkingDir: "{app}"; Tasks: desktopicon; Check: NeedsDesktopShortcut

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
