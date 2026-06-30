# -*- mode: python ; coding: utf-8 -*-
"""PicShare 打包规格（mac arm64 / Windows x86_64 通用）。

构建：
    pyinstaller picshare.spec --noconfirm --clean

产物：
    - macOS:   dist/PicShare.app
    - Windows: dist/PicShare/PicShare.exe（同目录还有运行所需的依赖）

注意：PyInstaller 不能跨平台交叉编译，需在目标平台各自构建。
"""

import sys

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

# customtkinter 随包携带主题/资源文件，必须显式收集，否则运行时报缺资源
datas = collect_data_files("customtkinter")
hiddenimports = collect_submodules("customtkinter")

a = Analysis(
    ["packaging/launcher.py"],
    pathex=["src"],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="PicShare",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,            # 隐藏控制台黑框（GUI 程序）
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,         # 在目标机原生架构构建（macos-14=arm64, win=x64）
    codesign_identity=None,
    entitlements_file=None,
    icon=None,                # 有图标后填 packaging/icon.icns / icon.ico
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="PicShare",
)

if sys.platform == "darwin":
    app = BUNDLE(
        coll,
        name="PicShare.app",
        icon=None,
        bundle_identifier="com.picshare.app",
        info_plist={
            "NSHighResolutionCapable": True,
            "LSMinimumSystemVersion": "11.0",
            # 本程序仅做局域网/IPv6 自用服务，标注允许任意本地网络访问
            "NSAppTransportSecurity": {"NSAllowsArbitraryLoads": True},
        },
    )
