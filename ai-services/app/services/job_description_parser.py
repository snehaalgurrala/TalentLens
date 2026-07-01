"""
Job description parsing service.

Flow:
  1. Load prompt template for the requested parser_version.
  2. Call LLM with the primary prompt.
  3. Extract and validate JSON → ParseJobDescriptionResponse.
  4. On JSON/validation failure, retry once with the fallback prompt (more explicit).
  5. On second failure, raise ParsingError (caller maps to HTTP 422).
"""

import json
import logging
from pathlib import Path

from pydantic import ValidationError

from app.schemas.job_description import ParseJobDescriptionResponse
from app.services.llm import BaseLLMClient
from app.services.parser import _extract_json

logger = logging.getLogger(__name__)

_PROMPTS_DIR = Path(__file__).parent.parent / "prompts"

_SUPPORTED_VERSIONS = {"v1"}


class ParsingError(Exception):
    """Raised when the LLM response cannot be parsed into the required schema."""


def _load_prompt(version: str, suffix: str = "") -> str:
    name = f"parse_job_description_{version}{suffix}.txt"
    path = _PROMPTS_DIR / name
    return path.read_text(encoding="utf-8")


async def parse_job_description(
    jd_text: str,
    parser_version: str,
    llm_client: BaseLLMClient,
) -> ParseJobDescriptionResponse:
    """
    Extract structured job description data using an LLM.

    Tries the primary prompt first; falls back to a simpler, more directive
    prompt if the response fails JSON parsing or Pydantic validation.
    """
    if parser_version not in _SUPPORTED_VERSIONS:
        raise ParsingError(f"Unsupported parser_version: '{parser_version}'")

    log_ctx = {"parser_version": parser_version}

    # ── Attempt 1: primary prompt ─────────────────────────────────────────────
    primary_prompt = _load_prompt(parser_version).replace("{jd_text}", jd_text)
    logger.info("Calling LLM (primary prompt)", extra=log_ctx)

    try:
        raw = await llm_client.complete(primary_prompt)
        data = _extract_json(raw)
        result = ParseJobDescriptionResponse(**data)
        logger.info(
            "Primary extraction succeeded",
            extra={**log_ctx, "confidence": result.confidence},
        )
        return result
    except (json.JSONDecodeError, ValidationError, KeyError, TypeError) as exc:
        logger.warning(
            "Primary extraction failed — falling back to retry prompt",
            extra={**log_ctx, "error": str(exc)},
        )

    # ── Attempt 2: fallback prompt ────────────────────────────────────────────
    fallback_prompt = _load_prompt(parser_version, "_fallback").replace("{jd_text}", jd_text)
    logger.info("Calling LLM (fallback prompt)", extra=log_ctx)

    try:
        raw = await llm_client.complete(fallback_prompt)
        data = _extract_json(raw)
        result = ParseJobDescriptionResponse(**data)
        logger.info(
            "Fallback extraction succeeded",
            extra={**log_ctx, "confidence": result.confidence},
        )
        return result
    except (json.JSONDecodeError, ValidationError, KeyError, TypeError) as exc:
        logger.error(
            "Fallback extraction also failed",
            extra={**log_ctx, "error": str(exc)},
        )
        raise ParsingError(
            f"Could not extract structured data after two attempts: {exc}"
        ) from exc
