"""Tempo from an onset curve: a Fourier tempogram (how strong is a steady pulse at each BPM) with a comb over the
pulse's harmonics, so a true pulse at B gets support from B, 2B, 3B and 4B."""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Tuple

import numpy as np

from .features import FPS

GRID = np.arange(30.0, 300.0, 0.25)          # BPM values scored
EST_MIN, EST_MAX = 50.0, 200.0               # the tempo is looked for in this range
HARMONIC_WEIGHTS = (1.0, 0.75, 0.5, 0.25)
MIN_PROMINENCE = 3.0                         # best score must be this many times the typical score, else "no clear pulse" (provisional)
SEGMENT_SECONDS = 20.0
PRIOR_CENTER, PRIOR_SIGMA_OCT = 110.0, 0.7    # gentle preference for everyday tempi when two readings (B and 2B) score alike (Ellis 2007)


@dataclass
class Tempo:
    bpm: Optional[float]
    prominence: float                        # best score / median score over the grid; high = clear pulse
    score_at: "callable"                     # score_at(bpm) -> comb score, to ask "does the audio support THIS tempo?"
    segments: List[float]                    # per-segment estimates (empty for short files)


def _tempogram(env: np.ndarray) -> np.ndarray:
    n = len(env)
    w = np.hanning(n)
    t = np.arange(n) / FPS
    freqs = np.concatenate([GRID * h / 60.0 for h in (1, 2, 3, 4)])
    freqs = np.unique(freqs)
    # |sum env(t) e^{-2 pi i f t}| for each needed frequency, in chunks to keep memory small
    out = np.empty(len(freqs))
    e = env * w
    for i in range(0, len(freqs), 256):
        f = freqs[i:i + 256]
        out[i:i + 256] = np.abs(np.exp(-2j * np.pi * np.outer(f, t)) @ e)
    return freqs, out


def _scores(env: np.ndarray):
    freqs, mag = _tempogram(env)

    def at(f_hz: float) -> float:
        return float(np.interp(f_hz, freqs, mag))

    def score_at(bpm: float) -> float:
        return sum(wt * at(h * bpm / 60.0) for h, wt in zip((1, 2, 3, 4), HARMONIC_WEIGHTS))
    grid_scores = np.array([score_at(b) for b in GRID])
    return score_at, grid_scores


def _best(grid_scores: np.ndarray) -> Tuple[float, float]:
    m = (GRID >= EST_MIN) & (GRID <= EST_MAX)
    prior = np.exp(-0.5 * (np.log2(GRID / PRIOR_CENTER) / PRIOR_SIGMA_OCT) ** 2)
    i = int(np.argmax(np.where(m, grid_scores * prior, -1)))
    med = float(np.median(grid_scores)) + 1e-12
    return float(GRID[i]), float(grid_scores[i] / med)


def estimate(env: np.ndarray) -> Tempo:
    if len(env) < int(4 * FPS) or not np.any(env):
        return Tempo(None, 0.0, lambda b: 0.0, [])
    score_at, gs = _scores(env)
    bpm, prom = _best(gs)
    segs: List[float] = []
    seg_n = int(SEGMENT_SECONDS * FPS)
    if len(env) >= 2 * seg_n:
        k = min(4, len(env) // seg_n)
        for part in np.array_split(env, k):
            _, g = _scores(part)
            b, p = _best(g)
            if p >= MIN_PROMINENCE:
                segs.append(b)
    return Tempo(bpm, prom, score_at, segs)
