import base64
import json
import logging

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from fastapi.responses import StreamingResponse, Response
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.llm_service import chat_with_rag, chat_with_mimo, chat_stream
from app.services.asr_service import asr_service
from app.services.tts_service import tts_service
from app.services.rag_service import retrieve_context

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """文字聊天接口（RAG 增强 + TTS 语音合成）"""
    try:
        reply = await chat_with_rag(request.message)
    except Exception:
        try:
            reply = await chat_with_mimo(request.message)
        except Exception as e2:
            raise HTTPException(status_code=500, detail=f"AI服务调用失败: {str(e2)}")

    # TTS 语音合成
    audio_b64 = None
    try:
        audio_bytes = await tts_service.synthesize(reply)
        if audio_bytes:
            audio_b64 = base64.b64encode(audio_bytes).decode()
    except Exception as e:
        logger.warning(f"TTS 合成失败（不影响文字回复）: {e}")

    return ChatResponse(reply=reply, session_id=request.session_id, audio=audio_b64)


@router.post("/asr")
async def asr_endpoint(audio: UploadFile = File(...)):
    """ASR: 语音转文字（MiMo ASR API）"""
    try:
        audio_bytes = await audio.read()
        audio_format = audio.filename.split('.')[-1] if audio.filename else "wav"
        text = await asr_service.transcribe(audio_bytes, audio_format)
        return {"text": text, "format": audio_format}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"ASR error: {str(e)}")


@router.post("/tts")
async def tts_endpoint(
    text: str = Form(...),
    speaker: str = Form("中文女")
):
    """TTS: 文字转语音"""
    try:
        audio_bytes = await tts_service.synthesize(text, speaker)
        return Response(
            content=audio_bytes,
            media_type="audio/wav",
            headers={"Content-Disposition": "attachment; filename=tts_output.wav"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"TTS error: {str(e)}")


@router.post("/chat/stream")
async def chat_stream_endpoint(
    message: str = Form(None),
    audio: UploadFile = File(None),
    session_id: str = Form(None),
):
    """流式对话接口（支持文字和语音输入，流式输出文字+语音）"""
    async def event_generator():
        input_text = message
        full_text = ""

        # 如果有音频输入，先 ASR 识别
        if audio is not None:
            try:
                audio_bytes = await audio.read()
                audio_format = audio.filename.split('.')[-1] if audio.filename else "webm"
                input_text = await asr_service.transcribe(audio_bytes, audio_format)
                yield _sse_event("asr_result", {"text": input_text})
            except Exception as e:
                logger.error(f"ASR failed: {e}")
                yield _sse_event("error", {"message": f"ASR 识别失败: {str(e)}"})
                yield _sse_event("done", {"session_id": session_id, "total_text": ""})
                return

        if not input_text or not input_text.strip():
            yield _sse_event("error", {"message": "输入为空"})
            yield _sse_event("done", {"session_id": session_id, "total_text": ""})
            return

        # RAG 检索知识库
        context_chunks = []
        try:
            context_str = await retrieve_context(input_text)
            if context_str:
                context_chunks = [context_str]
        except Exception as e:
            logger.warning(f"RAG search failed: {e}")

        # 流式生成回答 + 逐句合成语音
        sentence_buffer = ""
        end_marks = set("。！？；\n")

        try:
            async for text_chunk in chat_stream(input_text, context_chunks):
                sentence_buffer += text_chunk
                full_text += text_chunk
                yield _sse_event("text_chunk", {"text": text_chunk})

                # 遇到句号等标点，合成这一句的语音
                if sentence_buffer and sentence_buffer[-1] in end_marks:
                    sentence = sentence_buffer.strip()
                    if sentence:
                        try:
                            audio_bytes = await tts_service.synthesize(sentence)
                            if audio_bytes:
                                audio_b64 = base64.b64encode(audio_bytes).decode()
                                yield _sse_event("audio_chunk", {
                                    "audio": audio_b64,
                                    "format": "wav"
                                })
                        except Exception as e:
                            logger.warning(f"TTS failed: {e}")
                    sentence_buffer = ""

        except Exception as e:
            logger.error(f"LLM failed: {e}")
            yield _sse_event("error", {"message": f"AI error: {str(e)}"})

        # 处理剩余未合成的文本
        if sentence_buffer.strip():
            try:
                audio_bytes = await tts_service.synthesize(sentence_buffer.strip())
                if audio_bytes:
                    audio_b64 = base64.b64encode(audio_bytes).decode()
                    yield _sse_event("audio_chunk", {
                        "audio": audio_b64,
                        "format": "wav"
                    })
            except Exception as e:
                logger.warning(f"TTS final failed: {e}")

        yield _sse_event("done", {
            "session_id": session_id,
            "total_text": full_text,
        })

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream; charset=utf-8",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


def _sse_event(event_type: str, data: dict) -> str:
    return f"event: {event_type}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"
