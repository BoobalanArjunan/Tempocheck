# Real-data check for tempocheck (about 30 minutes)

The tests use synthetic songs. This check uses real songs with trusted tempo labels.

## Tasks
1. Install: `pip install -e ".[dev]"`, then `pytest -q` (expect 46 passed).
2. Get a labelled set. Easiest: the **GiantSteps Tempo** dataset (electronic music, ~660 clips with BPM) or **Ballroom** (698 clips with BPM). Make a `labels.csv` with columns `file,bpm`.
3. Run: `python scripts/real_data_check.py --labels labels.csv --audio-dir <audio folder> --out real_check`
4. Send me `real_check/results.md`.
5. Listen to 5 songs from the "FAIL on the true label" list and tell me: is the label wrong, or is tempocheck wrong?

## How the numbers get used
- False alarm rate above about 5%: I raise the tolerance or the pulse-strength limit, or change the estimator.
- Wrong labels caught below about 70%: I look at what the misses have in common.
- Acc2 far below 85%: the estimator needs work before any release.
