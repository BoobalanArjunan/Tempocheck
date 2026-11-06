"""Compare a labelled BPM with the audio and give a verdict."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .estimate import MIN_PROMINENCE, Tempo, estimate
from .features import load_mono, onset_envelope

TOL = 0.04                 # 4 percent: the usual "right tempo" tolerance in tempo research
SUPPORT_RATIO = 0.8        # the label counts as "also supported by the audio" at this share of the best score
RELATIONS = ((2.0, "audio is 2x the label"), (0.5, "audio is half the label"), (3.0, "audio is 3x the label"),
             (1 / 3, "audio is a third of the label"), (1.5, "audio is 3/2 of the label"), (2 / 3, "audio is 2/3 of the label"))

OK, OCTAVE, WRONG, UNSURE, ERROR = "OK", "OCTAVE", "WRONG", "UNSURE", "ERROR"


@dataclass
class Verdict:
    file: str
    label: float
    status: str
    estimate: Optional[float]
    reason: str
    prominence: float = 0.0

    @property
    def level(self) -> str:
        return {OK: "PASS", OCTAVE: "WARN", UNSURE: "REVIEW", WRONG: "FAIL", ERROR: "ERROR"}[self.status]


def close(a: float, b: float, tol: float = TOL) -> bool:
    return abs(a - b) <= tol * b


def judge(label: float, t: Tempo, file: str = "") -> Verdict:
    if t.bpm is None:
        return Verdict(file, label, UNSURE, None, "too short or silent to measure a tempo")
    if len(t.segments) >= 2 and any(not close(s, t.segments[0], TOL) and not any(close(s, t.segments[0] * r, TOL) for r, _ in RELATIONS)
                                    for s in t.segments[1:]):
        return Verdict(file, label, UNSURE, t.bpm, "tempo changes inside the file: " + ", ".join(f"{s:g}" for s in t.segments), t.prominence)
    if t.prominence < MIN_PROMINENCE:
        return Verdict(file, label, UNSURE, t.bpm, f"no clear steady pulse (strength {t.prominence:.1f}); label cannot be judged", t.prominence)
    if close(t.bpm, label):
        return Verdict(file, label, OK, t.bpm, "label matches the audio", t.prominence)
    for r, text in RELATIONS:
        if close(t.bpm, label * r):
            return Verdict(file, label, OCTAVE, t.bpm, f"{text} (measured {t.bpm:g}); both feel natural to some listeners", t.prominence)
    if t.score_at(label) >= SUPPORT_RATIO * t.score_at(t.bpm):
        return Verdict(file, label, UNSURE, t.bpm, f"audio supports both the label and {t.bpm:g}", t.prominence)
    return Verdict(file, label, WRONG, t.bpm, f"audio says about {t.bpm:g}, label says {label:g}", t.prominence)


def check_file(path, label: float) -> Verdict:
    p = Path(path)
    try:
        env = onset_envelope(load_mono(p))
    except Exception as e:  # unreadable audio
        return Verdict(p.name, label, ERROR, None, f"could not read audio: {e}")
    return judge(label, estimate(env), p.name)
