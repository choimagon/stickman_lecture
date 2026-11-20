import wave

import numpy as np
import pytest

from mathscene.audio import SAMPLE_RATE, bubble_cues, visual_cues, write_effect_track
from mathscene.narration import NarrationError, narration_minimums, write_narration


def test_bubble_cues_follow_visible_text_changes():
    segments = [
        {"frames": 5, "bubbleSpeech": {}},
        {"frames": 10, "bubbleSpeech": {"teacher": "첫 설명"}},
        {"frames": 15, "bubbleSpeech": {"teacher": "첫 설명"}},
        {"frames": 30, "bubbleSpeech": {"teacher": "다음 설명"}},
        {"frames": 8, "bubbleSpeech": {}},
        {"frames": 4, "bubbleSpeech": {"teacher": "다음 설명"}},
        {"frames": 5, "bubbleSpeech": {"teacher": "다음 설명", "student": "질문"}},
    ]
    assert bubble_cues(segments) == [5, 30, 68, 72]


def test_bubble_track_is_short_and_aligned_even_across_a_block(tmp_path):
    path = tmp_path / "pop.wav"
    write_effect_track(path, [(frame, "bubble") for frame in (0, 29, 59)], 60, 30)
    with wave.open(str(path), "rb") as stream:
        assert stream.getframerate() == SAMPLE_RATE
        assert stream.getnframes() == 2 * SAMPLE_RATE
        samples = np.frombuffer(stream.readframes(stream.getnframes()), dtype="<i2")
    for frame in [0, 29, 59]:
        onset = int(frame * SAMPLE_RATE / 30)
        assert np.max(np.abs(samples[onset:onset + 1600])) > 4000
        if frame:
            assert not samples[onset - 1600:onset].any()
    assert samples[48_000:50_000].any()
    assert not samples[54_000:57_000].any()


def test_visual_cues_coalesce_when_elements_appear_together():
    segments = [
        {"frames": 15, "visualEffects": ["arrow", "graph", "point"]},
        {"frames": 25, "visualEffects": []},
        {"frames": 10, "visualEffects": ["shape", "shape"]},
    ]
    assert visual_cues(segments) == [(0, "graph"), (40, "shape")]


def test_narration_starts_inside_the_visible_bubbles_and_matches_the_lesson(tmp_path):
    sample_rate = 1000
    clips = {"첫 설명": np.full(400, 4000, dtype="<i2"), "마지막": np.full(300, -5000, dtype="<i2")}
    spans = [{"start": 0, "end": 9, "text": "첫 설명"}, {"start": 15, "end": 25, "text": "마지막"}]
    assert narration_minimums(clips, sample_rate) == pytest.approx({"첫 설명": .6, "마지막": .5})
    path = tmp_path / "narration.wav"
    write_narration(path, spans, clips, 30, 10, sample_rate)
    with wave.open(str(path), "rb") as stream:
        assert stream.getnframes() == 3000
        samples = np.frombuffer(stream.readframes(3000), dtype="<i2")
    expected = np.zeros(3000, dtype="<i2")
    expected[100:500] = 4000
    expected[1600:1900] = -5000
    np.testing.assert_array_equal(samples, expected)

    spans[0]["end"] = 5
    with pytest.raises(NarrationError, match="longer than the bubble"):
        write_narration(path, spans, clips, 30, 10, sample_rate)
