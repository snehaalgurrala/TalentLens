import logging

from fastapi import APIRouter, Depends, HTTPException, status

from app.schemas.resume import ParseResumeRequest, ParseResumeResponse
from app.services.llm import BaseLLMClient, get_llm_client
from app.services.parser import ParsingError, parse_resume

logger = logging.getLogger(__name__)

router = APIRouter(tags=["parsing"])


@router.post(
    "/parse-resume",
    response_model=ParseResumeResponse,
    summary="Extract structured data from resume text",
)
async def parse_resume_endpoint(
    request: ParseResumeRequest,
    llm: BaseLLMClient = Depends(get_llm_client),
) -> ParseResumeResponse:
    log_ctx = {"parser_version": request.parser_version}
    logger.info("Received parse-resume request", extra=log_ctx)

    try:
        result = await parse_resume(
            resume_text=request.resume_text,
            parser_version=request.parser_version,
            llm_client=llm,
        )
    except ParsingError as exc:
        logger.error(
            "Parsing failed after retries",
            extra={**log_ctx, "error": str(exc)},
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    logger.info(
        "Parse-resume completed",
        extra={**log_ctx, "confidence": result.confidence},
    )
    return result
