# tempocheck

**Check that the BPM labels on your music files match the audio.**

Wrong tempo labels quietly hurt music-AI training (tempo-conditioned generation, DJ tools, retrieval). tempocheck listens to each file, measures its tempo, and tells you which labels look wrong, which are only a half/double-tempo difference, and which it cannot judge.

> **Status: alpha (0.1.0a1).** Tested on synthetic songs with a known tempo only. **Not yet measured on real music.** Run `scripts/real_data_check.py` on a labelled set (see `docs/REAL_DATA_CHECK.md`) before trusting it on your data.

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

## Limits (read these)

- **Not validated on real music yet.** Numbers like the 4% tolerance and the "clear pulse" strength are judgement defaults.
- It is a simple estimator (onset curve + tempogram). Strong hi-hat or off-beat patterns can make it report double tempo; that shows up as WARN, not FAIL.
- Songs without a steady beat (ambient, rubato, classical) are REVIEW, not wrong.
- Only the middle 3 minutes of a file are used. Tempo changes inside a file are flagged REVIEW.
- A FAIL means "the audio disagrees with the label", not "the label is wrong": listen to the file.

## Tests

`pytest -q` (46 tests on synthetic songs). A planted-bug check (29 deliberate bugs in the code) was caught by the tests.

MIT licensed.
