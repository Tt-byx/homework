from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # MiMo API 配置（从 .env 文件读取）
    mimo_api_key: str = ""
    mimo_base_url: str = "https://token-plan-cn.xiaomimimo.com/v1"
    mimo_model: str = "mimo-v2.5-pro"

    # Embedding API 配置（SiliconFlow，OpenAI 兼容格式）
    embedding_api_key: str = ""
    embedding_base_url: str = "https://api.siliconflow.cn/v1"
    embedding_model: str = "BAAI/bge-m3"

    # ChromaDB 配置
    chroma_persist_dir: str = "./chroma_data"

    # RAG 检索配置
    rag_top_k: int = 5
    rag_chunk_size: int = 400
    rag_chunk_overlap: int = 50

    # 文件上传目录（与 Java 共享）
    upload_dir: str = "D:/scenic_uploads"

    # 服务配置
    python_port: int = 8000

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
    }


settings = Settings()
