import base64
import json
import logging

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from fastapi.responses import StreamingResponse, Response
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.llm_service import chat_with_mimo, chat_stream
from app.services.asr_service import asr_service
from app.services.tts_service import tts_service
from app.services.rag_service import rag_service

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    try:
        context_chunks = []
        try:
            context_chunks = await rag_service.search(request.message, top_k=3)
        except Exception as e:
            logger.warning(f"RAG search failed: {e}")

        if context_chunks:
            prompt = rag_service.build_prompt(request.message, context_chunks)
        else:
            prompt = request.message

        reply = await chat_with_mimo(prompt)
        return ChatResponse(reply=reply, session_id=request.session_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI error: {str(e)}")


@router.post("/asr")
async def asr_endpoint(audio: UploadFile = File(...)):
    """ASR: Speech to Text"""
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
    """TTS: Text to Speech"""
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
    async def event_generator():
        input_text = message
        full_text = ""

        if audio is not None:
            try:
                audio_bytes = await audio.read()
                audio_format = audio.filename.split('.')[-1] if audio.filename else "webm"
                input_text = await asr_service.transcribe(audio_bytes, audio_format)
                yield _sse_event("asr_result", {"text": input_text})
            except Exception as e:
                logger.error(f"ASR failed: {e}")
                yield _sse_event("error", {"message": f"ASR failed: {str(e)}"})
                yield _sse_event("done", {"session_id": session_id, "total_text": ""})
                return

        if not input_text or not input_text.strip():
            yield _sse_event("error", {"message": "Empty input"})
            yield _sse_event("done", {"session_id": session_id, "total_text": ""})
            return

        context_chunks = []
        try:
            context_chunks = await rag_service.search(input_text, top_k=3)
        except Exception as e:
            logger.warning(f"RAG search failed: {e}")

        sentence_buffer = ""
        end_marks = set("。！？；\n")

        try:
            async for text_chunk in chat_stream(input_text, context_chunks):
                sentence_buffer += text_chunk
                full_text += text_chunk
                yield _sse_event("text_chunk", {"text": text_chunk})

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