# pic-share

This is a client photo selection and delivery system designed specifically for photographers. Through a modern web album, clients can browse, mark favorite photos online, and download originals, completely eliminating the compression and inefficiency of WeChat file transfers.
这是一款专为摄影师设计的客户选片交付系统。通过现代化的网页相册，让客户在线浏览、标记心仪照片，支持原图下载，彻底告别微信传图的压缩和低效。

You need to install ImageMagick to use the RAW preview function of this software.
你需要安装 ImageMagick 才能正常使用这个软件的 RAW 预览图功能。

## 核心功能 / Key Features

- **专业选片体验**：仿 iOS 风格的现代化界面，提升品牌形象
- **RAW 格式全支持**：自动生成 CR2、CR3、NEF 等 RAW 文件预览图
- **智能标记系统**：客户一键收藏，照片自动汇总到指定文件夹
- **IPv6 直连访问**：无需复杂配置，自动生成公网访问链接
- **全设备兼容**：完美适配手机、平板、电脑浏览器
- **高性能缓存**：多线程生成缩略图，支持懒加载

## 使用流程 / Workflow

- **摄影师端**：运行程序，选择照片根目录；在「相册访问管理」中为某个相册生成**专属访问链接**（可设有效期与口令），发给对应客户
- **客户端**：直接打开收到的链接即可浏览、标记喜欢的照片、下载原图（无需输入相册名）
- **回收成果**：在 `被标记的照片` 文件夹查看各客户的选择

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
3. 点击「🔗 相册访问管理」，选中相册 →（可选设有效期/口令）→「生成并复制链接」。
4. 把得到的 `http://[...]:5000/share/<token>` 链接发给客户，对方打开即可浏览。

## 访问控制 / Access Control

采用**能力 URL（Capability URL）**模型，而非可猜的相册名：

- 每个相册绑定一个不可枚举的随机 token（`/share/<token>`），相册由 token 在服务端推导，
  客户**无法在 URL 里指定相册名**，因此看不到、也猜不到别人的相册。
- 可为链接设置**有效期**（到期自动失效）与**短口令**（口令以哈希存储，绝不落明文）。
- 在桌面端可随时**撤销**某条链接，使其立即失效。
- token 存储于 `<根目录>/._access_tokens.json`，由桌面端管理，Web 端只读校验。

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
├── tokens.py          # 访问 token 存储与校验（能力 URL）
├── gui.py             # Tkinter 控制面板 + 访问管理 + 程序入口 main()
└── web/
    ├── app.py         # Flask app 与 token 作用域路由
    └── templates.py   # 内嵌 HTML / CSS / SVG 图标
```

## 安全提示 / Security Note

访问控制基于 token（详见上节），相比"猜相册名"已显著加固。但仍需注意以下固有限制：

- **链接即凭证**：能力 URL 本质是 bearer secret，**任何拿到链接的人都能访问**。
  对敏感相册请加设**口令**或**有效期**，并避免在公开渠道分享链接。
- **明文 HTTP**：当前未启用 TLS，链路上的中间人可截获 token 与照片。强加密需配合
  反向代理 / 隧道（如 Caddy、Cloudflare Tunnel）部署，属后续方向。
- **口令未限流**：当前未对口令校验做速率限制，短口令在攻击者已持有 token 时理论上
  可被联网爆破；如需更强口令保护，建议后续加入限流 / 锁定。

请始终确保所选相册根目录下只存放愿意交付的照片。
