"""
Unit tests for app.ai.speech.audio_preprocessing.

Uses pydub's own signal generators to build real (short, synthetic) audio
in-memory — no network, no ML model, no GPU — so trimming/normalization
logic is exercised against real waveforms rather than mocks.
"""

import os

from pydub import AudioSegment
from pydub.generators import Sine

from app.ai.speech.audio_preprocessing import preprocess_audio_file


def _tone_with_silence_padding(tone_ms: int = 500, silence_ms: int = 800) -> AudioSegment:
    """A tone sandwiched between two silent pads — mirrors a real recording
    where the candidate pauses before/after speaking."""
    tone = Sine(440).to_audio_segment(duration=tone_ms).apply_gain(-3.0)
    silence = AudioSegment.silent(duration=silence_ms)
    return silence + tone + silence


def _write_wav(tmp_path, audio: AudioSegment, name: str = "input.wav") -> str:
    path = str(tmp_path / name)
    audio.export(path, format="wav")
    return path


class TestPreprocessAudioFile:
    def test_trims_leading_and_trailing_silence(self, tmp_path):
        audio = _tone_with_silence_padding(tone_ms=500, silence_ms=800)
        input_path = _write_wav(tmp_path, audio)

        with preprocess_audio_file(input_path) as processed_path:
            assert os.path.exists(processed_path)
            processed = AudioSegment.from_file(processed_path)

        # Well under the original ~2100ms (800 + 500 + 800), and comfortably
        # longer than just the 500ms tone (some quiet edge samples survive
        # the -40dBFS threshold) — the padding was removed, the tone wasn't.
        assert len(processed) < len(audio) - 800
        assert len(processed) >= 400

    def test_normalizes_quiet_audio_toward_full_scale(self, tmp_path):
        quiet_tone = Sine(440).to_audio_segment(duration=1000).apply_gain(-30.0)
        input_path = _write_wav(tmp_path, quiet_tone)

        with preprocess_audio_file(input_path) as processed_path:
            processed = AudioSegment.from_file(processed_path)

        assert processed.dBFS > quiet_tone.dBFS + 10

    def test_resamples_to_16khz_mono(self, tmp_path):
        stereo_44k = Sine(440).to_audio_segment(duration=500).set_frame_rate(44100).set_channels(2)
        input_path = _write_wav(tmp_path, stereo_44k)

        with preprocess_audio_file(input_path) as processed_path:
            processed = AudioSegment.from_file(processed_path)

        assert processed.frame_rate == 16000
        assert processed.channels == 1

    def test_does_not_over_trim_a_fully_silent_recording(self, tmp_path):
        silence = AudioSegment.silent(duration=1000)
        input_path = _write_wav(tmp_path, silence)

        with preprocess_audio_file(input_path) as processed_path:
            processed = AudioSegment.from_file(processed_path)

        # Guarded by _MIN_AUDIO_MS: a silent recording must not be reduced
        # to (near) nothing, or Whisper would have no file to work with.
        assert len(processed) >= 200

    def test_cleans_up_temp_file_on_exit(self, tmp_path):
        audio = Sine(440).to_audio_segment(duration=500)
        input_path = _write_wav(tmp_path, audio)

        captured_path = None
        with preprocess_audio_file(input_path) as processed_path:
            captured_path = processed_path

        assert not os.path.exists(captured_path)

    def test_falls_back_to_original_file_on_undecodable_input(self, tmp_path):
        input_path = str(tmp_path / "garbage.webm")
        with open(input_path, "wb") as fh:
            fh.write(b"not-a-real-audio-file")

        with preprocess_audio_file(input_path) as processed_path:
            assert processed_path == input_path
            assert os.path.exists(processed_path)

        # Fallback path is the caller's original staged file — this
        # function must never delete something it didn't create.
        assert os.path.exists(input_path)
