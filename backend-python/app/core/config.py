from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    mimo_api_key: str = ""
    mimo_base_url: str = "https://token-plan-cn.xiaomimimo.com/v1"
    mimo_model: str = "mimo-v2.5-pro"

    python_port: int = 8000

    asr_server_url: str = "ws://localhost:10095"
    asr_model: str = "paraformer-zh"

    cosyvoice_server_url: str = "http://localhost:5000"
    cosyvoice_model: str = "CosyVoice-300M-SFT"
    cosyvoice_speaker: str = "zh-CN-XiaoxiaoNeural"

    chroma_persist_dir: str = "./data/chroma_db"
    chroma_collection: str = "scenic_knowledge"

    knowledge_doc_dir: str = "../doc"

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
    }


settings = Settings()
