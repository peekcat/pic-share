#!/usr/bin/env bash
# 在 Apple Silicon (arm64) Mac 上构建 PicShare.app
set -euo pipefail
cd "$(dirname "$0")/.."

python3 -m venv .build-venv
# shellcheck disable=SC1091
source .build-venv/bin/activate

pip install --upgrade pip
pip install -e .
pip install "pyinstaller>=6.0"

pyinstaller picshare.spec --noconfirm --clean

echo ""
echo "✅ 构建完成：dist/PicShare.app"
echo "   首次打开若提示「来自身份不明的开发者」，右键 → 打开，或："
echo "   xattr -dr com.apple.quarantine dist/PicShare.app"
