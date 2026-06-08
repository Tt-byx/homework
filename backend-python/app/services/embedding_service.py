import logging
from openai import AsyncOpenAI
from app.core.config import settings

logger = logging.getLogger(__name__)

client = AsyncOpenAI(
    api_key=settings.embedding_api_key,
    base_url=settings.embedding_base_url,
)

BATCH_SIZE = 32


async def embed_texts(texts: list[str]) -> list[list[float]]:
    """批量 embedding 文本列表"""
    if not texts:
        return []

    all_embeddings = []
    for i in range(0, len(texts), BATCH_SIZE):
        batch = texts[i : i + BATCH_SIZE]
        response = await client.embeddings.create(
            model=settings.embedding_model,
            input=batch,
        )
        batch_embeddings = [item.embedding for item in response.data]
        all_embeddings.extend(batch_embeddings)
        logger.info(f"Embedding 进度: {min(i + BATCH_SIZE, len(texts))}/{len(texts)}")

    return all_embeddings


async def embed_query(query: str) -> list[float]:
    """单条查询的 embedding"""
    result = await embed_texts([query])
    return result[0]
