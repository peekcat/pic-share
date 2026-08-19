#!/usr/bin/env bash
# 在 Mac 上构建 PicShare.app 并打成可拖拽安装的 DMG
set -euo pipefail
cd "$(dirname "$0")/.."

python3 -m venv .build-venv
# shellcheck disable=SC1091
source .build-venv/bin/activate

pip install --upgrade pip
pip install -e .
pip install "pyinstaller>=6.0"

pyinstaller picshare.spec --noconfirm --clean

# 版本号唯一真源在 src/picshare/__init__.py
VERSION="$(python -c 'import picshare; print(picshare.__version__)')"
# 文件名里统一用 arm64 / x64，和 CI 产物命名保持一致
case "$(uname -m)" in
    arm64)  ARCH="arm64" ;;
    x86_64) ARCH="x64" ;;
    *)      ARCH="$(uname -m)" ;;
esac

packaging/macos/make-dmg.sh "$VERSION" "$ARCH"

echo ""
echo "✅ 构建完成："
echo "   dist/PicShare.app                              （直接运行用）"
echo "   dist/PicShare-${VERSION}-macos-${ARCH}.dmg     （分发用）"
echo ""
echo "   包未经 Apple 签名/公证，首次打开会提示「无法验证开发者」，"
echo "   在 系统设置 → 隐私与安全性 → 仍要打开，或："
echo "   xattr -dr com.apple.quarantine /Applications/PicShare.app"
