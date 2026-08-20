; PicShare Windows 安装包（Inno Setup 6.5+ / 7.x）
;
; 编译：
;     ISCC.exe packaging\windows\picshare.iss /DMyAppVersion=0.9.2
;
; 前置：先跑过 `pyinstaller picshare.spec`，产物在 dist\PicShare\。
; 本文件必须以 UTF-8 with BOM 保存，否则 ISCC 会按系统 ANSI 码页读取，中文变乱码。

#ifndef MyAppVersion
  #define MyAppVersion "0.0.0"
#endif
; PyInstaller 的 onedir 产物目录（相对本文件所在位置）
#ifndef SourceDir
  #define SourceDir "..\..\dist\PicShare"
#endif
#ifndef OutputDir
  #define OutputDir "..\..\dist"
#endif

#define MyAppName "PicShare"
#define MyAppExeName "PicShare.exe"
#define MyAppPublisher "peekcat"
#define MyAppURL "https://github.com/peekcat/pic-share"

[Setup]
; AppId 是这个程序的身份标识，一旦发布就不能再改——改了会导致新版本
; 与旧版本并排安装、卸载项重复。
AppId={{C72FD85A-6B7B-4D6F-90BA-0F7AF7F0F6BA}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}/issues
AppUpdatesURL={#MyAppURL}/releases
VersionInfoVersion={#MyAppVersion}

; 装到 %LocalAppData%\Programs\PicShare：配合 PrivilegesRequired=lowest 全程不弹 UAC。
; 摄影师的电脑常常没有管理员权限，要管理员才能装会直接卡住一批人。
PrivilegesRequired=lowest
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
; 开始菜单文件夹名不值得让用户填一遍
DisableProgramGroupPage=yes
UninstallDisplayName={#MyAppName}
UninstallDisplayIcon={app}\{#MyAppExeName}

; 非商业许可，安装前让用户看到
LicenseFile=..\..\LICENSE

; 仅 64 位；PyInstaller 产物就是 x64 的
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

OutputDir={#OutputDir}
OutputBaseFilename=PicShare-Setup-{#MyAppVersion}-x64
; onedir 产物是一大堆 DLL/pyd，实压比很高，值得用最高档
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern

[Languages]
; 简体中文在 Inno Setup 6.x 里是「非官方翻译」，不随编译器安装（runner 上也没有），
; 所以由 make-installer.ps1 找一份可用的传进来：优先编译器自带（Inno 7 起转正、
; 版本必然匹配），没有就用仓库自带的 ChineseSimplified.isl。
; 两者都没有时只出英文界面——语言缺失不该让整个构建挂掉。
#ifdef ChineseIsl
Name: "chinese"; MessagesFile: "{#ChineseIsl}"
#endif
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "{#SourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#MyAppName}}"; Flags: nowait postinstall skipifsilent

; 卸载不动 %APPDATA%\PicShare\（记住的相册根目录、端口、日志），
; 也不动照片根目录下的 ._picshare\（token、选片清单、缓存）——
; 那些是用户数据，重装后应当还在。

