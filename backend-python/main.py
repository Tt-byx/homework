import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import chat, knowledge
from app.services.vector_store import get_client

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时验证 ChromaDB 连接
    try:
        client = get_client()
        client.heartbeat()
        logging.getLogger(__name__).info("ChromaDB 初始化成功")
    except Exception as e:
        logging.getLogger(__name__).warning(f"ChromaDB 初始化失败: {e}")
    yield


app = FastAPI(title="景区AI数字人 - Python后端", version="0.2.0", lifespan=lifespan)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:10086", "http://localhost:5173", "http://localhost:5176"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(chat.router, prefix="/api", tags=["chat"])
app.include_router(knowledge.router, prefix="/api", tags=["knowledge"])


@app.get("/health")
async def health():
    return {"status": "ok", "service": "python-backend"}
