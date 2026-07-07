"""Unit tests for app.ai.communication.comparison (normalize_text, compare_words)."""

from app.ai.communication.comparison import compare_words, normalize_text
from app.ai.communication.schemas import WordSubstitution


class TestNormalizeText:
    def test_lowercases_and_splits_on_whitespace(self):
        assert normalize_text("The Quick Brown Fox") == ["the", "quick", "brown", "fox"]

    def test_strips_punctuation(self):
        assert normalize_text("Hello, world!") == ["hello", "world"]

    def test_collapses_repeated_whitespace(self):
        assert normalize_text("hello    world\t\nfoo") == ["hello", "world", "foo"]

    def test_empty_string_returns_empty_list(self):
        assert normalize_text("") == []

    def test_whitespace_only_string_returns_empty_list(self):
        assert normalize_text("   \t  ") == []

    def test_punctuation_only_string_returns_empty_list(self):
        assert normalize_text("!!! ,, ...") == []


class TestCompareWords:
    def test_identical_sentences_are_all_correct(self):
        words = ["the", "quick", "brown", "fox"]
        result = compare_words(words, list(words))

        assert result.correct_words == words
        assert result.missing_words == []
        assert result.extra_words == []
        assert result.substitutions == []

    def test_missing_word_at_end(self):
        reference = ["the", "quick", "brown", "fox"]
        hypothesis = ["the", "quick", "brown"]
        result = compare_words(reference, hypothesis)

        assert result.correct_words == ["the", "quick", "brown"]
        assert result.missing_words == ["fox"]
        assert result.extra_words == []
        assert result.substitutions == []

    def test_extra_word_inserted(self):
        reference = ["the", "quick", "fox"]
        hypothesis = ["the", "very", "quick", "fox"]
        result = compare_words(reference, hypothesis)

        assert result.correct_words == ["the", "quick", "fox"]
        assert result.extra_words == ["very"]
        assert result.missing_words == []

    def test_substitution_pairs_expected_and_actual(self):
        reference = ["the", "quick", "brown", "fox"]
        hypothesis = ["the", "slow", "brown", "fox"]
        result = compare_words(reference, hypothesis)

        assert result.correct_words == ["the", "brown", "fox"]
        assert result.substitutions == [WordSubstitution(expected="quick", actual="slow")]
        assert result.missing_words == []
        assert result.extra_words == []

    def test_repeated_words_each_matched_by_position(self):
        # Dropping one of three repeated "the"s should report exactly one
        # missing word, not silently absorb it via an earlier duplicate.
        reference = ["the", "the", "the", "dog"]
        hypothesis = ["the", "the", "dog"]
        result = compare_words(reference, hypothesis)

        assert result.correct_words == ["the", "the", "dog"]
        assert result.missing_words == ["the"]
        assert result.extra_words == []

    def test_empty_hypothesis_reports_all_reference_words_missing(self):
        reference = ["the", "quick", "brown", "fox"]
        result = compare_words(reference, [])

        assert result.correct_words == []
        assert result.missing_words == reference
        assert result.extra_words == []
        assert result.substitutions == []

    def test_empty_reference_reports_all_hypothesis_words_extra(self):
        hypothesis = ["the", "quick", "brown", "fox"]
        result = compare_words([], hypothesis)

        assert result.correct_words == []
        assert result.extra_words == hypothesis
        assert result.missing_words == []
        assert result.substitutions == []

    def test_both_empty_returns_empty_result(self):
        result = compare_words([], [])

        assert result.correct_words == []
        assert result.missing_words == []
        assert result.extra_words == []
        assert result.substitutions == []

    def test_replace_block_length_mismatch_spills_into_missing_and_extra(self):
        reference = ["the", "quick", "brown", "fox"]
        hypothesis = ["the", "very", "slow", "old", "brown", "fox"]
        result = compare_words(reference, hypothesis)

        # "quick" (1 word) replaced by "very slow old" (3 words): one paired
        # substitution, the remaining two hypothesis words become extra.
        assert result.substitutions == [WordSubstitution(expected="quick", actual="very")]
        assert result.extra_words == ["slow", "old"]
        assert result.correct_words == ["the", "brown", "fox"]
