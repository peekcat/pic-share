# 在 Windows x86_64 上构建 PicShare.exe 并打成安装包
# 用法（PowerShell）：  .\scripts\build-windows.ps1
$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)

python -m venv .build-venv
.\.build-venv\Scripts\Activate.ps1

pip install --upgrade pip
pip install -e .
pip install "pyinstaller>=6.0"

pyinstaller picshare.spec --noconfirm --clean

# 版本号唯一真源在 src/picshare/__init__.py
$version = (python -c "import picshare; print(picshare.__version__)").Trim()

powershell -ExecutionPolicy Bypass -File packaging\windows\make-installer.ps1 -Version $version

Write-Host ""
Write-Host "构建完成："
Write-Host "  dist\PicShare\PicShare.exe                （绿色版，整个文件夹一起拷）"
Write-Host "  dist\PicShare-Setup-$version-x64.exe      （分发用安装包）"
Write-Host ""
Write-Host "安装包未做代码签名，首次运行 SmartScreen 会提示「Windows 已保护你的电脑」，"
Write-Host "点「更多信息」→「仍要运行」即可。"
