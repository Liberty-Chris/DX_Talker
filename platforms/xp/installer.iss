#define AppVersion "@VERSION@"
#define StageDir "@STAGE@"
#define Bits "@BITS@"
[Setup]
AppId=@APPID@
AppName=DX Talker XP ({#Bits} bit)
AppVersion={#AppVersion}
AppPublisher=DX Talker
DefaultDirName={localappdata}\Programs\DXTalkerXP-{#Bits}bit
DefaultGroupName=DX Talker XP ({#Bits} bit)
PrivilegesRequired=lowest
@ARCHFLAGS@
MinVersion=@MINVER@
OutputDir=@OUTPUT@
OutputBaseFilename=DXTalker-Setup-Windows-XP-{#Bits}bit
SetupIconFile={#StageDir}\assets\brand\dxt.ico
UninstallDisplayIcon={app}\DXTalkerXP.exe
Compression=lzma2
SolidCompression=yes
CloseApplications=yes
RestartApplications=no
DisableProgramGroupPage=yes

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; Flags: checkedonce; Check: NeedsDesktopShortcut

[Files]
Source: "{#StageDir}\DXTalkerXP.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#StageDir}\run_xp.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#StageDir}\sounddevice.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#StageDir}\LICENSE"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#StageDir}\dxtalker\*"; DestDir: "{app}\dxtalker"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "{#StageDir}\xp_support\*"; DestDir: "{app}\xp_support"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "{#StageDir}\runtime\*"; DestDir: "{app}\runtime"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "{#StageDir}\assets\*"; DestDir: "{app}\assets"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "{#StageDir}\docs\help\*"; DestDir: "{app}\docs\help"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\DX Talker XP ({#Bits} bit)"; Filename: "{app}\DXTalkerXP.exe"; WorkingDir: "{app}"
Name: "{userdesktop}\DX Talker XP ({#Bits} bit)"; Filename: "{app}\DXTalkerXP.exe"; WorkingDir: "{app}"; Tasks: desktopicon; Check: NeedsDesktopShortcut

[Run]
Filename: "{app}\DXTalkerXP.exe"; Description: "Launch DX Talker XP"; Flags: nowait postinstall skipifsilent

[Code]
function InitializeSetup: Boolean;
var
  Version: TWindowsVersion;
begin
  Result := True;
  GetWindowsVersionEx(Version);
  if (Version.Major = 5) and (Version.Minor = 2) and (Version.ServicePackMajor < 2) then
  begin
    MsgBox('The 64 bit XP platform requires Service Pack 2.', mbError, MB_OK);
    Result := False;
  end;
end;

function DesktopHasShortcut(const Folder: String): Boolean;
var
  Entry: TFindRec;
  Shell, Shortcut: Variant;
begin
  Result := False;
  if FindFirst(AddBackslash(Folder) + '*.lnk', Entry) then
  begin
    try
      try
        Shell := CreateOleObject('WScript.Shell');
        repeat
          try
            Shortcut := Shell.CreateShortcut(AddBackslash(Folder) + Entry.Name);
            if CompareText(Shortcut.TargetPath, ExpandConstant('{app}\DXTalkerXP.exe')) = 0 then
            begin
              Result := True;
              Break;
            end;
          except
            Log('Could not inspect a shortcut; leaving it unchanged.');
          end;
        until not FindNext(Entry);
      except
        Result := FileExists(ExpandConstant('{app}\DXTalkerXP.exe'));
      end;
    finally
      FindClose(Entry);
    end;
  end;
end;

function NeedsDesktopShortcut: Boolean;
begin
  Result := not (DesktopHasShortcut(ExpandConstant('{userdesktop}')) or
    DesktopHasShortcut(ExpandConstant('{commondesktop}')));
end;
