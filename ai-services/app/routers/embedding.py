import logging

from fastapi import APIRouter, Depends, HTTPException, status

from app.schemas.embedding import GenerateEmbeddingRequest, GenerateEmbeddingResponse
from app.services.embedding import EmbeddingGenerationError, EmbeddingService, get_embedding_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["embedding"])


@router.post(
    "/generate-embedding",
    response_model=GenerateEmbeddingResponse,
    summary="Generate a semantic embedding vector for text",
)
async def generate_embedding_endpoint(
    request: GenerateEmbeddingRequest,
    service: EmbeddingService = Depends(get_embedding_service),
) -> GenerateEmbeddingResponse:
    log_ctx = {"text_length": len(request.text)}
    logger.info("Received generate-embedding request", extra=log_ctx)

    try:
        result = await service.generate_embedding(request.text)
    except EmbeddingGenerationError as exc:
        logger.error(
            "Embedding generation failed after retries",
            extra={**log_ctx, "error": str(exc)},
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc

    logger.info(
        "Generate-embedding completed",
        extra={**log_ctx, "model": result.model, "dimension": result.dimension},
    )
    return GenerateEmbeddingResponse(
        embedding=result.embedding, model=result.model, dimension=result.dimension
    )
