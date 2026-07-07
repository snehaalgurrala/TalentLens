from pydantic import BaseModel


class WordSubstitution(BaseModel):
    expected: str
    actual: str


class WordComparisonResult(BaseModel):
    correct_words: list[str]
    missing_words: list[str]
    extra_words: list[str]
    substitutions: list[WordSubstitution]


class ReadAloudMetrics(BaseModel):
    total_words: int
    correct_words: int
    missing_words: int
    extra_words: int
    substituted_words: int
    word_accuracy: float
    completion_percentage: float
    reading_speed_wpm: float
    overall_score: float


class ReadAloudAnalysisResult(BaseModel):
    comparison: WordComparisonResult
    metrics: ReadAloudMetrics


class ListenRepeatMetrics(BaseModel):
    reference_word_count: int
    hypothesis_word_count: int
    semantic_similarity: float
    keyword_coverage: float
    completion_percentage: float
    overall_score: float
    matched_keywords: list[str]
    missing_keywords: list[str]


class ListenRepeatAnalysisResult(BaseModel):
    metrics: ListenRepeatMetrics
