import asyncio
import logging
from openai import AsyncOpenAI
from app.core.config import settings

logger = logging.getLogger(__name__)

_client = None

def _get_client():
    global _client
    if _client is None:
        _client = AsyncOpenAI(
            api_key=settings.embedding_api_key or "not-set",
            base_url=settings.embedding_base_url,
        )
    return _client

BATCH_SIZE = 32


async def embed_texts(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []

    client = _get_client()
    all_embeddings = []
    for i in range(0, len(texts), BATCH_SIZE):
        batch = texts[i : i + BATCH_SIZE]
        # 带重试的 embedding 调用（应对限流）
        for attempt in range(3):
            try:
                response = await client.embeddings.create(
                    model=settings.embedding_model,
                    input=batch,
                )
                batch_embeddings = [item.embedding for item in response.data]
                all_embeddings.extend(batch_embeddings)
                break
            except Exception as e:
                if "429" in str(e) or "rate" in str(e).lower():
                    wait = 2 ** attempt * 2  # 2s, 4s, 8s
                    logger.warning(f"Embedding 限流，等待 {wait}s 后重试 ({attempt+1}/3)")
                    await asyncio.sleep(wait)
                else:
                    raise

    return all_embeddings


async def embed_query(query: str) -> list[float]:
    result = await embed_texts([query])
    return result[0]
