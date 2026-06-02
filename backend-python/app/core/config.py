from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # MiMo API 配置（从 .env 文件读取）
    mimo_api_key: str = ""
    mimo_base_url: str = "https://token-plan-cn.xiaomimimo.com/v1"
    mimo_model: str = "mimo-v2.5-pro"

    # 服务配置
    python_port: int = 8000

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
    }


settings = Settings()
