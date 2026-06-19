import asyncio
import logging

import edge_tts

logger = logging.getLogger(__name__)


class TTSService:
    """edge-tts 本地语音合成服务

    使用 Microsoft Edge TTS 引擎，延迟仅 0.3-0.5s/句。
    输出 MP3 格式，前端 Web Audio API 原生支持。
    """

    # 中文语音：晓晓（女声，自然度高）
    VOICE = "zh-CN-XiaoxiaoNeural"

    async def synthesize(self, text: str) -> bytes:
        """将文字合成为 MP3 音频 bytes"""
        if not text or not text.strip():
            return b""

        try:
            communicate = edge_tts.Communicate(text.strip(), self.VOICE)
            audio_data = bytearray()
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    audio_data.extend(chunk["data"])
            return bytes(audio_data) if audio_data else b""
        except Exception as e:
            logger.error(f"edge-tts 合成失败: {e}")
            raise RuntimeError(f"TTS 合成失败: {str(e)}")


tts_service = TTSService()
