import wave

import numpy as np

from mathscene.audio import SAMPLE_RATE, bubble_cues, visual_cues, write_effect_track


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
