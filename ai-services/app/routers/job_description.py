import logging

from fastapi import APIRouter, Depends, HTTPException, status

from app.schemas.job_description import ParseJobDescriptionRequest, ParseJobDescriptionResponse
from app.services.job_description_parser import ParsingError, parse_job_description
from app.services.llm import BaseLLMClient, get_llm_client

logger = logging.getLogger(__name__)

router = APIRouter(tags=["parsing"])


@router.post(
    "/parse-job-description",
    response_model=ParseJobDescriptionResponse,
    summary="Extract structured data from job description text",
)
async def parse_job_description_endpoint(
    request: ParseJobDescriptionRequest,
    llm: BaseLLMClient = Depends(get_llm_client),
) -> ParseJobDescriptionResponse:
    log_ctx = {"parser_version": request.parser_version}
    logger.info("Received parse-job-description request", extra=log_ctx)

    try:
        result = await parse_job_description(
            jd_text=request.jd_text,
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
        "Parse-job-description completed",
        extra={**log_ctx, "confidence": result.confidence},
    )
    return result
