"""Real-data check for tempocheck. Needs real songs WITH trusted tempo labels (for example the GiantSteps Tempo dataset,
GTZAN with its tempo annotations, or the Ballroom dataset), as a folder of audio plus a labels CSV (file,bpm).

    python scripts/real_data_check.py --labels labels.csv --audio-dir songs/ --out real_check

It answers:
  1. FALSE ALARMS: with the TRUE labels, how many songs does tempocheck call WRONG (FAIL)? Should be a few percent at most.
  2. HOW MANY LABELS IT CATCHES: it swaps each label for a wrong one (a different song's tempo, at least 20% away) and counts FAIL.
  3. Plain accuracy of the tempo estimate: within 4% (Acc1) and within 4% allowing half/double/third/3-2 (Acc2).
Your files are never changed. Writes <out>/results.md and <out>/verdicts.csv.
"""
from __future__ import annotations

import argparse
import collections
import random
import sys
from pathlib import Path

from tempocheck.check import RELATIONS, TOL, check_file, close
from tempocheck.labels import read_csv
from tempocheck.report import write_csv


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--labels", type=Path, required=True)
    ap.add_argument("--audio-dir", type=Path)
    ap.add_argument("--limit", type=int, default=300, help="songs to use (default 300)")
    ap.add_argument("--out", type=Path, default=Path("real_check"))
    ap.add_argument("--seed", type=int, default=0)
    a = ap.parse_args()
    items, problems = read_csv(a.labels, a.audio_dir)
    if len(items) < 20:
        sys.exit(f"only {len(items)} usable rows ({len(problems)} problems); need at least 20")
    rng = random.Random(a.seed)
    rng.shuffle(items)
    items = items[: a.limit]
    a.out.mkdir(parents=True, exist_ok=True)

    true_v, wrong_v = [], []
    for i, (p, bpm) in enumerate(items, 1):
        v = check_file(p, bpm)
        true_v.append(v)
        far = [b for _, b in items if abs(b - bpm) > 0.2 * bpm]
        wrong_v.append(check_file(p, rng.choice(far)) if (far and v.estimate) else None)
        if i % 25 == 0:
            print(f"  {i}/{len(items)}", flush=True)
    write_csv(a.out / "verdicts.csv", true_v)
    n = len(true_v)
    lv = collections.Counter(v.level for v in true_v)
    readable = [v for v in true_v if v.estimate]
    acc1 = sum(close(v.estimate, v.label) for v in readable)
    acc2 = sum(close(v.estimate, v.label) or any(close(v.estimate, v.label * r) for r, _ in RELATIONS) for v in readable)
    wv = [w for w in wrong_v if w]
    caught = sum(w.level == "FAIL" for w in wv)
    L = ["# tempocheck: real-data check", "", f"{n} songs, tolerance {TOL:.0%}.", "",
         "## 1. With the TRUE labels (every FAIL here is a false alarm)", "",
         f"- PASS {lv['PASS']}, WARN (half/double) {lv['WARN']}, REVIEW {lv['REVIEW']}, FAIL {lv['FAIL']}, ERROR {lv['ERROR']}",
         f"- **False alarm rate (FAIL): {100 * lv['FAIL'] / n:.1f}%**", "",
         "## 2. With deliberately WRONG labels", "",
         f"- {len(wv)} songs given a wrong label (20%+ away): FAIL on **{caught} ({100 * caught / max(1, len(wv)):.0f}%)**",
         f"- the rest: " + ", ".join(f"{k} {v}" for k, v in collections.Counter(w.level for w in wv if w.level != 'FAIL').items()), "",
         "## 3. Plain tempo accuracy", "",
         f"- Acc1 (within {TOL:.0%}): {100 * acc1 / max(1, len(readable)):.1f}%   Acc2 (also half/double/3x/1.5x): {100 * acc2 / max(1, len(readable)):.1f}%", "",
         "For scale: good published trackers reach roughly 60-70% Acc1 and 85-95% Acc2 on hard sets such as GiantSteps. "
         "tempocheck is a simple estimator, so lower is plausible; what matters most is section 1 (false alarms).", "",
         "Songs with a FAIL on the true label (check these by ear, the label may be the thing that is wrong):", ""]
    L += [f"- {v.file}: label {v.label:g}, measured {v.estimate:g}" for v in true_v if v.level == "FAIL"][:40] or ["- none"]
    (a.out / "results.md").write_text("\n".join(L), encoding="utf-8")
    print("\n".join(L))


if __name__ == "__main__":
    main()
