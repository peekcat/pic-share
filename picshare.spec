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

from PyInstaller.utils.hooks import collect_all

# pywebview 的平台后端（mac: cocoa/pyobjc, win: edgechromium, linux: gtk/qt）
# 需连同数据/隐藏导入一并收集，否则打包后窗口起不来
datas, binaries, hiddenimports = collect_all("webview")

# 本地内置的 PhotoSwipe 静态资源（离线使用），打进包内的 picshare/web/static
datas += [
    ("src/picshare/web/static/photoswipe/photoswipe.esm.min.js", "picshare/web/static/photoswipe"),
    ("src/picshare/web/static/photoswipe/photoswipe.css", "picshare/web/static/photoswipe"),
]

# rawpy(libraw)：RAW 内嵌预览提取失败时的兜底解码，四平台都用，显式全量收集
# 原生库，避免漏收导致运行时找不到 libraw 动态库。
_d, _b, _h = collect_all("rawpy")
datas += _d
binaries += _b
hiddenimports += _h

# Windows 上 pywebview 通过 pythonnet/clr（.NET 桥）启动窗口。PyInstaller 常漏收其
# 原生运行时（clr_loader 的 ClrLoader.dll、pythonnet 的 Python.Runtime.dll 等），
# 导致运行时报 "Failed to resolve Python.Runtime.Loader.Initialize"。这里显式全量收集。
# 非 Windows 平台未安装这些包，collect_all 会抛错，忽略即可。
for _pkg in ("clr_loader", "pythonnet"):
    try:
        _d, _b, _h = collect_all(_pkg)
        datas += _d
        binaries += _b
        hiddenimports += _h
    except Exception:
        pass
hiddenimports += ["clr"]

a = Analysis(
    ["packaging/launcher.py"],
    pathex=["src"],
    binaries=binaries,
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
