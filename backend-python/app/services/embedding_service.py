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
        response = await client.embeddings.create(
            model=settings.embedding_model,
            input=batch,
        )
        batch_embeddings = [item.embedding for item in response.data]
        all_embeddings.extend(batch_embeddings)

    return all_embeddings


async def embed_query(query: str) -> list[float]:
    result = await embed_texts([query])
    return result[0]
