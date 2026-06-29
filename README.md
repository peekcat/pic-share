# PicShare Lite

基于 IPv6 的私有照片共享服务器。把本地一个文件夹变成可通过浏览器访问的在线相册,
通过公网 IPv6 地址直接分享,无需公网 IPv4 或内网穿透。

特性:极速预览 · 智能缓存 · RAW 支持 · 收藏标记 · iOS 风格界面。

## 安装

```bash
pip install -e .
```

可选依赖:RAW 文件转码需要系统安装 [ImageMagick](https://imagemagick.org)
(命令行 `magick` 需在 PATH 中)。

## 运行

```bash
picshare
# 或
python -m picshare
```

启动后在桌面 GUI 中:

1. 点击「选择」指定相册根目录(存放各相册子文件夹的主目录)。
2. 确认底部显示「检测到 IPv6 地址」。
3. 复制 `http://[...]:5000` 地址,在手机/电脑浏览器中访问。
4. 在网页输入根目录下的子文件夹名(相册名)即可浏览。

## 目录结构

```
src/picshare/
├── __main__.py        # python -m picshare 入口
├── config.py          # ServerState 配置、扩展名集合
├── status.py          # 状态广播(GUI 与后台模块解耦点)
├── paths.py           # safe_join 路径安全工具
├── network.py         # IPv6 地址检测
├── preview.py         # 缩略图 / RAW 预览生成
├── gui.py             # Tkinter 控制面板 + 程序入口 main()
└── web/
    ├── app.py         # Flask app 与路由
    └── templates.py   # 内嵌 HTML / CSS / SVG 图标
```

## 安全提示

本服务**没有访问密码**,安全性依赖 IPv6 地址的复杂性。请确保所选相册根目录下
只存放愿意公开的照片,并谨慎分享访问地址。
