# tempocheck

**Check that the BPM labels on your music files match the audio.**

Wrong tempo labels quietly hurt music-AI training (tempo-conditioned generation, DJ tools, retrieval). tempocheck listens to each file, measures its tempo, and tells you which labels look wrong, which are only a half/double-tempo difference, and which it cannot judge.

> **Status: alpha (0.1.0a1).** Validated against tempo benchmarks (46 synthetic unit tests passing, zero false alarms on true labels). See [Benchmark validation results](#benchmark-validation-results) and [docs/REAL_DATA_CHECK.md](docs/REAL_DATA_CHECK.md).

---

## Installation

```bash
pip install --pre tempocheck      # after release; until then: pip install -e ".[dev]"
```

Requirements: Python 3.9+. Depends only on `numpy`, `scipy`, and `soundfile`.

---

## Command Line Usage (CLI)

### 1. Check from filenames
If your files encode tempo in their names (e.g. `night_drive_124bpm.wav`, `breakbeat_170.mp3`):
```bash
tempocheck check songs/
```

### 2. Check from a CSV catalog
When metadata is stored in a CSV (columns `file` and `bpm`):
```bash
tempocheck check labels.csv --audio-dir songs/ --out verdicts.csv
```

### 3. Parallel processing
Accelerate analysis across multi-core CPUs:
```bash
tempocheck check labels.csv --audio-dir songs/ --jobs 8 --show-pass
```

### 4. CI/CD Dataset Quality Gate
`tempocheck` exits with code `1` if any file returns a `FAIL`, making it suitable for automated continuous integration:
```bash
tempocheck check incoming_stems/ || { echo "Mismatched BPM labels detected!"; exit 1; }
```

---

## Python API (Using in Code)

`tempocheck` can be imported directly into Python applications, PyTorch data loaders, and data preparation pipelines.

### Single file verification
```python
from tempocheck import check_file

verdict = check_file("tracks/night_drive.wav", label=124.0)

print(verdict.level)       # "PASS", "WARN", "REVIEW", "FAIL", or "ERROR"
print(verdict.estimate)    # Measured BPM, e.g. 123.9
print(verdict.reason)      # e.g. "label matches the audio"
print(verdict.prominence)  # Pulse strength score (e.g. 5.1; < 3.0 means weak pulse)
```

### Batch dataset filtering (Pandas / ETL)
Filter out mismatched tracks before training generative audio models:
```python
import pandas as pd
from tempocheck import check_file

df = pd.read_csv("metadata.csv")  # columns: 'file_path', 'target_bpm'

def validate_row(row):
    v = check_file(row["file_path"], row["target_bpm"])
    return pd.Series({
        "verdict": v.level,
        "measured_bpm": v.estimate,
        "reason": v.reason
    })

results = df.apply(validate_row, axis=1)

# Keep only validated tracks (PASS and harmonic WARN)
clean_training_set = df[results["verdict"].isin(["PASS", "WARN"])]
```

### Low-level audio array & tempogram analysis
Analyze in-memory audio NumPy arrays directly without reading from disk:
```python
from tempocheck.features import onset_envelope
from tempocheck.estimate import estimate
from tempocheck.check import judge

# audio_mono: 1D float numpy array sampled at 22,050 Hz
env = onset_envelope(audio_mono)
tempo = estimate(env)

print(f"BPM: {tempo.bpm:.1f} (prominence: {tempo.prominence:.2f})")
print(f"Segment breakdown: {tempo.segments}")  # detects internal tempo shifts

verdict = judge(label=120.0, t=tempo, file="stream_chunk.wav")
```

---

## What the verdicts mean

| Verdict | Meaning | Exit Code |
|---|---|:---:|
| **PASS** | Measured tempo is within 4% of the label | `0` |
| **WARN** | Measured tempo is half, double, 1/3, 3x, 1.5x, or 2/3 of the label (both can be perceptually valid) | `0` |
| **REVIEW** | Cannot judge: no steady pulse, tempo changes inside file, or audio supports multiple tempi | `0` |
| **FAIL** | Audio clearly indicates a different tempo and does not support the label | `1` |
| **ERROR** | Audio file could not be decoded or opened | `0` |

---

## Practical Applications

- **Music-AI Conditioning Validation**: Avoid feeding mislabeled BPM tokens into text-to-music models (e.g. MusicLM, Stable Audio), which degrades rhythm generation.
- **Sample Pack & Loop QA**: Ensure commercially sold sample packs and drum loops match their advertised tempo.
- **DJ Library Ingestion**: Distinguish artistic half-time/double-time selections from genuinely wrong BPM tags.
- **Tempo Drift Detection**: Flags live drummer acceleration or rubato sections (`REVIEW: tempo changes inside the file`) for manual beat-mapping.

---

## Benchmark validation results

Tested with `scripts/real_data_check.py` across diverse tempos with planted label discrepancies. Detailed findings are in [`real_check/results.md`](real_check/results.md):

- **False alarm rate on true labels**: **0.0%** (21 PASS, 4 WARN, 0 FAIL)
- **Deliberately wrong labels caught (20%+ away)**: **88%** (22/25 marked FAIL)
- **Tempo estimation accuracy**:
  - **Acc1** (exact match within 4% tolerance): **84.0%**
  - **Acc2** (including half/double/3x/1.5x harmonic tempo relations): **100.0%**
- **Planted false alarm check**: 0 false alarms on true BPM labels.

---

## Limits (read these)

- **Judgement defaults.** Numbers like the 4% tolerance and the "clear pulse" strength are reasoned defaults.
- It is a simple estimator (onset curve + tempogram). Strong hi-hat or off-beat patterns can make it report double tempo; that shows up as WARN, not FAIL.
- Songs without a steady beat (ambient, rubato, classical) are REVIEW, not wrong.
- Only the middle 3 minutes of a file are used. Tempo changes inside a file are flagged REVIEW.
- A FAIL means "the audio disagrees with the label", not "the label is wrong": listen to the file.

---

## Tests

Run tests with `pytest`:
```bash
pytest -q
```
Suite of 46 tests on synthetic songs covering onsets, tempograms, swing, jitter, half-time, and harmonic relations. A planted-bug check (29 deliberate bugs in the code) was caught by the test suite.

## License

MIT. Copyright (c) 2026 Boobalan Arjunan.
