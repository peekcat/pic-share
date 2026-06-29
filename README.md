# PicShareLite-IPV6

This is a program developed for professional photographers or photography studios. It exposes your IPv6 address so that your clients can access a specific folder, select the photos they like for retouching, or download the photos you have already edited.

You need to install ImageMagick to use the RAW preview function of this software.
你需要安装 ImageMagick 才能正常使用这个软件的 RAW 预览图功能。

PicShareLite 是专为摄影师设计的客户选片交付系统。通过现代化的网页相册，让客户在线浏览、标记心仪照片，支持原图下载，彻底告别微信传图的压缩和低效。
PicShareLite is a client photo selection and delivery system designed specifically for photographers. Through a modern web album, clients can browse, mark favorite photos online, and download originals, completely eliminating the compression and inefficiency of WeChat file transfers.

## 核心功能 / Key Features

- **专业选片体验**：仿 iOS 风格的现代化界面，提升品牌形象
- **RAW 格式全支持**：自动生成 CR2、CR3、NEF 等 RAW 文件预览图
- **智能标记系统**：客户一键收藏，照片自动汇总到指定文件夹
- **IPv6 直连访问**：无需复杂配置，自动生成公网访问链接
- **全设备兼容**：完美适配手机、平板、电脑浏览器
- **高性能缓存**：多线程生成缩略图，支持懒加载

## 使用流程 / Workflow

- **摄影师端**：运行程序，选择照片根目录，复制生成的 IPv6 链接
- **客户端**：打开链接，输入相册名，浏览并标记喜欢的照片，下载原图
- **回收成果**：在 `被标记的照片` 文件夹查看客户选择

## 安装 / Install

```bash
pip install -e .
```

可选依赖：RAW 文件转码需要系统安装 [ImageMagick](https://imagemagick.org)
（命令行 `magick` 需在 PATH 中）。

## 运行 / Run

```bash
picshare
# 或
python -m picshare
```

启动后在桌面 GUI 中：

1. 点击「选择」指定相册根目录（存放各相册子文件夹的主目录）。
2. 确认底部显示「检测到 IPv6 地址」。
3. 复制 `http://[...]:5000` 地址，在手机/电脑浏览器中访问。
4. 在网页输入根目录下的子文件夹名（相册名）即可浏览。

## 目录结构 / Project Layout

> 本仓库已由原始单文件重构为 src 布局的标准 Python 工程。

```
src/picshare/
├── __main__.py        # python -m picshare 入口
├── config.py          # ServerState 配置、扩展名集合
├── status.py          # 状态广播（GUI 与后台模块解耦点）
├── paths.py           # safe_join 路径安全工具
├── network.py         # IPv6 地址检测（Windows / macOS / Linux）
├── preview.py         # 缩略图 / RAW 预览生成
├── gui.py             # Tkinter 控制面板 + 程序入口 main()
└── web/
    ├── app.py         # Flask app 与路由
    └── templates.py   # 内嵌 HTML / CSS / SVG 图标
```

## 安全提示 / Security Note

本服务**没有访问密码**，安全性依赖 IPv6 地址的复杂性。请确保所选相册根目录下
只存放愿意公开的照片，并谨慎分享访问地址。
