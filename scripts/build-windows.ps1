# 在 Windows x86_64 上构建 PicShare.exe
# 用法（PowerShell）：  .\scripts\build-windows.ps1
$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)

python -m venv .build-venv
.\.build-venv\Scripts\Activate.ps1

pip install --upgrade pip
pip install -e .
pip install "pyinstaller>=6.0"

pyinstaller picshare.spec --noconfirm --clean

Write-Host ""
Write-Host "构建完成：dist\PicShare\PicShare.exe"
Write-Host "整个 dist\PicShare 文件夹即为可分发产物（exe 需与同目录依赖一起拷贝）。"
