"""Deterministic strength / improvement / summary rules for the
Communication Assessment aggregate
(app.ai.communication.communication_assessment_engine).

Pure functions, no DB, no LLM calls — every rule is a fixed threshold
comparison against a documented constant in app.ai.communication.config.
"""

from app.ai.communication import config
from app.ai.communication.schemas import (
    CommunicationAssessmentSummary,
    ListenRepeatAssessmentInput,
    ReadAloudAssessmentInput,
)

_STRENGTH_READING_ACCURACY = "Reads clearly and accurately"
_STRENGTH_LISTENING_COMPREHENSION = "Demonstrates strong listening comprehension"
_STRENGTH_SPEAKING_PACE = "Maintains a comfortable speaking pace"

_IMPROVEMENT_READING_ACCURACY = "Misses important words while reading"
_IMPROVEMENT_LISTENING_COMPREHENSION = "Could improve listening comprehension"
_IMPROVEMENT_PACE_TOO_FAST = "Speaking pace may be difficult to follow"
_IMPROVEMENT_PACE_TOO_SLOW = "Speaking pace is slower than recommended"

# Maps each improvement message to the short recruiter-facing topic used by
# generate_summary. Both pace messages collapse to the same topic since a
# summary shouldn't mention "speaking pace" twice.
_IMPROVEMENT_TOPICS = {
    _IMPROVEMENT_READING_ACCURACY: "reading accuracy",
    _IMPROVEMENT_LISTENING_COMPREHENSION: "listening comprehension",
    _IMPROVEMENT_PACE_TOO_FAST: "speaking pace",
    _IMPROVEMENT_PACE_TOO_SLOW: "speaking pace",
}


def detect_strengths(
    read_aloud: ReadAloudAssessmentInput, listen_repeat: ListenRepeatAssessmentInput
) -> list[str]:
    strengths: list[str] = []
    if read_aloud.word_accuracy > config.READING_ACCURACY_STRENGTH_THRESHOLD:
        strengths.append(_STRENGTH_READING_ACCURACY)
    if listen_repeat.semantic_similarity > config.SEMANTIC_SIMILARITY_STRENGTH_THRESHOLD:
        strengths.append(_STRENGTH_LISTENING_COMPREHENSION)
    if (
        config.READING_SPEED_COMFORTABLE_MIN_WPM
        <= read_aloud.reading_speed_wpm
        <= config.READING_SPEED_COMFORTABLE_MAX_WPM
    ):
        strengths.append(_STRENGTH_SPEAKING_PACE)
    return strengths


def detect_improvements(
    read_aloud: ReadAloudAssessmentInput, listen_repeat: ListenRepeatAssessmentInput
) -> list[str]:
    improvements: list[str] = []
    if read_aloud.word_accuracy < config.READING_ACCURACY_IMPROVEMENT_THRESHOLD:
        improvements.append(_IMPROVEMENT_READING_ACCURACY)
    if listen_repeat.semantic_similarity < config.SEMANTIC_SIMILARITY_IMPROVEMENT_THRESHOLD:
        improvements.append(_IMPROVEMENT_LISTENING_COMPREHENSION)
    if read_aloud.reading_speed_wpm > config.READING_SPEED_TOO_FAST_WPM:
        improvements.append(_IMPROVEMENT_PACE_TOO_FAST)
    if read_aloud.reading_speed_wpm < config.READING_SPEED_TOO_SLOW_WPM:
        improvements.append(_IMPROVEMENT_PACE_TOO_SLOW)
    return improvements


def _improvement_topics(improvements: list[str]) -> list[str]:
    topics: list[str] = []
    for message in improvements:
        topic = _IMPROVEMENT_TOPICS.get(message)
        if topic and topic not in topics:
            topics.append(topic)
    return topics


def generate_summary(
    strengths: list[str], improvements: list[str]
) -> CommunicationAssessmentSummary:
    """Template-based recruiter summary — no AI calls. Driven off the
    strength/improvement *labels* already produced by detect_strengths/
    detect_improvements (not raw scores), so the summary can never
    contradict them."""
    reading_strength = _STRENGTH_READING_ACCURACY in strengths
    listening_strength = _STRENGTH_LISTENING_COMPREHENSION in strengths

    if reading_strength and listening_strength:
        opening = (
            "The candidate demonstrated strong reading accuracy and "
            "good listening comprehension."
        )
    elif reading_strength:
        opening = "The candidate demonstrated strong reading accuracy."
    elif listening_strength:
        opening = "The candidate demonstrated good listening comprehension."
    else:
        opening = "The candidate completed the communication assessment."

    topics = _improvement_topics(improvements)
    if topics:
        closing = f"Minor improvements are recommended in {' and '.join(topics)}."
    else:
        closing = "No significant areas for improvement were identified."

    return CommunicationAssessmentSummary(overview=f"{opening} {closing}")
