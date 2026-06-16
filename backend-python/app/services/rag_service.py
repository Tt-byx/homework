import logging
from app.core.config import settings
from app.services.embedding_service import embed_query
from app.services.vector_store import query as chroma_query

logger = logging.getLogger(__name__)

DISTANCE_THRESHOLD = 0.7  # cosine 距离阈值，越小越相关


async def retrieve_context(query: str, top_k: int = None) -> str:
    """检索知识库，返回格式化的上下文文本"""
    if top_k is None:
        top_k = settings.rag_top_k

    try:
        query_embedding = await embed_query(query)
        results = chroma_query(query_embedding, top_k=top_k)
    except Exception as e:
        logger.warning(f"知识库检索失败，将使用无上下文模式: {e}")
        return ""

    if not results:
        return ""

    context_parts = []
    for i, r in enumerate(results):
        if r["distance"] > DISTANCE_THRESHOLD:
            continue
        context_parts.append(
            f"【参考资料{i + 1}】(来源: {r['doc_title']})\n{r['text']}"
        )

    if not context_parts:
        logger.info(f"检索到 {len(results)} 个 chunk，但相似度均低于阈值，跳过上下文注入")
        return ""

    context = "\n\n".join(context_parts)
    logger.info(f"检索到 {len(context_parts)} 条相关资料")
    return context


def build_rag_prompt(context: str, query: str) -> list[dict]:
    """组装带知识库上下文的消息列表"""
    system_content = (
        "你是一个专业的景区导览AI数字人助手。\n"
        "你的职责是为游客提供关于景区的准确、友好的信息和建议。\n\n"
        "【回答格式要求——必须严格遵守】\n"
        "1. 禁止使用任何 Markdown 格式符号：不要用 **、*、#、-、1.、```、>、| 等符号。\n"
        "2. 用纯文本、口语化的方式回答，就像一个真人导游在面对面跟游客聊天。\n"
        "3. 如果需要列举，用「第一、第二」或「首先、其次」等自然语言连接，不要用编号列表。\n"
        "4. 回答要简洁，控制在3-5句话，避免长篇大论。\n"
        "5. 用中文回答。\n\n"
        "【重要规则】\n"
        "1. 你必须仅根据以下参考资料回答问题。不要编造或推测资料中没有的信息。\n"
        "2. 如果参考资料中没有相关信息，请诚实告知「根据现有资料，我暂时无法回答这个问题」。\n"
        "3. 适当引用具体景点名称和数据，增加回答的可信度。\n\n"
        "【路线推荐】\n"
        "当游客询问推荐路线时，用口语化方式介绍：先说路线名称、适合人群和预计时长，然后按顺序用「首先、接着、然后、最后」介绍每个站点，最后给温馨提示。"
    )

    if context:
        system_content += f"\n\n【参考资料】\n{context}"
    else:
        system_content += "\n\n【注意】当前知识库中没有找到与问题相关的资料，请告知用户你暂时无法回答。"

    return [
        {"role": "system", "content": system_content},
        {"role": "user", "content": query},
    ]
