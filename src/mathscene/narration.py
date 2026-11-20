"""Build an offline speech track from the lesson's visible speech bubbles."""
import os
import wave
from pathlib import Path

import numpy as np


VOICE_REPO = "supertone-oss-archive/supertonic-3"
VOICE_REVISION = "aafc6e32416a594460b32413efc49d7fe4ce6d46"
VOICE_NAMES = tuple(f"{kind}{number}" for kind in ("F", "M") for number in range(1, 6))
LEAD = .10
TAIL = .10
MODEL_FILES = (
    "duration_predictor.onnx", "text_encoder.onnx", "vector_estimator.onnx", "vocoder.onnx",
    "tts.json", "unicode_indexer.json",
)


class NarrationError(ValueError):
    pass


def voice_directory():
    configured = os.environ.get("STICKMAN_LECTURE_VOICE_DIR")
    if configured:
        return Path(configured).expanduser().resolve()
    return Path.home() / ".cache" / "stickman-lecture" / "supertonic-3"


def check_voice(voice):
    try:
        from supertonic import TTS
    except (OSError, ImportError) as exc:
        raise NarrationError("Install the narration dependencies with python -m pip install -e '.[narration]'.") from exc
    directory = voice_directory()
    files = [*(directory / "onnx" / f for f in MODEL_FILES), directory / "voice_styles" / f"{voice}.json"]
    if any(not f.is_file() or not f.stat().st_size for f in files):
        raise NarrationError("Voice model not installed. Run stickman-lecture voice-setup first.")
    return TTS, directory


def download_voice():
    try:
        from huggingface_hub import snapshot_download
    except ImportError as exc:
        raise NarrationError("Install the narration dependencies with python -m pip install -e '.[narration]'.") from exc
    directory = voice_directory()
    try:
        snapshot_download(repo_id=VOICE_REPO, revision=VOICE_REVISION, local_dir=directory,
                          allow_patterns=["onnx/*", "voice_styles/*.json", "LICENSE"], max_workers=3)
    except Exception as exc:
        raise NarrationError(f"Could not download the offline voice model: {exc}") from exc
    check_voice("F3")
    return directory


def synthesize_spans(spans, locale, voice):
    if not spans:
        raise NarrationError("This lesson has no visible speech bubbles to narrate.")
    TTS, directory = check_voice(voice)
    try:
        engine = TTS(model="supertonic-3", model_dir=directory, auto_download=False,
                     intra_op_num_threads=4, inter_op_num_threads=1)
        style = engine.get_voice_style(voice_name=voice)
        lang = locale.split("-")[0].lower()
        clips = {}
        for text in dict.fromkeys(span["text"] for span in spans):
            speech, _duration = engine.synthesize(text, voice_style=style, lang=lang)
            samples = np.asarray(speech, dtype=np.float32).reshape(-1)
            if not samples.size or not np.isfinite(samples).all() or np.max(np.abs(samples)) < .001:
                raise NarrationError("The voice engine did not generate audible narration for a bubble.")
            clips[text] = np.rint(np.clip(samples, -.9, .9) * 32767).astype("<i2")
    except (OSError, RuntimeError, ValueError) as exc:
        raise NarrationError(f"Could not synthesize narration: {exc}") from exc
    return clips, int(engine.sample_rate)


def narration_minimums(clips, sample_rate):
    return {text: len(samples) / sample_rate + LEAD + TAIL for text, samples in clips.items()}


def write_narration(path, spans, clips, total_frames, fps, sample_rate):
    position = lambda frame: round(frame * sample_rate / fps)
    lead, tail = round(LEAD * sample_rate), round(TAIL * sample_rate)
    queued = []
    for span in spans:
        start = position(span["start"]) + lead
        data = clips.get(span["text"])
        if data is None:
            raise NarrationError("A speech bubble changed while adjusting the timing. Use speak for narration.")
        if start + len(data) + tail > position(span["end"]) + 2:
            time = span["start"] / fps
            raise NarrationError(f"Narration is longer than the bubble at {time:.2f}s. "
                                 "Increase the bubble duration or remove --fixed-timing.")
        queued.append((start, data))
    silence = bytes(sample_rate * 2)
    with wave.open(str(path), "wb") as stream:
        stream.setparams((1, 2, sample_rate, position(total_frames), "NONE", "not compressed"))

        def pad(count):
            while count > 0:
                block = min(count, sample_rate)
                stream.writeframesraw(silence[:block * 2])
                count -= block

        cursor = 0
        for start, data in queued:
            pad(start - cursor)
            stream.writeframesraw(data.tobytes())
            cursor = start + len(data)
        pad(position(total_frames) - cursor)
