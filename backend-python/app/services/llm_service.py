from openai import AsyncOpenAI
from app.core.config import settings

# 创建 OpenAI 兼容客户端，指向 MiMo API
client = AsyncOpenAI(
    api_key=settings.mimo_api_key,
    base_url=settings.mimo_base_url,
)

SYSTEM_PROMPT = """你是一个专业的景区导览AI数字人助手。
你的职责是为游客提供关于景区的准确、友好的信息和建议。
请用简洁、亲切的语气回答游客的问题。
如果不确定答案，请诚实告知。"""


async def chat_with_mimo(message: str) -> str:
    """调用 MiMo 大模型 API（OpenAI 兼容格式）- 无知识库版本"""
    response = await client.chat.completions.create(
        model=settings.mimo_model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": message},
        ],
        temperature=0.7,
        max_tokens=1024,
    )
    return response.choices[0].message.content


async def chat_with_rag(message: str) -> str:
    """RAG 增强对话：检索知识库 → 拼接上下文 → 调用大模型"""
    from app.services.rag_service import retrieve_context, build_rag_prompt

    context = await retrieve_context(message)
    messages = build_rag_prompt(context, message)

    response = await client.chat.completions.create(
        model=settings.mimo_model,
        messages=messages,
        temperature=0.7,
        max_tokens=1024,
    )
    return response.choices[0].message.content
