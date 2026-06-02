#!/usr/bin/env pwsh
# ============================================
# 景区导览 AI 数字人项目 Git 初始化脚本
# 使用方式：在项目根目录下打开 PowerShell，运行 .\git-init.ps1
# ============================================

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  景区导览 AI 数字人 - Git 仓库初始化" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# 确认当前位置
$currentDir = Get-Location
Write-Host "当前目录: $currentDir" -ForegroundColor Yellow
Write-Host ""

# Step 1: 初始化 Git
if (Test-Path ".git") {
    Write-Host "[1/5] Git 仓库已存在，跳过初始化" -ForegroundColor Green
} else {
    Write-Host "[1/5] 初始化 Git 仓库..." -ForegroundColor Yellow
    git init
    if ($LASTEXITCODE -ne 0) { Write-Host "Error: git init failed" -ForegroundColor Red; exit 1 }
    Write-Host "  -> 初始化完成" -ForegroundColor Green
}
Write-Host ""

# Step 2: 创建项目目录骨架（如果不存在）
Write-Host "[2/5] 创建项目目录骨架..." -ForegroundColor Yellow

$dirs = @(
    "frontend",
    "backend-java",
    "backend-python",
    "docker",
    "doc"
)

foreach ($dir in $dirs) {
    if (-not (Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
        Write-Host "  -> 创建目录: $dir/" -ForegroundColor Gray
    } else {
        Write-Host "  -> 目录已存在: $dir/" -ForegroundColor Gray
    }
}

# 在空目录中放 .gitkeep（Git 不能追踪空目录）
foreach ($dir in $dirs) {
    $gitkeepPath = Join-Path $dir ".gitkeep"
    if (-not (Test-Path $gitkeepPath)) {
        New-Item -ItemType File -Path $gitkeepPath -Force | Out-Null
    }
}
Write-Host "  -> 目录骨架就绪" -ForegroundColor Green
Write-Host ""

# Step 3: 设置主分支为 main
Write-Host "[3/5] 设置默认分支为 main..." -ForegroundColor Yellow
git branch -M main 2>$null
Write-Host "  -> 已设置" -ForegroundColor Green
Write-Host ""

# Step 4: 添加远程仓库
Write-Host "[4/5] 配置远程仓库..." -ForegroundColor Yellow
$remoteUrl = "https://github.com/Tt-byx/Scenic_Area_Services.git"

# 检查是否已有 origin
$existingRemote = git remote get-url origin 2>$null
if ($existingRemote) {
    Write-Host "  -> 远程 origin 已存在: $existingRemote" -ForegroundColor Gray
    if ($existingRemote -ne $remoteUrl) {
        Write-Host "  -> 更新 origin 地址为 $remoteUrl" -ForegroundColor Yellow
        git remote set-url origin $remoteUrl
    }
} else {
    git remote add origin $remoteUrl
    Write-Host "  -> 已添加远程仓库: $remoteUrl" -ForegroundColor Green
}
Write-Host ""

# Step 5: 首次提交
Write-Host "[5/5] 创建首次提交..." -ForegroundColor Yellow
$hasCommits = git log --oneline -1 2>$null
if ($hasCommits) {
    Write-Host "  -> 已有提交历史，跳过" -ForegroundColor Green
} else {
    git add -A
    $commitMsg = @"
init: 项目骨架初始化

- 初始化 Vue3 / Spring Boot / FastAPI 三端项目结构
- 添加 README.md、.gitignore、CLAUDE.md 等基础文件
- 添加题目原文（题目.md）
- 配置远程仓库关联
"@
    git commit -m $commitMsg
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  -> 没有新文件需要提交，跳过" -ForegroundColor Yellow
    } else {
        Write-Host "  -> 首次提交完成" -ForegroundColor Green
    }
}
Write-Host ""

# 完成提示
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  初始化完成！" -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "后续步骤：" -ForegroundColor Yellow
Write-Host "  1. 推送到远程仓库（首次需要加 -u）：" -ForegroundColor White
Write-Host "     git push -u origin main" -ForegroundColor Green
Write-Host ""
Write-Host "  2. 创建开发分支：" -ForegroundColor White
Write-Host "     git checkout -b dev" -ForegroundColor Green
Write-Host "     git push -u origin dev" -ForegroundColor Green
Write-Host ""
Write-Host "  3. 创建个人分支（替换 your-name）：" -ForegroundColor White
Write-Host "     git checkout -b your-name dev" -ForegroundColor Green
Write-Host "     git push -u origin your-name" -ForegroundColor Green
Write-Host ""
Write-Host "  提示：如果 GitHub 上已有内容，先执行 git pull origin main --rebase 再 push" -ForegroundColor Gray
Write-Host ""
