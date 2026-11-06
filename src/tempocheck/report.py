from __future__ import annotations

import csv
from collections import Counter
from typing import List

from .check import Verdict


def summary_line(vs: List[Verdict]) -> str:
    c = Counter(v.level for v in vs)
    return f"{len(vs)} files: {c['PASS']} pass, {c['WARN']} warn (half/double tempo), {c['REVIEW']} need a look, {c['FAIL']} fail, {c['ERROR']} unreadable"


def text(vs: List[Verdict], problems: List[str], show_pass: bool = False) -> str:
    L = []
    for v in vs:
        if v.level == "PASS" and not show_pass:
            continue
        est = f"{v.estimate:g}" if v.estimate else "-"
        L.append(f"{v.level:6} {v.file}  label {v.label:g}  measured {est}  {v.reason}")
    if problems:
        L += ["", f"{len(problems)} label problems (not checked):"] + [f"  {p}" for p in problems[:50]]
        if len(problems) > 50:
            L.append(f"  ... and {len(problems) - 50} more")
    L += ["", summary_line(vs)]
    return "\n".join(L)


def write_csv(path, vs: List[Verdict]) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["file", "label_bpm", "measured_bpm", "verdict", "reason", "pulse_strength"])
        for v in vs:
            w.writerow([v.file, v.label, "" if v.estimate is None else v.estimate, v.level, v.reason, round(v.prominence, 2)])
