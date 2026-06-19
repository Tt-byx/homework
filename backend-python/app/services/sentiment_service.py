"""
LLM 驱动的情感分析服务
使用 MiMo API 分析文本情感，输出细粒度情感标签和对应的 Live2D 表情。
"""
import json
import logging
from functools import lru_cache

from openai import AsyncOpenAI
from app.core.config import settings

logger = logging.getLogger(__name__)

_client = None


def _get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(
            api_key=settings.mimo_api_key or "not-set",
            base_url=settings.mimo_base_url,
        )
    return _client


SENTIMENT_PROMPT = """分析以下文本的情感倾向。严格按JSON格式返回，不要输出其他内容。

文本：{text}

返回格式：
{{"sentiment": "positive/neutral/negative", "emotion": "happy/surprised/grateful/confused/angry/worried/excited/sad", "confidence": 0.0到1.0}}

说明：
- sentiment: 整体情感极性
- emotion: 细粒度情感类别
- confidence: 置信度

只返回JSON，不要任何解释。"""


# emotion → Live2D 表情映射
EMOTION_EXPRESSION_MAP = {
    "happy": "Smile",
    "excited": "Smile",
    "grateful": "Smile",
    "surprised": "Star",
    "confused": "Circle",
    "angry": "Angry",
    "worried": "Cry",
    "sad": "Cry",
}

# 降级方案：关键词检测
KEYWORD_FALLBACK = {
    "Cry": ["抱歉", "无法", "不知道", "没有找到", "暂时无法", "错误", "失败", "遗憾", "对不起"],
    "Smile": ["恭喜", "太好了", "开心", "高兴", "快乐", "棒", "赞", "喜欢", "美丽", "精彩", "😊", "😄", "欢迎", "祝"],
    "Angry": ["注意", "小心", "警告", "禁止", "危险", "请勿", "不要"],
    "Star": ["？", "吗", "呢", "什么", "怎么", "为什么", "请问"],
}


def _keyword_fallback(text: str) -> dict:
    """关键词降级方案"""
    for expr, keywords in KEYWORD_FALLBACK.items():
        if any(w in text for w in keywords):
            sentiment = "positive" if expr == "Smile" else ("negative" if expr in ("Cry", "Angry") else "neutral")
            return {"sentiment": sentiment, "emotion": "happy" if expr == "Smile" else "confused", "expression": expr, "confidence": 0.5}
    return {"sentiment": "neutral", "emotion": "neutral", "expression": "Normal", "confidence": 0.3}


async def analyze_sentiment(text: str) -> dict:
    """
    分析文本情感，返回 {sentiment, emotion, expression, confidence}
    失败时降级到关键词检测。
    """
    if not text or not text.strip():
        return {"sentiment": "neutral", "emotion": "neutral", "expression": "Normal", "confidence": 0.0}

    # 短文本直接用关键词（节省 API 调用）
    if len(text.strip()) <= 5:
        return _keyword_fallback(text)

    try:
        prompt = SENTIMENT_PROMPT.format(text=text[:200])  # 截断避免 token 浪费
        response = await _get_client().chat.completions.create(
            model=settings.mimo_model,
            messages=[
                {"role": "system", "content": "你是一个情感分析引擎，只返回JSON格式的结果。"},
                {"role": "user", "content": prompt},
            ],
            temperature=0.1,  # 低温度保证一致性
            max_tokens=100,
        )

        content = response.choices[0].message.content or ""
        # 提取 JSON（处理可能的 markdown 包裹）
        content = content.strip()
        if content.startswith("```"):
            content = content.split("\n", 1)[-1].rsplit("```", 1)[0].strip()

        result = json.loads(content)
        emotion = result.get("emotion", "neutral")
        expression = EMOTION_EXPRESSION_MAP.get(emotion, "Normal")

        return {
            "sentiment": result.get("sentiment", "neutral"),
            "emotion": emotion,
            "expression": expression,
            "confidence": float(result.get("confidence", 0.5)),
        }

    except Exception as e:
        logger.warning(f"LLM 情感分析失败，降级到关键词: {e}")
        return _keyword_fallback(text)
