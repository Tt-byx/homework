# 项目经历：景区导览 AI 数字人系统

---

## 一、项目描述

### 项目背景

本项目是第十五届中国软件杯 A 组赛题（出题方：锐捷网络），要求构建一个面向景区场景的 AI 数字人导览系统。传统景区导览依赖人工讲解员和静态指示牌，存在服务覆盖不足、无法个性化推荐、交互体验单一等痛点。本项目旨在通过大模型 + RAG + 语音交互 + 数字人技术，打造一个 7×24 小时在线的智能虚拟导游。

### 项目目标

- 游客通过语音或文字与数字人对话，获取景区知识问答和个性化路线推荐
- 数字人具备口型同步、表情变化、语音播报等拟人化交互体验
- 知识库准确率 ≥ 90%，语音问答端到端延迟 < 5 秒
- 管理后台提供知识库管理、数据大屏、对话分析等运营能力

### 项目概述

系统采用前后端分离的三端架构：Vue 3 游客端/管理后台、Spring Boot Java 网关后端、FastAPI Python AI 后端。核心链路为：用户输入（文字/语音）→ RAG 知识检索 → 大模型生成回答 → TTS 语音合成 → Live2D 数字人口型同步播报。知识库基于景区文档构建，通过 Embedding 向量化 + ChromaDB 向量检索实现精准问答。

---

## 二、项目职责

### 角色

独立开发者，负责系统架构设计、三端开发、AI 能力集成、联调测试全流程。

### 遇到的痛点与解决方案

#### 痛点 1：RAG 知识检索准确率不达标

**问题：** 初始方案使用 ChromaDB 内置的 embedding 模型进行文本向量化，中文语义检索效果差，相关文档无法被正确召回。

**解决：** 引入 SiliconFlow 平台的 BAAI/bge-m3 模型作为外部 Embedding 服务（OpenAI 兼容格式），将文档和查询分别向量化后通过 cosine 相似度检索。同时优化文本切片策略（300-500 字 chunk，50 字重叠）和 system prompt（防幻觉指令 + 结构化回答格式），最终准确率从 60% 提升至 90%。

#### 痛点 2：语音全链路延迟过高

**问题：** 最初方案使用 FunASR（本地部署）+ CosyVoice（本地部署），模型加载需要 35 秒，且受系统代理阻断模型下载影响。

**解决：** 统一替换为 MiMo API（mimo-v2.5-asr + mimo-v2.5-tts），零本地模型依赖，API 调用秒级响应。同时实现 TTS 按句合成——LLM 生成文本后按句号分句，逐句调用 TTS 并即时推送音频，首句语音播放延迟从 5 秒降至 1.5 秒。

#### 痛点 3：数字人口型同步效果不自然

**问题：** 简单的音量 RMS 驱动口型开合，无法体现不同汉字的嘴型差异（如"啊"大张嘴 vs"衣"扁嘴）。

**解决：** 实现双模式口型同步系统——文字口型模式（基于汉字韵母映射表，覆盖 200+ 常用汉字的嘴形参数）和音频口型模式（Web Audio API AnalyserNode 实时分析）。音频播放时自动切换到音频驱动，播放结束后回退到文字驱动，保证口型与语音/文字的实时同步。

#### 痛点 4：Java HttpClient 转发 multipart 请求失败

**问题：** Java WebSocket handler 使用 `java.net.http.HttpClient` 手动构建 multipart/form-data 请求转发到 Python，Python 端无法解析 body（返回 422 验证错误）。

**解决：** 排查发现 HttpClient 的 `BodyPublishers.ofString()` 发送的 multipart 编码与 python-multipart 库不兼容。改用 Spring 的 `RestTemplate` + `HttpEntity<LinkedMultiValueMap>` 自动处理 multipart 编码，问题解决。文字消息改用 JSON 格式直调 `/api/chat`，音频消息用 RestTemplate 的 multipart 支持。

#### 痛点 5：Windows 端口冲突导致服务无法启动

**问题：** Python 后端绑定 8000 端口时报 WinError 10013，排查发现端口 7955-8054 被 Windows Hyper-V 动态保留。

**解决：** 改用 9000 端口，统一修改三端配置（Python config、Java application.yml、Vite proxy）。同时在 ASR 模型加载时临时清除系统 SOCKS5 代理环境变量，避免代理阻断模型下载。

---

## 三、项目业绩

### 目标达成情况

| 评分项 | 分值 | 达成情况 |
|--------|------|---------|
| 功能完整度 | 40分 | 6 个 Phase 全部完成，文字/语音问答、数字人交互、路线推荐、管理后台全部跑通 |
| 技术与创新性 | 30分 | RAG 准确率 90%（20 题测试集 18 题正确），Live2D 数字人口型同步 |
| 行业体验 | 20分 | 语音输入→文字确认→发送、数字人表情随情感变化、路线快捷推荐 |
| 文档质量 | 10分 | 设计文档 + PPT + 演示视频（待完成） |

### 我的贡献

- **架构设计：** 设计三端分离架构（Vue 3 → Spring Boot → FastAPI），Java 作为唯一网关，Python 专注 AI 能力，职责清晰
- **RAG 知识库：** 实现完整的文档解析→切片→向量化→检索→生成链路，准确率 90%
- **语音交互：** 集成 MiMo ASR/TTS API，实现录音→识别→问答→语音播报全链路
- **数字人系统：** 集成 Live2D Cubism SDK，实现口型同步（文字+音频双模式）、12 种表情/姿势、鼠标交互
- **管理后台：** 实现知识库管理（上传/列表/删除/重处理）、ECharts 数据大屏（4 指标卡片 + 3 图表）、对话记录查看
- **工程实践：** 处理了 CORS 跨域、端口冲突、代理阻断、multipart 编码兼容等实际部署问题

### 我的收获

1. **全栈能力提升：** 独立完成 Vue 3 + Spring Boot + FastAPI 三端开发，对前后端分离架构有了深入理解
2. **AI 工程化经验：** 掌握了 RAG（检索增强生成）的完整实现流程，理解了 Embedding 向量化、向量数据库检索、Prompt 工程等核心技术
3. **语音技术实践：** 了解了 ASR/TTS 的 API 调用方式和流式处理优化（按句合成减少延迟）
4. **问题排查能力：** 解决了多个跨平台、跨语言的实际工程问题（Windows 端口保留、代理阻断、multipart 编码兼容、BOM 编码等）
5. **数字人技术探索：** 学习了 Live2D Cubism SDK 的集成、口型同步算法（韵母→嘴形映射）、Web Audio API 的实时音频分析

---

## 四、技术栈详解

### 前端（Vue 3）

| 技术 | 用途 |
|------|------|
| Vue 3 + Composition API | 页面框架，响应式数据管理 |
| Pinia | 状态管理（聊天消息、WebSocket 连接、音频播放状态） |
| Element Plus | UI 组件库（按钮、表格、标签、消息提示） |
| ECharts | 数据大屏可视化（趋势折线图、情感饼图、热门问题柱状图） |
| Live2D Cubism SDK | 2D 数字人渲染（WebGL Canvas、物理模拟、表情系统） |
| Web Audio API | 音频播放 + AnalyserNode 实时口型同步 |
| MediaRecorder API | 浏览器录音（PCM → WAV 编码） |
| WebSocket | 双向实时通信（文字/音频消息收发） |

### Java 后端（Spring Boot）

| 技术 | 用途 |
|------|------|
| Spring Boot 3.3.5 | Web 框架，REST API + WebSocket |
| MyBatis-Plus 3.5.7 | ORM，自动生成 CRUD，LambdaQueryWrapper |
| MySQL 8.0 | 数据库（5 张表：用户、景点、会话、消息、知识文档） |
| RestTemplate | 调用 Python 后端 API（文字聊天、文档处理） |
| WebSocket | 实时双向通信，转发文字/音频到 Python，回传结果到前端 |
| @Async | 异步文档处理（上传后后台调用 Python 解析+向量化） |

### Python 后端（FastAPI）

| 技术 | 用途 |
|------|------|
| FastAPI | 异步 Web 框架，REST API + SSE 流式输出 |
| OpenAI SDK | 调用 MiMo API（LLM/ASR/TTS，OpenAI 兼容格式） |
| ChromaDB | 向量数据库（持久化存储，cosine 相似度检索） |
| SiliconFlow BAAI/bge-m3 | Embedding 模型（1024 维向量化，中文语义理解） |
| python-docx / openpyxl | 文档解析（Word/Excel → 纯文本） |

### AI 服务

| 服务 | 模型 | 提供方 |
|------|------|--------|
| LLM 大模型 | mimo-v2.5-pro | 小米 MiMo API |
| ASR 语音识别 | mimo-v2.5-asr | 小米 MiMo API |
| TTS 语音合成 | mimo-v2.5-tts | 小米 MiMo API |
| 文本 Embedding | BAAI/bge-m3 | 硅基流动 SiliconFlow |

### 关键技术亮点

1. **RAG 检索增强生成：** 文档→切片→Embedding→向量存储→检索→Prompt 注入→LLM 生成，防幻觉指令确保回答基于知识库
2. **双模式口型同步：** 文字口型（汉字韵母→嘴形映射表 200+ 字）+ 音频口型（AnalyserNode RMS 实时分析），自动切换
3. **情感驱动表情：** Python 关键词情感检测→expression 字段→WebSocket 传输→Live2D 表情切换
4. **TTS 按句合成：** LLM 流式生成→按句号分句→逐句 TTS→即时推送音频，减少首句播放延迟
5. **三端统一 AI 网关：** Java 作为唯一前端入口，转发到 Python AI 后端，职责分离清晰
