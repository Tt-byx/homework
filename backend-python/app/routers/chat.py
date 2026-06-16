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
from app.utils.text_utils import strip_markdown

logger = logging.getLogger(__name__)
router = APIRouter()


def detect_expression(text: str) -> str:
    """基于关键词的简单情感检测，返回 Live2D 表情名"""
    # 优先级从高到低
    if any(w in text for w in ["抱歉", "无法", "不知道", "没有找到", "暂时无法", "错误", "失败"]):
        return "Cry"
    if any(w in text for w in ["恭喜", "太好了", "开心", "高兴", "快乐", "棒", "赞", "喜欢", "美丽", "精彩", "精彩", "😊", "😄"]):
        return "Smile"
    if any(w in text for w in ["注意", "小心", "警告", "禁止", "危险", "请勿", "不要"]):
        return "Angry"
    if any(w in text for w in ["？", "吗", "呢", "什么", "怎么", "为什么", "请问"]):
        return "Star"
    return "Normal"


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """文字聊天接口（RAG + TTS 按句合成 + 情感检测）"""
    try:
        reply = await chat_with_rag(request.message)
    except Exception:
        try:
            reply = await chat_with_mimo(request.message)
        except Exception as e2:
            raise HTTPException(status_code=500, detail=f"AI服务调用失败: {str(e2)}")

    # 情感检测
    expression = detect_expression(reply)

    # TTS 按句合成，剥离 Markdown 符号便于朗读
    audio_list = []
    try:
        sentences = _split_sentences(reply)
        for sentence in sentences:
            clean_sentence = strip_markdown(sentence)
            if clean_sentence.strip():
                try:
                    audio_bytes = await tts_service.synthesize(clean_sentence.strip())
                    if audio_bytes:
                        audio_list.append(base64.b64encode(audio_bytes).decode())
                except Exception as e:
                    logger.warning(f"句子 TTS 失败: {e}")
    except Exception as e:
        logger.warning(f"TTS 合成失败（不影响文字回复）: {e}")

    # 将多个音频用逗号连接（前端逐个播放）
    audio_str = ",".join(audio_list) if audio_list else None

    return ChatResponse(
        reply=reply,
        session_id=request.session_id,
        audio=audio_str,
        expression=expression,
    )


def _split_sentences(text: str) -> list[str]:
    """按中文标点分句"""
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
    return sentences if sentences else [text]


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
):
    """TTS: 文字转语音"""
    try:
        audio_bytes = await tts_service.synthesize(text)
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
    """流式对话接口（支持文字和语音输入，流式输出文字+语音+表情）"""
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
        first_expression_sent = False

        try:
            async for text_chunk in chat_stream(input_text, context_chunks):
                sentence_buffer += text_chunk
                full_text += text_chunk
                yield _sse_event("text_chunk", {"text": text_chunk})

                # 首句完成时发送表情
                if not first_expression_sent and sentence_buffer and sentence_buffer[-1] in end_marks:
                    first_expression_sent = True
                    expression = detect_expression(sentence_buffer)
                    yield _sse_event("expression", {"expression": expression})

                # 遇到句号等标点，合成这一句的语音（剥离Markdown便于朗读）
                if sentence_buffer and sentence_buffer[-1] in end_marks:
                    sentence = strip_markdown(sentence_buffer.strip())
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
            if not first_expression_sent:
                expression = detect_expression(full_text)
                yield _sse_event("expression", {"expression": expression})
            try:
                clean_remaining = strip_markdown(sentence_buffer.strip())
                if clean_remaining:
                    audio_bytes = await tts_service.synthesize(clean_remaining)
                    if audio_bytes:
                        audio_b64 = base64.b64encode(audio_bytes).decode()
                        yield _sse_event("audio_chunk", {
                            "audio": audio_b64,
                            "format": "wav"
                        })
            except Exception as e:
                logger.warning(f"TTS final failed: {e}")

        # 如果没有任何句子完成（极短回复），发送默认表情
        if not first_expression_sent:
            yield _sse_event("expression", {"expression": detect_expression(full_text)})

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
