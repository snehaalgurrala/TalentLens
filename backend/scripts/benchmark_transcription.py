"""
One-off benchmark comparing the OLD transcription pipeline (base model, no
preprocessing, default decoding args) against the NEW pipeline (small model,
silence-trim + normalize preprocessing, deterministic decoding args, filler
cleanup) on a real recorded file already present in local storage.

Not part of the test suite — run manually:
    python scripts/benchmark_transcription.py <path-to-audio-file>
"""

from __future__ import annotations

import sys
import time

import whisper

from app.ai.speech.audio_preprocessing import preprocess_audio_file
from app.ai.speech.transcript_cleanup import clean_transcript


def run_old_pipeline(audio_path: str) -> tuple[str, float, float]:
    model = whisper.load_model("base", device="cpu")
    started = time.monotonic()
    result = model.transcribe(audio_path)
    elapsed = time.monotonic() - started
    return result.get("text", ""), elapsed, 0.0


def run_new_pipeline(audio_path: str) -> tuple[str, float, float]:
    model = whisper.load_model("small", device="cpu")

    preprocess_started = time.monotonic()
    with preprocess_audio_file(audio_path) as processed_path:
        preprocess_elapsed = time.monotonic() - preprocess_started

        started = time.monotonic()
        result = model.transcribe(
            processed_path,
            language="en",
            task="transcribe",
            temperature=0.0,
            beam_size=5,
            best_of=5,
            condition_on_previous_text=False,
            fp16=False,
        )
        elapsed = time.monotonic() - started

    text = clean_transcript((result.get("text") or "").strip())
    return text, elapsed, preprocess_elapsed


def main() -> None:
    audio_path = sys.argv[1]
    print(f"Benchmarking: {audio_path}\n")

    print("=" * 70)
    print("OLD pipeline — base model, no preprocessing, default decode args")
    print("=" * 70)
    old_text, old_elapsed, _ = run_old_pipeline(audio_path)
    print(f"Transcript: {old_text!r}")
    print(f"Transcription time: {old_elapsed:.2f}s\n")

    print("=" * 70)
    print("NEW pipeline — small model, trim+normalize, deterministic decode")
    print("=" * 70)
    new_text, new_elapsed, preprocess_elapsed = run_new_pipeline(audio_path)
    print(f"Transcript: {new_text!r}")
    print(f"Preprocessing time: {preprocess_elapsed:.3f}s")
    print(f"Transcription time: {new_elapsed:.2f}s")
    print(f"Total (preprocess + transcribe): {preprocess_elapsed + new_elapsed:.2f}s\n")

    print("=" * 70)
    print("Summary")
    print("=" * 70)
    print(f"Old total: {old_elapsed:.2f}s")
    print(f"New total: {preprocess_elapsed + new_elapsed:.2f}s")
    print(f"Slowdown factor: {(preprocess_elapsed + new_elapsed) / old_elapsed:.2f}x")


if __name__ == "__main__":
    main()
