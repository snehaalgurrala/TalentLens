"""Unit tests for app.ai.communication.keyword_extraction
(extract_keywords, keyword_coverage)."""

from app.ai.communication.keyword_extraction import extract_keywords, keyword_coverage


class TestExtractKeywords:
    def test_filters_stopwords_and_keeps_significant_words(self):
        assert extract_keywords("Innovation distinguishes a leader from a follower") == [
            "innovation",
            "distinguishes",
            "leader",
            "follower",
        ]

    def test_case_and_punctuation_are_ignored(self):
        assert extract_keywords("Innovation, Distinguishes!") == ["innovation", "distinguishes"]

    def test_deduplicates_preserving_first_occurrence(self):
        assert extract_keywords("the dog and the dog") == ["dog"]

    def test_empty_string_returns_empty_list(self):
        assert extract_keywords("") == []

    def test_stopword_only_sentence_returns_empty_list(self):
        assert extract_keywords("the a an of in") == []


class TestKeywordCoverage:
    def test_full_coverage(self):
        coverage, matched, missing = keyword_coverage(
            ["innovation", "leader", "follower"], ["innovation", "leader", "follower"]
        )
        assert coverage == 100.0
        assert matched == ["innovation", "leader", "follower"]
        assert missing == []

    def test_partial_coverage(self):
        coverage, matched, missing = keyword_coverage(
            ["innovation", "leader", "follower"], ["innovation", "leader"]
        )
        assert coverage == round(2 / 3 * 100, 2)
        assert matched == ["innovation", "leader"]
        assert missing == ["follower"]

    def test_order_independent(self):
        coverage, _, _ = keyword_coverage(
            ["innovation", "leader"], ["leader", "extra", "innovation"]
        )
        assert coverage == 100.0

    def test_no_reference_keywords_returns_zero(self):
        coverage, matched, missing = keyword_coverage([], ["anything"])
        assert coverage == 0.0
        assert matched == []
        assert missing == []

    def test_empty_hypothesis_returns_zero_coverage(self):
        coverage, matched, missing = keyword_coverage(["innovation", "leader"], [])
        assert coverage == 0.0
        assert matched == []
        assert missing == ["innovation", "leader"]
