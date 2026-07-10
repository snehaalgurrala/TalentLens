"""
Unit tests for app.ai.speech.

The real openai-whisper model is never loaded here — `_load_model` (in
whisper_service) is patched everywhere a model would otherwise load, and
SpeechService tests inject a fake WhisperService directly. Tests run
instantly with no model download, no GPU, and no ffmpeg dependency, matching
this module's "never call external APIs" requirement even at test time.
"""

import math
from unittest.mock import MagicMock, patch

import pytest

from app.ai.speech.exceptions import (
    AudioValidationError,
    ModelLoadError,
    TranscriptionError,
)
from app.ai.speech.schemas import TranscriptionResult
from app.ai.speech.speech_service import SpeechService
from app.ai.speech.transcription import staged_audio_file, validate_audio
from app.ai.speech.whisper_service import (
    WhisperService,
    get_model,
    reset_model_cache,
)

# ── validate_audio ───────────────────────────────────────────────────────────


class TestValidateAudio:
    def test_missing_data_raises(self):
        with pytest.raises(AudioValidationError, match="No audio data"):
            validate_audio(None, "audio/webm")

    def test_empty_bytes_raises(self):
        with pytest.raises(AudioValidationError, match="No audio data"):
            validate_audio(b"", "audio/webm")

    def test_unsupported_mime_type_raises(self):
        with pytest.raises(AudioValidationError, match="Unsupported audio type"):
            validate_audio(b"data", "video/mp4")

    def test_missing_mime_type_raises(self):
        with pytest.raises(AudioValidationError, match="Unsupported audio type"):
            validate_audio(b"data", None)

    def test_strips_codec_suffix(self):
        assert validate_audio(b"data", "audio/webm;codecs=opus") == "audio/webm"

    def test_oversized_file_raises(self):
        with patch(
            "app.ai.speech.transcription.get_max_audio_size_bytes", return_value=10
        ):
            with pytest.raises(AudioValidationError, match="exceeds the"):
                validate_audio(b"x" * 11, "audio/webm")

    def test_valid_audio_returns_normalized_mime(self):
        assert validate_audio(b"data", "audio/OGG") == "audio/ogg"


# ── staged_audio_file ─────────────────────────────────────────────────────────


class TestStagedAudioFile:
    def test_writes_bytes_and_cleans_up(self):
        captured_path = None
        with staged_audio_file(b"hello world", "audio/webm") as path:
            captured_path = path
            assert path.endswith(".webm")
            with open(path, "rb") as fh:
                assert fh.read() == b"hello world"

        import os

        assert not os.path.exists(captured_path)

    def test_uses_correct_extension_per_mime_type(self):
        with staged_audio_file(b"x", "audio/mpeg") as path:
            assert path.endswith(".mp3")


# ── WhisperService / get_model ────────────────────────────────────────────────


def _mock_model(transcribe_return: dict | None = None) -> MagicMock:
    model = MagicMock()
    model.transcribe = MagicMock(
        return_value=transcribe_return
        or {"text": "hello", "language": "en", "segments": []}
    )
    return model


class TestGetModel:
    def setup_method(self):
        reset_model_cache()

    def teardown_method(self):
        reset_model_cache()

    def test_loads_once_and_reuses_singleton(self):
        fake_model = _mock_model()
        with patch(
            "app.ai.speech.whisper_service._load_model", return_value=fake_model
        ) as mock_load:
            m1 = get_model("base", "cpu")
            m2 = get_model("base", "cpu")

        assert m1 is m2
        mock_load.assert_called_once_with("base", "cpu")

    def test_reloads_when_model_name_changes(self):
        with patch(
            "app.ai.speech.whisper_service._load_model", return_value=_mock_model()
        ) as mock_load:
            get_model("tiny", "cpu")
            get_model("small", "cpu")

        assert mock_load.call_count == 2

    def test_load_failure_raises_model_load_error(self):
        with patch(
            "app.ai.speech.whisper_service._load_model",
            side_effect=ModelLoadError("boom"),
        ):
            with pytest.raises(ModelLoadError):
                get_model("bad-model", "cpu")


class TestWhisperServiceTranscribe:
    def setup_method(self):
        reset_model_cache()

    def teardown_method(self):
        reset_model_cache()

    def test_happy_path_returns_whisper_result_dict(self):
        fake_model = _mock_model({"text": "hi there", "language": "en", "segments": []})
        with patch("app.ai.speech.whisper_service._load_model", return_value=fake_model):
            svc = WhisperService(model_name="base", device="cpu")
            result = svc.transcribe("/tmp/fake.webm")

        assert result["text"] == "hi there"
        fake_model.transcribe.assert_called_once_with(
            "/tmp/fake.webm",
            language="en",
            task="transcribe",
            temperature=0.0,
            beam_size=5,
            best_of=5,
            condition_on_previous_text=False,
            fp16=False,
        )

    def test_uses_real_fp16_on_a_non_cpu_device(self):
        fake_model = _mock_model()
        with patch("app.ai.speech.whisper_service._load_model", return_value=fake_model):
            svc = WhisperService(model_name="small", device="cuda")
            svc.transcribe("/tmp/fake.webm")

        assert fake_model.transcribe.call_args.kwargs["fp16"] is True

    def test_corrupted_audio_raises_transcription_error(self):
        fake_model = MagicMock()
        fake_model.transcribe = MagicMock(side_effect=RuntimeError("ffmpeg decode failed"))
        with patch("app.ai.speech.whisper_service._load_model", return_value=fake_model):
            svc = WhisperService(model_name="base", device="cpu")
            with pytest.raises(TranscriptionError, match="ffmpeg decode failed"):
                svc.transcribe("/tmp/corrupted.webm")

    def test_model_load_failure_propagates(self):
        with patch(
            "app.ai.speech.whisper_service._load_model",
            side_effect=ModelLoadError("no network"),
        ):
            svc = WhisperService(model_name="base", device="cpu")
            with pytest.raises(ModelLoadError):
                svc.transcribe("/tmp/fake.webm")


# ── SpeechService.transcribe ──────────────────────────────────────────────────


def _fake_whisper_service(transcribe_return: dict | None = None, side_effect=None) -> MagicMock:
    whisper_service = MagicMock(spec=WhisperService)
    whisper_service.model_name = "base"
    if side_effect is not None:
        whisper_service.transcribe = MagicMock(side_effect=side_effect)
    else:
        whisper_service.transcribe = MagicMock(
            return_value=transcribe_return
            or {"text": "hello world", "language": "en", "segments": []}
        )
    return whisper_service


class TestSpeechServiceTranscribe:
    async def test_missing_file_raises_before_touching_whisper(self):
        whisper_service = _fake_whisper_service()
        svc = SpeechService(whisper_service)

        with pytest.raises(AudioValidationError):
            await svc.transcribe(b"", mime_type="audio/webm")

        whisper_service.transcribe.assert_not_called()

    async def test_unsupported_mime_type_raises_before_touching_whisper(self):
        whisper_service = _fake_whisper_service()
        svc = SpeechService(whisper_service)

        with pytest.raises(AudioValidationError):
            await svc.transcribe(b"data", mime_type="video/mp4")

        whisper_service.transcribe.assert_not_called()

    async def test_happy_path_returns_structured_transcription_result(self):
        raw_result = {
            "text": "hello world",
            "language": "en",
            "segments": [
                {"id": 0, "start": 0.0, "end": 1.5, "text": "hello", "avg_logprob": -0.1},
                {"id": 1, "start": 1.5, "end": 3.0, "text": " world", "avg_logprob": -0.2},
            ],
        }
        whisper_service = _fake_whisper_service(raw_result)
        svc = SpeechService(whisper_service)

        result = await svc.transcribe(b"fake-audio-bytes", mime_type="audio/webm")

        assert isinstance(result, TranscriptionResult)
        assert result.transcript == "hello world"
        assert result.language == "en"
        assert result.model_name == "base"
        assert result.duration_seconds == 3.0
        assert len(result.segments) == 2
        assert result.segments[0].text == "hello"
        assert result.segments[0].confidence == pytest.approx(math.exp(-0.1))
        assert result.confidence == pytest.approx(
            (math.exp(-0.1) + math.exp(-0.2)) / 2
        )

        # The staged temp file passed to WhisperService must exist at call
        # time and use the extension matching the mime type.
        called_path = whisper_service.transcribe.call_args.args[0]
        assert called_path.endswith(".webm")

    async def test_no_segments_yields_zero_duration_and_no_confidence(self):
        whisper_service = _fake_whisper_service(
            {"text": "hi", "language": "en", "segments": []}
        )
        svc = SpeechService(whisper_service)

        result = await svc.transcribe(b"data", mime_type="audio/ogg")

        assert result.duration_seconds == 0.0
        assert result.confidence is None
        assert result.segments == []

    async def test_corrupted_audio_propagates_transcription_error(self):
        whisper_service = _fake_whisper_service(
            side_effect=TranscriptionError("Whisper failed to transcribe audio: bad file")
        )
        svc = SpeechService(whisper_service)

        with pytest.raises(TranscriptionError, match="bad file"):
            await svc.transcribe(b"corrupted-bytes", mime_type="audio/webm")

    async def test_model_load_failure_propagates(self):
        whisper_service = _fake_whisper_service(side_effect=ModelLoadError("no network"))
        svc = SpeechService(whisper_service)

        with pytest.raises(ModelLoadError):
            await svc.transcribe(b"data", mime_type="audio/webm")

    async def test_default_whisper_service_created_when_none_given(self):
        svc = SpeechService()
        assert isinstance(svc.whisper_service, WhisperService)
