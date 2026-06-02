# Git 仓库初始化步骤

在 `C:\Users\28182\Desktop\Scenic_Area_Services` 目录下打开 PowerShell，依次执行：

## 步骤 1：初始化 Git 并关联远程仓库

```powershell
cd C:\Users\28182\Desktop\Scenic_Area_Services
git init
git branch -M main
git remote add origin https://github.com/Tt-byx/Scenic_Area_Services.git
git add -A
git commit -m "init: 项目骨架初始化"
git push -u origin main
```

## 步骤 2：建立分支体系

```powershell
# 创建并推送开发分支
git checkout -b dev
git push -u origin dev

# 回到 main 分支（个人分支后面各建各的）
git checkout main
```

## 步骤 3：确认远程仓库连接正确

```powershell
git remote -v
# 应显示：
# origin  https://github.com/Tt-byx/Scenic_Area_Services.git (fetch)
# origin  https://github.com/Tt-byx/Scenic_Area_Services.git (push)
```

## 常见问题

### push 报错 "remote contains work that you do not have locally"
说明 GitHub 上已有内容（比如自动创建了 README），先合并：
```powershell
git pull origin main --rebase
git push -u origin main
```

### 提示 "fatal: refusing to merge unrelated histories"
```powershell
git pull origin main --rebase --allow-unrelated-histories
git push -u origin main
```

### 提示需要登录 GitHub
GitHub 现在不支持密码认证，需要用 Personal Access Token：
1. GitHub → Settings → Developer settings → Personal access tokens → Generate new token
2. 勾选 `repo` 权限
3. push 时用户名填 GitHub 用户名，密码填生成的 token
