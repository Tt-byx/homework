import asyncio
import logging

logger = logging.getLogger(__name__)

# Global model cache
_model_cache = {}


class TTSService:

    def __init__(self, server_url: str = "http://localhost:5000"):
        self.server_url = server_url
        self._local_model = None
        self._use_local = False
        self._initialized = False

    async def _ensure_initialized(self):
        if self._initialized:
            return
        if 'tts' in _model_cache:
            self._local_model = _model_cache['tts']
            self._use_local = True
            self._initialized = True
            return
        await self.init_local_model()

    async def init_local_model(self):
        try:
            import sys
            import os
            base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            cosyvoice_path = os.path.join(base, "CosyVoice")
            matcha_path = os.path.join(cosyvoice_path, "third_party", "Matcha-TTS")
            sys.path.insert(0, matcha_path)
            sys.path.insert(0, cosyvoice_path)
            from cosyvoice.cli.cosyvoice import CosyVoice
            logger.info("Loading CosyVoice model...")
            model_path = os.path.join(base, "pretrained_models", "CosyVoice-300M-SFT")
            self._local_model = CosyVoice(model_path)
            self._use_local = True
            self._initialized = True
            _model_cache['tts'] = self._local_model
            logger.info("CosyVoice local model loaded")
        except ImportError:
            logger.warning("cosyvoice not installed, will use remote TTS")
        except Exception as e:
            logger.warning(f"CosyVoice local model failed: {e}, will use remote TTS")

    def start_background_loading(self):
        import threading
        def _load():
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self.init_local_model())
        thread = threading.Thread(target=_load, daemon=True)
        thread.start()
        logger.info("TTS model loading started in background")

    async def synthesize(self, text: str, speaker: str = "zh-CN-XiaoxiaoNeural") -> bytes:
        await self._ensure_initialized()
        if not text or not text.strip():
            return b""
        if self._use_local and self._local_model:
            return await self._synthesize_local(text, speaker)
        else:
            return await self._synthesize_remote(text, speaker)

    async def _synthesize_local(self, text: str, speaker: str) -> bytes:
        import io
        import soundfile as sf
        import numpy as np
        import tempfile
        import os

        loop = asyncio.get_event_loop()

        def _generate():
            output = list(self._local_model.inference_sft(text, speaker))
            if output and len(output) > 0:
                audio_data = output[0]["tts_speech"].numpy()
                if audio_data.ndim == 2 and audio_data.shape[0] == 1:
                    audio_data = audio_data.T
                with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
                    temp_path = f.name
                sf.write(temp_path, audio_data, 22050, format='WAV')
                with open(temp_path, 'rb') as f:
                    result = f.read()
                os.unlink(temp_path)
                return result
            return b""

        return await loop.run_in_executor(None, _generate)

    async def _synthesize_remote(self, text: str, speaker: str) -> bytes:
        try:
            import httpx
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.server_url}/tts",
                    json={"text": text, "speaker": speaker, "format": "wav"},
                )
                if response.status_code == 200:
                    return response.content
                else:
                    raise RuntimeError(f"TTS error: {response.status_code}")
        except httpx.ConnectError:
            raise RuntimeError("TTS service unavailable")
        except Exception as e:
            raise RuntimeError(f"TTS failed: {str(e)}")

    async def synthesize_stream(self, text_chunks, speaker: str = "zh-CN-XiaoxiaoNeural"):
        await self._ensure_initialized()
        sentence_buffer = ""
        end_marks = set(".!?;\n")

        async for chunk in text_chunks:
            sentence_buffer += chunk
            if sentence_buffer and sentence_buffer[-1] in end_marks:
                sentence = sentence_buffer.strip()
                if sentence:
                    audio = await self.synthesize(sentence, speaker)
                    if audio:
                        yield audio
                sentence_buffer = ""

        if sentence_buffer.strip():
            audio = await self.synthesize(sentence_buffer.strip(), speaker)
            if audio:
                yield audio


tts_service = TTSService()
