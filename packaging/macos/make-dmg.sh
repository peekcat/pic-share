#!/usr/bin/env bash
# 把 dist/PicShare.app 打成可拖拽安装的 DMG。
#
# 用法：packaging/macos/make-dmg.sh <version> <arch>
#   例：packaging/macos/make-dmg.sh 0.9.2 arm64  →  dist/PicShare-0.9.2-macos-arm64.dmg
#
# 只用系统自带的 codesign / hdiutil，不引入 create-dmg 之类依赖——
# 那些工具靠 AppleScript 摆 Finder 窗口，在没有 GUI 会话的 CI runner 上容易挂。
set -euo pipefail

VERSION="${1:?用法: make-dmg.sh <version> <arch>}"
ARCH="${2:?用法: make-dmg.sh <version> <arch>}"

cd "$(dirname "$0")/../.."
APP="dist/PicShare.app"
DMG="dist/PicShare-${VERSION}-macos-${ARCH}.dmg"

[ -d "$APP" ] || { echo "❌ 找不到 $APP，先跑 pyinstaller picshare.spec" >&2; exit 1; }

# ad-hoc 签名。没有 Apple 开发者证书（$99/年）时这是免费能做的上限：
# 它不会消除首次打开的警告，但能让签名内部自洽——未签名的 bundle 被 Gatekeeper
# 拦下时报的是「已损坏，无法打开」，用户根本找不到放行入口；ad-hoc 签过之后
# 报的是「无法验证开发者」，可以在系统设置里点「仍要打开」。
echo "→ ad-hoc 签名 $APP"
codesign --force --deep --sign - "$APP"
codesign --verify --deep --strict "$APP" 2>&1 || echo "⚠️  签名校验有告警（ad-hoc 签名常见，通常不影响运行）"

STAGE="$(mktemp -d)"
trap 'rm -rf "$STAGE"' EXIT

# 用 ditto 而非 cp，保留符号链接、扩展属性和资源分叉
ditto "$APP" "$STAGE/PicShare.app"
ln -s /Applications "$STAGE/应用程序"

cat > "$STAGE/首次打开说明.txt" <<'TXT'
PicShare 安装说明
==================

1) 把 PicShare 拖到旁边的「应用程序」文件夹。
2) 在启动台或「应用程序」里点击 PicShare 启动。


首次打开提示「无法打开，因为 Apple 无法检查其是否包含恶意软件」怎么办？
------------------------------------------------------------------

PicShare 没有购买 Apple 开发者签名，macOS 对所有未签名 App 都会这样提示，
与软件本身是否安全无关。放行方式二选一：

方式一（推荐）
  先双击一次 PicShare（会被拦下），然后打开
  系统设置 → 隐私与安全性 → 往下滚动 → 点「仍要打开」。
  macOS 13 及更早：系统偏好设置 → 安全性与隐私 → 通用 → 「仍要打开」。

方式二（终端一行命令）
  xattr -dr com.apple.quarantine /Applications/PicShare.app

放行一次之后，以后打开就都正常了。

项目主页：https://github.com/peekcat/pic-share
TXT

rm -f "$DMG"
echo "→ 生成 $DMG"
# -fs HFS+：显式指定，避免新系统默认出 APFS 格式的 DMG（老 macOS 挂不上）
hdiutil create \
    -volname "PicShare ${VERSION}" \
    -srcfolder "$STAGE" \
    -fs HFS+ \
    -format UDZO \
    -ov \
    "$DMG" >/dev/null

echo "✅ $DMG"
