#!/usr/bin/env bash
# 在 Linux x86_64 上构建 PicShare（产物为 dist/PicShare/ 目录）
set -euo pipefail
cd "$(dirname "$0")/.."

# 打包 tkinter/customtkinter 需要系统 Tcl/Tk 库（Debian/Ubuntu 示例）
if command -v apt-get >/dev/null 2>&1; then
    sudo apt-get update && sudo apt-get install -y python3-tk tk-dev
fi

python3 -m venv .build-venv
# shellcheck disable=SC1091
source .build-venv/bin/activate

pip install --upgrade pip
pip install -e .
pip install "pyinstaller>=6.0"

pyinstaller picshare.spec --noconfirm --clean

echo ""
echo "✅ 构建完成：dist/PicShare/PicShare"
echo "   整个 dist/PicShare 目录即为可分发产物。"
echo "   运行：./dist/PicShare/PicShare"
