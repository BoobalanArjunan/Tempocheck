"""Where the labelled BPM comes from: a CSV (columns for file and bpm) or the file name ("track_120bpm.wav")."""
from __future__ import annotations

import csv
import re
from pathlib import Path
from typing import List, Optional, Tuple

AUDIO_EXT = {".wav", ".flac", ".mp3", ".ogg", ".m4a", ".aiff", ".aif"}
FILE_COLS = ("file", "filename", "path", "name", "audio", "track")
BPM_COLS = ("bpm", "tempo", "label", "label_bpm")
_NAME_RE = re.compile(r"(?<![\d.])(\d{2,3}(?:\.\d+)?)\s*[-_ ]?bpm", re.I)


class LabelError(Exception):
    pass


def bpm_from_name(name: str) -> Optional[float]:
    m = _NAME_RE.search(name)
    return float(m.group(1)) if m else None


def read_csv(path: Path, audio_dir: Optional[Path] = None) -> Tuple[List[Tuple[Path, float]], List[str]]:
    """Returns ([(audio path, bpm)], [problems]). Rows with a missing file or an unusable bpm are reported, not guessed."""
    base = audio_dir or path.parent
    items, problems = [], []
    with open(path, newline="", encoding="utf-8-sig") as f:
        rd = csv.DictReader(f)
        cols = {c.strip().lower(): c for c in (rd.fieldnames or [])}
        fc = next((cols[c] for c in FILE_COLS if c in cols), None)
        bc = next((cols[c] for c in BPM_COLS if c in cols), None)
        if not fc or not bc:
            raise LabelError(f"{path.name}: need a file column ({'/'.join(FILE_COLS)}) and a bpm column ({'/'.join(BPM_COLS)}); found {list(cols)}")
        for i, row in enumerate(rd, start=2):
            name, raw = (row.get(fc) or "").strip(), (row.get(bc) or "").strip()
            try:
                bpm = float(raw)
                if not (20.0 <= bpm <= 400.0):
                    raise ValueError
            except ValueError:
                problems.append(f"row {i}: '{name}' has no usable bpm ('{raw}')")
                continue
            p = Path(name) if Path(name).is_absolute() else base / name
            if not p.exists():
                problems.append(f"row {i}: file not found: {name}")
                continue
            items.append((p, bpm))
    return items, problems


def from_filenames(folder: Path) -> Tuple[List[Tuple[Path, float]], List[str]]:
    items, problems = [], []
    for p in sorted(folder.rglob("*")):
        if p.suffix.lower() not in AUDIO_EXT:
            continue
        bpm = bpm_from_name(p.stem)
        if bpm is None or not (20.0 <= bpm <= 400.0):
            problems.append(f"no bpm in file name: {p.name}")
        else:
            items.append((p, bpm))
    return items, problems
