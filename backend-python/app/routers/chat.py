from fastapi import APIRouter, HTTPException
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.llm_service import chat_with_rag, chat_with_mimo

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    文字聊天接口（RAG 增强版）
    先从知识库检索相关资料，再调用大模型生成回答
    """
    try:
        reply = await chat_with_rag(request.message)
        return ChatResponse(reply=reply, session_id=request.session_id)
    except Exception as e:
        # RAG 失败时降级到无知识库版本
        try:
            reply = await chat_with_mimo(request.message)
            return ChatResponse(reply=reply, session_id=request.session_id)
        except Exception as e2:
            raise HTTPException(status_code=500, detail=f"AI服务调用失败: {str(e2)}")
