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
