from openai import AsyncOpenAI
from app.core.config import settings

_client = None

def _get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(
            api_key=settings.mimo_api_key or "not-set",
            base_url=settings.mimo_base_url,
        )
    return _client

SYSTEM_PROMPT = """你是一个专业的景区导游AI数字人助手。你的职责是为游客提供关于景区的准确、友好的信息和建议。请用简洁、亲切的语气回答游客的问题。如果不确定答案，请诚实地告诉游客。请用中文回答，直接给出答案，不要过多解释推理过程。"""


async def chat_with_mimo(message: str) -> str:
    response = await _get_client().chat.completions.create(
        model=settings.mimo_model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": message},
        ],
        temperature=0.7,
        max_tokens=2048,
    )
    msg = response.choices[0].message
    return msg.content or msg.reasoning_content or ""


async def chat_stream(message: str, context_chunks: list[str] = None):
    system_content = SYSTEM_PROMPT
    if context_chunks:
        context = "\n---\n".join(context_chunks)
        system_content += f"\n\n请根据以下参考资料回答游客的问题。\n\n参考资料：\n{context}"

    response = await _get_client().chat.completions.create(
        model=settings.mimo_model,
        messages=[
            {"role": "system", "content": system_content},
            {"role": "user", "content": message},
        ],
        temperature=0.7,
        max_tokens=2048,
        stream=True,
    )

    async for chunk in response:
        if chunk.choices:
            delta = chunk.choices[0].delta
            text = delta.content or delta.reasoning_content
            if text:
                yield text
