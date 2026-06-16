# Phase 2 TTS 语音合成实施

## 提示词

> 这一部分链路跑通，现在离项目跑通是不是还差一个tts语音合成？是的话先压缩上下文，然后规划下一步

## 做了什么

### 1. 改动

| 文件 | 改动 |
|------|------|
| `tts_service.py` | 重写：CosyVoice → MiMo TTS API（mimo-v2.5-tts） |
| `chat.py` | `/chat` 端点加 TTS 调用，回复文字 + 音频 |
| `chat.py` (schema) | ChatResponse 加 `audio` 字段（base64 WAV） |
| `ChatWebSocketHandler.java` | 转发 audio 字段给前端（audio_chunk 事件） |

### 2. MiMo TTS API 格式

```
POST /v1/chat/completions
{
  "model": "mimo-v2.5-tts",
  "messages": [
    {"role": "user", "content": ""},
    {"role": "assistant", "content": "待合成文本"}
  ]
}
→ response.choices[0].message.audio.data (base64 WAV, 24kHz 16bit mono)
```

### 3. 验证

- ✅ Java `mvn clean compile` — BUILD SUCCESS
- ✅ MiMo TTS 直接调用 — 107KB WAV（"你好，欢迎来到灵山胜境"）
- ✅ `/api/chat` 端点 — 返回 reply + audio（base64，约 1.1MB）

## 为什么这样做

MiMo TTS API 无需下载模型，直接用现有 API Key 调用，比本地部署 CosyVoice 简单得多。

## 产生的结果

文字聊天全链路：用户输入 → RAG 检索 → LLM 回答 → TTS 语音合成 → 前端显示文字 + 播放语音。
