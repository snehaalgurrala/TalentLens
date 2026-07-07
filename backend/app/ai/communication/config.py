"""
Communication Analysis configuration — thin wrapper around app.core.config.settings.

The product has exactly one Read Aloud reference sentence today, shown to
every candidate regardless of campaign (see
frontend/src/features/candidate-runner/mock-data.ts::readAloudSentence).
There is no per-campaign assessment-content model yet, so this sprint mirrors
that same fixed-sentence behavior on the backend rather than inventing a
content-management system out of scope for a scoring-engine sprint. When a
future sprint adds per-campaign Read Aloud content, get_read_aloud_reference_sentence
is the one place that needs to change to resolve a session-specific sentence
instead of the global default. The same rationale applies to
get_listen_repeat_reference_sentence.
"""

from app.core.config import settings

# Overall score formula weights — see
# docs/phase5-sprint5.4-prompt9-read-aloud-analysis.md for the full write-up.
# Not deployment-tunable (they define the scoring algorithm itself, not an
# environment-specific knob), so these are module constants rather than
# Settings fields.
WORD_ACCURACY_WEIGHT = 0.7
COMPLETION_WEIGHT = 0.3

# Listen & Repeat overall score formula weights — see
# docs/phase5-sprint5.4-prompt10-listen-repeat-analysis.md. Semantic
# similarity is weighted highest since paraphrasing is the point of the
# exercise; keyword coverage checks the key concepts survived the paraphrase;
# completion guards against a technically-on-topic but truncated response.
SEMANTIC_SIMILARITY_WEIGHT = 0.6
KEYWORD_COVERAGE_WEIGHT = 0.25
LISTEN_COMPLETION_WEIGHT = 0.15


def get_read_aloud_reference_sentence() -> str:
    return settings.READ_ALOUD_REFERENCE_SENTENCE


def get_listen_repeat_reference_sentence() -> str:
    return settings.LISTEN_REPEAT_REFERENCE_SENTENCE


# Communication Assessment (aggregate) scoring — see
# docs/phase5-sprint5.5-prompt11-communication-intelligence.md. The two
# sub-assessments are weighted equally; there's no product signal yet that
# either communication skill matters more than the other for the roles this
# MVP targets.
OVERALL_READ_ALOUD_WEIGHT = 0.5
OVERALL_LISTEN_REPEAT_WEIGHT = 0.5

# Confidence score components, equally weighted (MVP assumption — no
# empirical basis yet for weighting one signal over another). Reading/
# listening completion measure how much of each recording the candidate
# actually finished; semantic similarity doubles as a proxy for how
# confident the Listen & Repeat comparison itself is (a low-similarity
# transcript could mean the candidate paraphrased poorly, or that the
# transcript/comparison was noisy — either way, confidence should drop).
CONFIDENCE_READING_COMPLETION_WEIGHT = 1 / 3
CONFIDENCE_LISTENING_COMPLETION_WEIGHT = 1 / 3
CONFIDENCE_SIMILARITY_WEIGHT = 1 / 3

# Strength / improvement detection thresholds — deterministic rules, no LLM.
# See app.ai.communication.assessment_rules.
READING_ACCURACY_STRENGTH_THRESHOLD = 95.0
READING_ACCURACY_IMPROVEMENT_THRESHOLD = 80.0
SEMANTIC_SIMILARITY_STRENGTH_THRESHOLD = 90.0
SEMANTIC_SIMILARITY_IMPROVEMENT_THRESHOLD = 75.0

# Reading-pace zones, in words per minute. COMFORTABLE is a strength signal;
# below TOO_SLOW or above TOO_FAST is an improvement signal. The bands
# between COMFORTABLE and TOO_SLOW/TOO_FAST are deliberately a dead zone
# (neither flag fires) rather than picking an arbitrary boundary to split
# them — an MVP assumption to revisit once real candidate data is available.
READING_SPEED_COMFORTABLE_MIN_WPM = 110.0
READING_SPEED_COMFORTABLE_MAX_WPM = 160.0
READING_SPEED_TOO_SLOW_WPM = 90.0
READING_SPEED_TOO_FAST_WPM = 180.0
