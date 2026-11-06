"""Synthetic songs with a KNOWN tempo: kick/snare/hat patterns with swing, level jitter, timing jitter, a pad and noise."""
import numpy as np

SR = 22050


def _hit(x, t0, kind, amp, rng):
    i = int(t0 * SR)
    if i < 0 or i >= len(x) - 100:
        return
    n = {"kick": int(0.18 * SR), "snare": int(0.15 * SR), "hat": int(0.04 * SR)}[kind]
    n = min(n, len(x) - i)
    t = np.arange(n) / SR
    if kind == "kick":
        s = np.sin(2 * np.pi * (50 * t + 90 * (1 - np.exp(-t * 30)) / 30 * 30 * 0.0 + 60 * np.exp(-t * 25) * 0.0) + 8 * (1 - np.exp(-t * 40))) * np.exp(-t * 20)
    elif kind == "snare":
        s = (0.5 * np.sin(2 * np.pi * 190 * t) + rng.randn(n) * 0.7) * np.exp(-t * 28)
    else:
        s = rng.randn(n) * np.exp(-t * 120) * 0.5
    x[i:i + n] += amp * s


def make_song(bpm, seconds=40.0, seed=0, swing=0.0, jitter_ms=4.0, pattern="four", noise=0.01, pad=True, ramp_to=None):
    """pattern: 'four' = kick on every beat, snare on 2 and 4, hats on 8ths; 'half' = kick on 1 and 3 only (half-time feel)."""
    rng = np.random.RandomState(seed)
    x = np.zeros(int(seconds * SR) + SR, dtype=np.float64)
    t, beat = 0.0, 0
    while t < seconds:
        cur = bpm if ramp_to is None else bpm + (ramp_to - bpm) * t / seconds
        spb = 60.0 / cur
        j = lambda: rng.randn() * jitter_ms / 1000.0
        a = lambda: 0.8 + 0.2 * rng.rand()
        if pattern == "four" or beat % 2 == 0:
            _hit(x, t + j(), "kick", a(), rng)
        if beat % 2 == 1 and pattern == "four":
            _hit(x, t + j(), "snare", a(), rng)
        if pattern == "half" and beat % 4 == 2:
            _hit(x, t + j(), "snare", a(), rng)
        _hit(x, t + j(), "hat", 0.4 * a(), rng)
        _hit(x, t + spb / 2 + swing * spb / 6 + j(), "hat", 0.3 * a(), rng)
        t += spb
        beat += 1
    if pad:
        tt = np.arange(len(x)) / SR
        for f in (220, 277.2, 329.6):
            x += 0.08 * np.sin(2 * np.pi * f * tt + rng.rand() * 6)
    x += noise * rng.randn(len(x))
    x = x[: int(seconds * SR)]
    return (0.8 * x / np.abs(x).max()).astype(np.float32)
