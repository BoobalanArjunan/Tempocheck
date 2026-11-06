import sys
from functools import lru_cache
from pathlib import Path

import numpy as np
import pytest
import soundfile as sf

sys.path.insert(0, str(Path(__file__).parent))
from synth import SR, make_song  # noqa: E402


@lru_cache(maxsize=None)
def song(bpm, seed=0, **kw):
    return make_song(bpm, seed=seed, **kw)


def write(path, x, sr=SR):
    sf.write(str(path), x, sr)
    return path
