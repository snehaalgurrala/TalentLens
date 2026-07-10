from app.ai.speech.transcript_cleanup import clean_transcript


class TestCleanTranscript:
    def test_empty_string_returns_empty_string(self):
        assert clean_transcript("") == ""

    def test_collapses_repeated_spaces(self):
        assert clean_transcript("Hello    world,   how are   you") == "Hello world, how are you"

    def test_removes_standalone_filler_words_case_insensitive(self):
        assert clean_transcript("Um, I think uh the answer is Uh clear") == "I think the answer is clear"

    def test_does_not_remove_words_containing_filler_as_substring(self):
        assert clean_transcript("The umpire hummed a tune") == "The umpire hummed a tune"

    def test_preserves_punctuation_on_real_words(self):
        assert clean_transcript("Hello, world!  This is great.") == "Hello, world! This is great."

    def test_does_not_alter_meaningful_words(self):
        text = "The quick brown fox jumps over the lazy dog."
        assert clean_transcript(text) == text

    def test_trims_leading_and_trailing_whitespace(self):
        assert clean_transcript("   hello world   ") == "hello world"
