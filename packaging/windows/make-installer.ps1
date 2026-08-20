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

# 简体中文语言包。Inno Setup 6.x 把它归在「非官方翻译」里，不随编译器安装
# （GitHub runner 的 6.7.1 上确实没有），7.x 起才转正。
# 优先用编译器自带的那份——版本必然匹配；没有就退回仓库自带的副本。
$isl = $null
$builtin = Join-Path (Split-Path $iscc -Parent) "Languages\ChineseSimplified.isl"
$vendored = Join-Path $PSScriptRoot "ChineseSimplified.isl"
if (Test-Path $builtin) {
    $isl = $builtin
} elseif (Test-Path $vendored) {
    $isl = $vendored
}

$isccArgs = @("packaging\windows\picshare.iss", "/DMyAppVersion=$Version")
if ($isl) {
    Write-Host "中文语言包: $isl"
    $isccArgs += "/DChineseIsl=$isl"
} else {
    # 语言缺失不值得让整个构建挂掉，降级成英文界面并说清楚
    Write-Warning "找不到 ChineseSimplified.isl，安装界面将只有英文"
}

& $iscc $isccArgs
if ($LASTEXITCODE -ne 0) { throw "ISCC 编译失败 (exit $LASTEXITCODE)" }

Write-Host ""
Write-Host "✅ dist\PicShare-Setup-$Version-x64.exe"
