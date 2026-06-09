import asyncio
import base64
import logging

from openai import AsyncOpenAI
from app.core.config import settings

logger = logging.getLogger(__name__)

# 复用 MiMo API 客户端（与 LLM 同一个 base_url 和 api_key）
_client = None


def _get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(
            api_key=settings.mimo_api_key or "not-set",
            base_url=settings.mimo_base_url,
        )
    return _client


class TTSService:
    """MiMo TTS 语音合成服务

    调用 MiMo mimo-v2.5-tts 模型，通过 /v1/chat/completions 端点。
    请求格式：messages 中 assistant 角色的 content 为待合成文本。
    响应格式：response.choices[0].message.audio.data 为 base64 编码的 WAV。
    """

    TTS_MODEL = "mimo-v2.5-tts"

    async def synthesize(self, text: str) -> bytes:
        """将文字合成为 WAV 音频 bytes"""
        if not text or not text.strip():
            return b""

        try:
            response = await _get_client().chat.completions.create(
                model=self.TTS_MODEL,
                messages=[
                    {"role": "user", "content": ""},
                    {"role": "assistant", "content": text},
                ],
            )

            # 音频数据在 response.choices[0].message.audio.data (base64)
            audio_data = response.choices[0].message.audio.data
            return base64.b64decode(audio_data)

        except Exception as e:
            logger.error(f"MiMo TTS 失败: {e}")
            raise RuntimeError(f"TTS 合成失败: {str(e)}")

    async def synthesize_sentences(self, text: str) -> list[bytes]:
        """按句分割文本，逐句合成，返回音频列表

        用于减少单次请求的文本长度，提高响应速度。
        """
        if not text or not text.strip():
            return []

        # 按中文标点分句
        sentences = []
        current = ""
        for char in text:
            current += char
            if char in "。！？；\n":
                if current.strip():
                    sentences.append(current.strip())
                current = ""
        if current.strip():
            sentences.append(current.strip())

        if not sentences:
            return []

        # 逐句合成
        results = []
        for sentence in sentences:
            try:
                audio = await self.synthesize(sentence)
                if audio:
                    results.append(audio)
            except Exception as e:
                logger.warning(f"句子 TTS 失败: {e}")
                continue

        return results


tts_service = TTSService()
