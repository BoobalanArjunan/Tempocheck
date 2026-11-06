# tempocheck

**Check that the BPM labels on your music files match the audio.**

Wrong tempo labels quietly hurt music-AI training (tempo-conditioned generation, DJ tools, retrieval). tempocheck listens to each file, measures its tempo, and tells you which labels look wrong, which are only a half/double-tempo difference, and which it cannot judge.

> **Status: alpha (0.1.0a1).** Validated against tempo benchmarks (46 synthetic unit tests passing, zero false alarms on true labels). See [Benchmark validation results](#benchmark-validation-results) and [docs/REAL_DATA_CHECK.md](docs/REAL_DATA_CHECK.md).

## Install

```bash
pip install --pre tempocheck      # after it is published; until then: pip install -e ".[dev]"
```
Needs Python 3.9+. Depends only on numpy, scipy, soundfile.

## Use

Labels from a CSV (columns `file` and `bpm`):
```bash
tempocheck check labels.csv --audio-dir songs/ --out verdicts.csv
```
or from file names like `night_drive_124bpm.wav`:
```bash
tempocheck check songs/
```
Options: `--show-pass` (also list good files), `--jobs 4` (parallel).

## What the verdicts mean

| verdict | meaning | exit code |
|---|---|---|
| PASS | measured tempo is within 4% of the label | 0 |
| WARN | measured tempo is half, double, a third, 3x, 1.5x or 2/3 of the label. Both can feel right, so it is a warning | 0 |
| REVIEW | cannot judge: no steady pulse, tempo changes inside the file, too short/silent, or the audio supports both the label and the measured tempo | 0 |
| FAIL | the audio clearly says a different tempo and does not support the label | 1 |
| ERROR | file could not be read | 0 |

## Benchmark validation results

Tested with `scripts/real_data_check.py` across diverse tempos with planted label discrepancies. Detailed findings are in [`real_check/results.md`](real_check/results.md):

- **False alarm rate on true labels**: **0.0%** (21 PASS, 4 WARN, 0 FAIL)
- **Deliberately wrong labels caught (20%+ away)**: **88%** (22/25 marked FAIL)
- **Tempo estimation accuracy**:
  - **Acc1** (exact match within 4% tolerance): **84.0%**
  - **Acc2** (including half/double/3x/1.5x harmonic tempo relations): **100.0%**
- **Planted false alarm check**: 0 false alarms on true BPM labels.

## Limits (read these)

- **Judgement defaults.** Numbers like the 4% tolerance and the "clear pulse" strength are reasoned defaults.
- It is a simple estimator (onset curve + tempogram). Strong hi-hat or off-beat patterns can make it report double tempo; that shows up as WARN, not FAIL.
- Songs without a steady beat (ambient, rubato, classical) are REVIEW, not wrong.
- Only the middle 3 minutes of a file are used. Tempo changes inside a file are flagged REVIEW.
- A FAIL means "the audio disagrees with the label", not "the label is wrong": listen to the file.

## Tests

`pytest -q` (46 tests on synthetic songs). A planted-bug check (29 deliberate bugs in the code) was caught by the tests.

MIT licensed.
