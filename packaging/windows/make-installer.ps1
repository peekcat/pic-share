# 把 dist\PicShare\ 打成 Inno Setup 安装包。
#
# 用法： powershell -ExecutionPolicy Bypass -File packaging\windows\make-installer.ps1 -Version 0.9.2
# 产物： dist\PicShare-Setup-<version>-x64.exe
#
# 前置：先跑过 `pyinstaller picshare.spec`。
param(
    [Parameter(Mandatory = $true)][string]$Version
)

$ErrorActionPreference = "Stop"
Set-Location (Split-Path (Split-Path $PSScriptRoot -Parent) -Parent)

if (-not (Test-Path "dist\PicShare\PicShare.exe")) {
    throw "找不到 dist\PicShare\PicShare.exe，先跑 pyinstaller picshare.spec"
}

function Resolve-Iscc {
    $cmd = Get-Command iscc.exe -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }
    # GitHub Actions 的 windows runner 镜像自带 Inno Setup，但不在 PATH 里
    foreach ($base in @(${env:ProgramFiles(x86)}, $env:ProgramFiles)) {
        if (-not $base) { continue }
        foreach ($ver in @("Inno Setup 6", "Inno Setup 7")) {
            $p = Join-Path $base "$ver\ISCC.exe"
            if (Test-Path $p) { return $p }
        }
    }
    return $null
}

$iscc = Resolve-Iscc
if (-not $iscc) {
    Write-Host "未找到 Inno Setup，正在安装..."
    choco install innosetup -y --no-progress
    $iscc = Resolve-Iscc
}
if (-not $iscc) { throw "Inno Setup 安装后仍找不到 ISCC.exe" }

Write-Host "使用编译器: $iscc"
& $iscc "packaging\windows\picshare.iss" "/DMyAppVersion=$Version"
if ($LASTEXITCODE -ne 0) { throw "ISCC 编译失败 (exit $LASTEXITCODE)" }

Write-Host ""
Write-Host "✅ dist\PicShare-Setup-$Version-x64.exe"
