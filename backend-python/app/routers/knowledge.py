import logging
from fastapi import APIRouter, HTTPException
from app.schemas.knowledge import ProcessRequest, ProcessResponse
from app.services.document_parser import parse_file
from app.services.text_chunker import chunk_text
from app.services.embedding_service import embed_texts
from app.services.vector_store import add_document_chunks, delete_document

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/knowledge/process", response_model=ProcessResponse)
async def process_document(request: ProcessRequest):
    """解析文档 → 切片 → 向量化 → 存入 ChromaDB"""
    try:
        logger.info(f"开始处理文档: id={request.doc_id}, path={request.file_path}")

        text = parse_file(request.file_path, request.file_type)
        if not text.strip():
            return ProcessResponse(
                doc_id=request.doc_id,
                chunk_count=0,
                status="error",
                message="文档解析结果为空",
            )

        chunks = chunk_text(text)
        if not chunks:
            return ProcessResponse(
                doc_id=request.doc_id,
                chunk_count=0,
                status="error",
                message="文本切片结果为空",
            )

        embeddings = await embed_texts([c["text"] for c in chunks])

        add_document_chunks(request.doc_id, request.doc_title, chunks, embeddings)

        logger.info(f"文档处理完成: id={request.doc_id}, chunk_count={len(chunks)}")
        return ProcessResponse(
            doc_id=request.doc_id,
            chunk_count=len(chunks),
            status="success",
        )
    except Exception as e:
        logger.error(f"文档处理失败: {e}")
        raise HTTPException(status_code=500, detail=f"文档处理失败: {str(e)}")


@router.delete("/knowledge/{doc_id}")
async def delete_document_vectors(doc_id: int):
    """删除指定文档的所有向量"""
    try:
        delete_document(doc_id)
        return {"status": "success", "message": f"文档 {doc_id} 的向量已删除"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除失败: {str(e)}")
