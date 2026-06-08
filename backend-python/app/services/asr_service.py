import asyncio
import logging
import numpy as np

logger = logging.getLogger(__name__)

# Global model cache
_model_cache = {}


class ASRService:

    def __init__(self, server_url: str = "ws://localhost:10095"):
        self.server_url = server_url
        self._local_model = None
        self._use_local = False
        self._initialized = False

    async def _ensure_initialized(self):
        if self._initialized:
            return
        if 'asr' in _model_cache:
            self._local_model = _model_cache['asr']
            self._use_local = True
            self._initialized = True
            return
        await self.init_local_model()

    async def init_local_model(self):
        try:
            from funasr import AutoModel
            logger.info("Loading FunASR model...")
            self._local_model = AutoModel(
                model="paraformer-zh",
                vad_model="fsmn-vad",
                punc_model="ct-punc",
                disable_update=True,
            )
            self._use_local = True
            self._initialized = True
            _model_cache['asr'] = self._local_model
            logger.info("FunASR local model loaded")
        except ImportError:
            logger.warning("funasr not installed, will use remote ASR")
        except Exception as e:
            logger.warning(f"FunASR local model failed: {e}, will use remote ASR")

    def start_background_loading(self):
        import threading
        def _load():
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self.init_local_model())
        thread = threading.Thread(target=_load, daemon=True)
        thread.start()
        logger.info("ASR model loading started in background")

    async def transcribe(self, audio_bytes: bytes, audio_format: str = "wav") -> str:
        await self._ensure_initialized()
        if self._use_local and self._local_model:
            return await self._transcribe_local(audio_bytes)
        else:
            return await self._transcribe_remote(audio_bytes, audio_format)

    async def _transcribe_local(self, audio_bytes: bytes) -> str:
        import tempfile
        import os

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            f.write(audio_bytes)
            temp_path = f.name

        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: self._local_model.generate(input=temp_path)
            )
            if result and len(result) > 0:
                return result[0]["text"]
            return ""
        finally:
            os.unlink(temp_path)

    async def _transcribe_remote(self, audio_bytes: bytes, audio_format: str) -> str:
        try:
            import websockets
            import json

            uri = self.server_url
            async with websockets.connect(uri, max_size=2**24) as ws:
                config = {
                    "mode": "offline",
                    "audio_fs": 16000,
                    "wav_name": "user_audio",
                    "wav_format": audio_format,
                    "is_speaking": True,
                    "chunk_size": [5, 10, 5],
                    "itn": True,
                    "wav_format_type": "PCM16",
                }
                await ws.send(json.dumps(config))

                chunk_size = 9600
                for i in range(0, len(audio_bytes), chunk_size):
                    chunk = audio_bytes[i:i + chunk_size]
                    await ws.send(chunk)
                    await asyncio.sleep(0.01)

                await ws.send(json.dumps({"is_speaking": False}))

                result_text = ""
                while True:
                    try:
                        msg = await asyncio.wait_for(ws.recv(), timeout=10)
                        data = json.loads(msg)
                        if "text" in data:
                            result_text += data["text"]
                        if data.get("is_final", False):
                            break
                    except asyncio.TimeoutError:
                        break

                return result_text.strip()

        except ImportError:
            logger.error("websockets not installed")
            raise RuntimeError("ASR service unavailable: websockets not installed")
        except Exception as e:
            logger.error(f"ASR remote service failed: {e}")
            raise RuntimeError(f"ASR service failed: {str(e)}")


asr_service = ASRService()
