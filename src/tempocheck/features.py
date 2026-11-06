"""Audio -> onset-strength curve (how strongly new sounds start, over time). Light on purpose: numpy, scipy, soundfile only."""
from __future__ import annotations

from math import gcd
from pathlib import Path

import numpy as np
import soundfile as sf
from scipy.signal import resample_poly, stft

FS = 22050
N_FFT = 1024
HOP = 256                      # 86 frames per second
FPS = FS / HOP
N_BANDS = 24
FMIN, FMAX = 30.0, 10000.0
MAX_SECONDS = 180.0            # long files: only the middle 3 minutes are used


def load_mono(path, max_seconds: float = MAX_SECONDS) -> np.ndarray:
    x, sr = sf.read(str(path), dtype="float32", always_2d=True)
    x = x.mean(axis=1)
    if sr != FS:
        g = gcd(int(sr), FS)
        x = resample_poly(x, FS // g, int(sr) // g).astype(np.float32)
    n = int(max_seconds * FS)
    if len(x) > n:
        s = (len(x) - n) // 2
        x = x[s:s + n]
    return x


def onset_envelope(x: np.ndarray) -> np.ndarray:
    """Positive change of log band energy, averaged over bands; mean removed. Empty array for audio shorter than ~1 s."""
    if len(x) < FS // 2:
        return np.zeros(0)
    _, _, Z = stft(x, fs=FS, nperseg=N_FFT, noverlap=N_FFT - HOP, boundary=None, padded=False)
    P = np.abs(Z) ** 2
    freqs = np.linspace(0, FS / 2, P.shape[0])
    edges = np.geomspace(FMIN, FMAX, N_BANDS + 1)
    bands = np.stack([P[(freqs >= lo) & (freqs < hi)].sum(axis=0) if ((freqs >= lo) & (freqs < hi)).any() else np.zeros(P.shape[1])
                      for lo, hi in zip(edges[:-1], edges[1:])])
    L = np.log1p(1e4 * bands / (bands.max() + 1e-20))
    flux = np.maximum(np.diff(L, axis=1), 0.0).mean(axis=0)
    return flux - flux.mean()
