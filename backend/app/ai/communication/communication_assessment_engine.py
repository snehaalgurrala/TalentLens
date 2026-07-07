"""CommunicationAssessmentEngine — pure, deterministic aggregation of a
completed Read Aloud + Listen & Repeat AssessmentAnalysis pair into a single
recruiter-facing communication assessment.

No DB, no LLM calls — mirrors the isolation of
ReadAloudAnalysisService/ListenRepeatAnalysisService (app.ai.communication.
analysis_service). Scoring formula and rule thresholds are documented in
app.ai.communication.config; see also
docs/phase5-sprint5.5-prompt11-communication-intelligence.md.
"""

from app.ai.communication import assessment_rules, config
from app.ai.communication.schemas import (
    CommunicationAssessmentResult,
    ListenRepeatAssessmentInput,
    ReadAloudAssessmentInput,
)


class CommunicationAssessmentEngine:
    def assess(
        self,
        read_aloud: ReadAloudAssessmentInput,
        listen_repeat: ListenRepeatAssessmentInput,
    ) -> CommunicationAssessmentResult:
        """Overall score = 50% Read Aloud overall_score + 50% Listen & Repeat
        overall_score (each sub-score already blends its own metrics — see
        app.ai.communication.read_aloud_analyzer / listen_repeat_analyzer).

        Confidence score = equally-weighted average of reading completion,
        listening completion, and semantic similarity (see config.py for the
        rationale)."""
        overall_score = (
            read_aloud.overall_score * config.OVERALL_READ_ALOUD_WEIGHT
            + listen_repeat.overall_score * config.OVERALL_LISTEN_REPEAT_WEIGHT
        )
        confidence_score = (
            read_aloud.completion_percentage * config.CONFIDENCE_READING_COMPLETION_WEIGHT
            + listen_repeat.completion_percentage * config.CONFIDENCE_LISTENING_COMPLETION_WEIGHT
            + listen_repeat.semantic_similarity * config.CONFIDENCE_SIMILARITY_WEIGHT
        )

        strengths = assessment_rules.detect_strengths(read_aloud, listen_repeat)
        improvements = assessment_rules.detect_improvements(read_aloud, listen_repeat)
        summary = assessment_rules.generate_summary(strengths, improvements)

        return CommunicationAssessmentResult(
            overall_score=overall_score,
            reading_score=read_aloud.overall_score,
            listening_score=listen_repeat.overall_score,
            confidence_score=confidence_score,
            strengths=strengths,
            improvements=improvements,
            summary=summary,
        )
