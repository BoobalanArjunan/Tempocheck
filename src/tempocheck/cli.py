from __future__ import annotations

import argparse
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from . import __version__
from .check import TOL, check_file
from .labels import LabelError, from_filenames, read_csv
from .report import summary_line, text, write_csv


def _job(args):
    return check_file(*args)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="tempocheck", description="Check that the BPM labels on your music match the audio.")
    ap.add_argument("--version", action="version", version=f"tempocheck {__version__}")
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("check", help="check labels from a CSV, or from a folder of files named like song_120bpm.wav")
    c.add_argument("source", type=Path, help="labels.csv (columns: file, bpm) or a folder")
    c.add_argument("--audio-dir", type=Path, help="folder the CSV's file names are relative to (default: the CSV's folder)")
    c.add_argument("--out", type=Path, help="write every verdict to this CSV")
    c.add_argument("--show-pass", action="store_true", help="also list files that passed")
    c.add_argument("--jobs", type=int, default=1, help="files analysed in parallel (default 1)")
    a = ap.parse_args(argv)

    try:
        if a.source.is_dir():
            items, problems = from_filenames(a.source)
        elif a.source.is_file():
            items, problems = read_csv(a.source, a.audio_dir)
        else:
            print(f"error: {a.source} not found", file=sys.stderr)
            return 2
    except LabelError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    if not items:
        print("error: nothing to check" + (f" ({len(problems)} label problems, e.g. {problems[0]})" if problems else ""), file=sys.stderr)
        return 2
    if a.jobs > 1:
        with ProcessPoolExecutor(a.jobs) as ex:
            vs = list(ex.map(_job, items, chunksize=1))
    else:
        vs = [check_file(p, b) for p, b in items]
    print(text(vs, problems, a.show_pass))
    if a.out:
        write_csv(a.out, vs)
    return 1 if any(v.level == "FAIL" for v in vs) else 0


if __name__ == "__main__":
    sys.exit(main())
