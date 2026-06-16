# 移除 Playwright MCP 配置

**时间：** 2026-06-02 11:15

---

## 提示词

用户请求：将 Playwright MCP 从当前上下文中移除。

---

## 做了哪些事情

### 1. 定位 MCP 配置文件

排查了以下可能的配置位置：
- `~/.claude/settings.json` — 只有 env、statusLine 等设置，无 MCP
- `~/.claude/.mcp.json` — 不存在
- 项目目录 `.mcp.json` — 不存在
- Claude Desktop 配置 — 只有 Electron UI 设置

最终在 `~/.mcp.json`（用户主目录）找到 Playwright 配置。

### 2. 确认原配置内容

```json
{
  "mcpServers": {
    "playwright": {
      "command": "npx",
      "args": ["@playwright/mcp@latest", "--browser", "chromium"],
      "env": {
        "PLAYWRIGHT_BROWSERS_PATH": "C:\\Users\\28182\\AppData\\Local\\ms-playwright"
      }
    }
  }
}
```

### 3. 执行移除

将 `~/.mcp.json` 中的 `playwright` 条目删除，保留空的 `mcpServers` 对象结构。

---

## 产生结果

- Playwright MCP 已从全局配置中移除
- 重启 Claude Code 后生效，playwright 相关工具（19个）将不再加载到上下文中
- 释放约 4k tokens 的上下文空间

---

## 补充说明

- `~/.mcp.json` 是全局级 MCP 配置，影响所有项目的 Claude Code 会话
- 项目级 MCP 配置位于项目目录下的 `.mcp.json` 或 `.claude/settings.json` 中
- 如需恢复，可在 `~/.mcp.json` 中重新添加 playwright 配置
