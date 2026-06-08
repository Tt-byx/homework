from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import chat
from app.services.rag_service import rag_service
from app.core.config import settings

import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        await rag_service.init()
        logger.info("RAG service init OK")
    except Exception as e:
        logger.warning(f"RAG init failed: {e}")
    
    # Models will be loaded on first use (lazy loading)
    logger.info("Backend ready. Models will load on first request.")
    
    yield


app = FastAPI(
    title="Scenic AI Backend",
    version="0.2.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8080", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat.router, prefix="/api", tags=["chat"])


@app.get("/health")
async def health():
    return {"status": "ok", "service": "python-backend"}
