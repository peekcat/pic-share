# PicShare

> 专为摄影师设计的自托管、IPv6 直连**客户选片交付**工具。客户在现代化网页相册中在线浏览、标记心仪照片——不走云端上传，也没有微信传图的压缩与低效。

![version](https://img.shields.io/badge/version-0.8.2-blue)
![python](https://img.shields.io/badge/python-3.10%2B-blue)
![platform](https://img.shields.io/badge/platform-macOS%20%7C%20Windows%20%7C%20Linux-lightgrey)
![license](https://img.shields.io/badge/license-PolyForm%20Noncommercial%201.0.0-green)

[English](README.md) · **中文**

<!-- 截图：放一张进来并取消注释，例如 docs/screenshot.png
![PicShare](docs/screenshot.png)
-->

## 核心功能

- **专业选片体验** —— 仿 iOS 风格的现代化相册，提升品牌形象；配 PhotoSwipe 看图器（缩放 / 平移 / 手势 / 键盘）。
- **RAW 格式全支持** —— 自动生成 CR2 / CR3 / NEF / ARW / DNG / ORF / RW2 / PEF / SR2 预览，内置 libraw（经 `rawpy`）解码，**无需安装任何外部程序**。
- **一键选片** —— 客户在网页里收藏照片，选择以「每相册清单」形式保存（导出前不复制任何文件）。
- **IPv6 直连访问** —— 自动生成公网分享链接，无需端口转发或 NAT 配置。
- **全设备兼容** —— 完美适配手机、平板、电脑浏览器。
- **高性能分级缓存** —— 多线程预热缩略图，另有按需生成的大图（1600px）与 RAW「原图」（高清）档，支持懒加载。

## 快速开始

### 运行环境

桌面管理窗口使用各平台自带的系统 WebView（基于 [pywebview](https://pywebview.flowrene.org/)）：

- **macOS** —— 内置 WKWebView，无需额外安装。
- **Windows** —— 需要 **WebView2 运行时**（Win 10/11 通常已自带；若窗口打不开，安装 [Evergreen WebView2 Runtime](https://developer.microsoft.com/microsoft-edge/webview2/)）。
- **Linux** —— 需要 **WebKit2GTK**，例如 `sudo apt install gir1.2-webkit2-4.1 libwebkit2gtk-4.1-0`（不同发行版包名略有差异）。

### 安装

```bash
pip install -e .
```

### 运行

```bash
picshare        # 或：python -m picshare
```

启动后，在桌面管理窗口中：

1. 点击「**选择**」指定相册**根目录**（存放各相册子文件夹的主目录）。
2. 点击「**🔄 刷新网络**」，确认「公网访问地址」中出现 IPv6 地址。
3. 在「**🔗 相册访问管理**」选中相册、设有效期 →「**生成并复制链接**」（默认无口令；敏感相册可勾选启用访问口令）。
4. 把**链接**（`http://[...]:5000/share/<token>`）发给客户即可浏览；若加了口令，则把口令**另行**发给客户（可用「复制链接 / 复制口令」按钮随时重发）。

## 使用流程

- **摄影师端** —— 运行程序，选择照片根目录；在「相册访问管理」中为某个相册生成**专属访问链接**（可设有效期与口令），发给对应客户。
- **客户端** —— 直接打开收到的链接即可浏览、标记喜欢的照片、查看全分辨率大图（RAW 以按需生成的高清 JPEG 呈现），无需输入相册名。
- **回收成果** —— 在桌面端点击「**导出**」，按选片清单把选中的原图复制到 `被标记的照片/<相册>/`，随后自动在文件管理器中打开。

## 访问控制

采用**能力 URL（Capability URL）**模型，而非可猜的相册名：

- 每个相册绑定一个不可枚举的随机 token（`/share/<token>`），相册由 token 在服务端推导，客户**无法在 URL 里指定相册名**，因此看不到、也猜不到别人的相册。
- token 即强随机凭证（192 位），多数场景**一条链接即可**，无需口令。
- 可**选**为敏感相册加**访问口令**（默认关闭）：生成随机 4 位英数口令，与链接**分开**发给客户（口令**不嵌入 URL**，转发链接不会带走口令），客户在网页手动输入一次即可。
- 可为链接设置**有效期**（3 / 7 / 14 天，默认 3 天，到期自动失效）。
- 在桌面端可随时**撤销**某条链接，或重新复制其链接 / 口令。
- token 与口令（若设）存储于 `<根目录>/._picshare/tokens.json`（本机隐藏文件），由桌面端管理，Web 端只读校验。

## 目录结构

> 本仓库已由原始单文件重构为 src 布局的标准 Python 工程。

```
src/picshare/
├── __main__.py        # python -m picshare 入口
├── desktop.py         # 桌面入口：pywebview 管理窗口 + waitress 对外服务
├── config.py          # ServerState 配置、扩展名、缓存/数据目录
├── settings.py        # 用户级配置持久化（记住根目录等）
├── status.py          # 统一日志（logging → 控制台 / 文件 / 运行日志面板）
├── network.py         # IPv6 地址检测（Windows / macOS / Linux）
├── paths.py           # safe_join 路径安全工具
├── preview.py         # 缩略图 / 大图 / RAW 高清生成（rawpy 兜底 + 缓存版本戳）
├── tokens.py          # 访问 token 存储与校验（能力 URL）
├── selections.py      # 客户选片清单存储
├── admin/             # 管理端（pywebview，进程内 js_api，无对外 HTTP 端点）
│   ├── api.py         # 暴露给管理网页的 Python API
│   └── templates.py   # 管理端单页 HTML（相册卡片 / 分享 / 运行日志）
└── web/               # 对外 Web 服务（客户端 /share 访问）
    ├── app.py         # Flask app 与 token 作用域路由
    ├── templates.py   # 相册页 / 落地页 / 口令页模板
    └── static/photoswipe/   # 内置 PhotoSwipe 看图器（离线）
```

## 安全提示

访问控制基于 token（详见上节），相比"猜相册名"已显著加固。但仍需注意以下固有限制：

- **链接即凭证** —— 能力 URL 本质是 bearer secret，**任何拿到链接的人都能访问**。对敏感相册请加设**口令**或**有效期**，并避免在公开渠道分享链接。
- **明文 HTTP** —— 当前未启用 TLS，链路上的中间人可截获 token 与照片。强加密需配合反向代理 / 隧道（如 Caddy、Cloudflare Tunnel）部署，属后续方向。
- **口令未限流** —— 当前未对口令校验做速率限制，短口令在攻击者已持有 token 时理论上可被联网爆破；如需更强口令保护，建议后续加入限流 / 锁定。

请始终确保所选相册根目录下只存放愿意交付的照片。

## 许可协议

以 **[PolyForm Noncommercial License 1.0.0](LICENSE)** 源码可见方式发布 —— 你可以**仅出于非商业目的**使用、修改与分享本项目。**禁止任何商业用途。**

> 说明：由于附带"禁止商用"限制，本项目属于 *source-available（源码可见）*，并非 OSI 定义的"开源（open source）"。
