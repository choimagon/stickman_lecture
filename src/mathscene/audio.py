"""Synthesize short sounds for visible speech and drawing events."""
from bisect import bisect_left, bisect_right
import wave

import numpy as np


SAMPLE_RATE = 48_000
VISUAL_PRIORITY = ("graph", "arrow", "shape", "formula", "point")


def bubble_cues(segments):
    cues = []
    previous = {}
    frame = 0
    for segment in segments:
        current = segment["bubbleSpeech"]
        if any(previous.get(speaker) != text for speaker, text in current.items()):
            cues.append(frame)
        previous = current
        frame += segment["frames"]
    return cues


def visual_cues(segments):
    cues = []
    frame = 0
    for segment in segments:
        sounds = segment["visualEffects"]
        flavor = next((name for name in VISUAL_PRIORITY if name in sounds), None)
        if flavor:
            cues.append((frame, flavor))
        frame += segment["frames"]
    return cues


def pulse_for(effect):
    duration, attack_time, decay, peak, frequency, glide = {
        "bubble": (.106, .007, 34, .21, 755, -950),
        "graph": (.205, .035, 8, .13, 510, 1050),
        "arrow": (.152, .016, 14, .14, 475, 2380),
        "shape": (.122, .009, 27, .14, 480, -780),
        "point": (.065, .006, 37, .095, 1050, -960),
        "formula": (.158, .012, 22, .12, 1010, 125),
    }[effect]
    time = np.arange(round(duration * SAMPLE_RATE)) / SAMPLE_RATE
    attack = np.sin(np.pi / 2 * np.minimum(time / attack_time, 1)) ** 2
    release = np.clip((duration - time) / .018, 0, 1)
    envelope = attack * np.exp(-decay * time) * release
    phase = frequency * time + glide * time ** 2
    tone = np.sin(2 * np.pi * phase) + .22 * np.sin(2 * np.pi * 1.64 * phase)
    if effect in {"graph", "arrow"}:
        # Filtered deterministic noise adds a soft pencil or air texture.
        raw = np.random.default_rng(14).normal(size=time.size)
        smooth = np.convolve(raw, np.hanning(25) / 12, mode="same")
        tone = smooth * (4.2 if effect == "graph" else 2.9) + tone * .45
    pulse = envelope * tone
    return pulse * (peak / np.max(np.abs(pulse)))


def write_effect_track(path, cues, total_frames, fps):
    bank = {effect: pulse_for(effect) for effect in {effect for _, effect in cues}}
    placed = sorted((round(frame * SAMPLE_RATE / fps), effect) for frame, effect in cues)
    starts = [start for start, _ in placed]
    longest = max(map(len, bank.values()), default=0)
    samples = round(total_frames * SAMPLE_RATE / fps)
    with wave.open(str(path), "wb") as stream:
        stream.setparams((1, 2, SAMPLE_RATE, samples, "NONE", "not compressed"))
        for begin in range(0, samples, SAMPLE_RATE):
            end = min(begin + SAMPLE_RATE, samples)
            block = np.zeros(end - begin)
            first = bisect_right(starts, begin - longest)
            last = bisect_left(starts, end)
            for start, effect in placed[first:last]:
                pulse = bank[effect]
                lo = max(begin, start)
                hi = min(end, start + len(pulse))
                if lo < hi:
                    block[lo - begin:hi - begin] += pulse[lo - start:hi - start]
            stream.writeframesraw(np.rint(np.clip(block, -.8, .8) * 32767).astype("<i2").tobytes())
