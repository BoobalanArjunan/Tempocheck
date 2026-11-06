"""Known answers: every song is generated at an exact tempo, so we know what the right verdict is."""
import csv

import numpy as np
import pytest

from conftest import SR, song, write
from tempocheck import check, estimate as est
from tempocheck.cli import main
from tempocheck.features import onset_envelope, load_mono
from tempocheck.labels import bpm_from_name, from_filenames, read_csv, LabelError


def verdict(label, x):
    return check.judge(label, est.estimate(onset_envelope(x)))


# ------------------------------------------------------------------ the estimator
@pytest.mark.parametrize("bpm", [90, 100, 110, 120, 128, 140, 150, 160])
@pytest.mark.parametrize("seed", [0, 1])
def test_a_correct_label_passes_on_clear_songs(bpm, seed):
    v = verdict(bpm, song(bpm, seed, swing=0.3 * seed))
    assert v.status == check.OK, v.reason
    assert abs(v.estimate - bpm) <= 0.04 * bpm


@pytest.mark.parametrize("true,label", [(120, 95), (100, 133), (140, 105), (90, 121), (128, 100), (110, 150)])
def test_a_wrong_label_fails_and_says_what_the_audio_says(true, label):
    v = verdict(label, song(true, 3))
    assert v.status == check.WRONG and v.level == "FAIL"
    assert abs(v.estimate - true) <= 0.04 * true and f"{label:g}" in v.reason


def test_half_and_double_labels_are_a_warning_not_a_failure():
    v = verdict(60, song(120, 2))
    assert v.status == check.OCTAVE and v.level == "WARN" and "2x" in v.reason
    v = verdict(240, song(120, 2))
    assert v.status == check.OCTAVE and "half" in v.reason


def test_a_label_within_4_percent_passes_and_just_outside_does_not():
    x = song(120, 4)
    assert verdict(124.5, x).status == check.OK
    assert verdict(131, x).status == check.WRONG


def test_noise_without_a_pulse_is_unsure_not_wrong():
    x = (0.1 * np.random.RandomState(0).randn(SR * 30)).astype(np.float32)
    v = verdict(120, x)
    assert v.status == check.UNSURE and "no clear steady pulse" in v.reason


def test_a_tempo_change_inside_the_file_is_unsure():
    x = song(100, 5, seconds=60.0, ramp_to=150)
    v = verdict(100, x)
    assert v.status == check.UNSURE and "tempo changes" in v.reason


def test_silence_and_very_short_audio_are_unsure():
    assert verdict(120, np.zeros(SR * 10, dtype=np.float32)).status == check.UNSURE
    assert verdict(120, song(120, 0)[: SR // 4]).status == check.UNSURE


def test_loud_swing_and_timing_jitter_do_not_break_a_correct_label():
    v = verdict(120, song(120, 6, swing=0.6, jitter_ms=12.0))
    assert v.status == check.OK


def test_load_mono_resamples_and_crops_long_files(tmp_path):
    x = song(120, 0)
    p = write(tmp_path / "a.wav", np.stack([x, x], axis=1), SR)
    assert len(load_mono(p)) == len(x)
    import soundfile as sf
    sf.write(str(tmp_path / "b.wav"), np.tile(x[:SR * 4], (2, 1)).T.copy()[:, 0], 44100)
    assert abs(len(load_mono(tmp_path / "b.wav")) - SR * 4 / 2) < 5     # 44.1 kHz -> 22.05 kHz halves the length
    assert len(load_mono(p, max_seconds=10)) == 10 * SR


# ------------------------------------------------------------------ labels
def test_bpm_in_file_names():
    assert bpm_from_name("song_120bpm") == 120 and bpm_from_name("Song 98 BPM") == 98
    assert bpm_from_name("a-87.5-bpm") == 87.5 and bpm_from_name("track01") is None and bpm_from_name("2024_song") is None


def test_csv_with_missing_files_and_bad_bpm_reports_each_problem(tmp_path):
    write(tmp_path / "a.wav", song(120, 0), SR)
    (tmp_path / "l.csv").write_text("File,BPM\na.wav,120\nmissing.wav,100\na.wav,abc\na.wav,\na.wav,900\n", encoding="utf-8")
    items, problems = read_csv(tmp_path / "l.csv")
    assert [(p.name, b) for p, b in items] == [("a.wav", 120.0)]
    assert len(problems) == 4 and any("not found" in p for p in problems) and sum("no usable bpm" in p for p in problems) == 3


def test_csv_without_the_right_columns_is_an_error(tmp_path):
    (tmp_path / "l.csv").write_text("x,y\n1,2\n", encoding="utf-8")
    with pytest.raises(LabelError):
        read_csv(tmp_path / "l.csv")


def test_from_filenames_skips_non_audio_and_unlabelled_files(tmp_path):
    for n in ("a_120bpm.wav", "b.wav", "c_90bpm.flac", "notes_100bpm.txt"):
        (tmp_path / n).write_bytes(b"x")
    items, problems = from_filenames(tmp_path)
    assert sorted(p.name for p, _ in items) == ["a_120bpm.wav", "c_90bpm.flac"] and len(problems) == 1


# ------------------------------------------------------------------ command line
def test_cli_exit_codes_and_report(tmp_path, capsys):
    write(tmp_path / "right.wav", song(120, 7), SR)
    write(tmp_path / "wrong.wav", song(100, 8), SR)
    write(tmp_path / "half.wav", song(128, 9), SR)
    (tmp_path / "l.csv").write_text("file,bpm\nright.wav,120\nwrong.wav,140\nhalf.wav,64\n", encoding="utf-8")
    code = main(["check", str(tmp_path / "l.csv"), "--out", str(tmp_path / "o.csv")])
    out = capsys.readouterr().out
    assert code == 1
    assert "FAIL   wrong.wav" in out and "WARN   half.wav" in out and "right.wav" not in out.split("\n\n")[0]
    assert "3 files: 1 pass, 1 warn" in out and "1 fail" in out
    rows = {r["file"]: r for r in csv.DictReader(open(tmp_path / "o.csv"))}
    assert rows["right.wav"]["verdict"] == "PASS" and rows["wrong.wav"]["verdict"] == "FAIL" and rows["half.wav"]["measured_bpm"]


def test_cli_passes_with_exit_0_and_show_pass_lists_files(tmp_path, capsys):
    write(tmp_path / "ok_120bpm.wav", song(120, 7), SR)
    assert main(["check", str(tmp_path), "--show-pass"]) == 0
    assert "PASS   ok_120bpm.wav" in capsys.readouterr().out


def test_cli_usage_errors_exit_2(tmp_path, capsys):
    assert main(["check", str(tmp_path / "nope.csv")]) == 2
    assert main(["check", str(tmp_path)]) == 2                                        # an empty folder: nothing to check
    (tmp_path / "bad.csv").write_text("a,b\n1,2\n", encoding="utf-8")
    assert main(["check", str(tmp_path / "bad.csv")]) == 2


def test_an_unreadable_audio_file_is_an_error_row_not_a_crash(tmp_path, capsys):
    (tmp_path / "broken_120bpm.wav").write_bytes(b"not audio")
    assert main(["check", str(tmp_path)]) == 0
    assert "ERROR  broken_120bpm.wav" in capsys.readouterr().out


# ------------------------------------------------------------------ edges found by planting bugs
def test_close_is_measured_against_the_label_not_the_estimate():
    assert check.close(103.9, 100) and not check.close(104.1, 100) and not check.close(95.9, 100) and check.close(96.1, 100)


def test_when_the_audio_has_two_competing_tempi_the_verdict_is_unsure_not_wrong():
    mix = song(100, 1) + 0.6 * song(137, 2)                    # two unrelated pulses; the 137 one is a little stronger
    t = est.estimate(onset_envelope(mix))
    assert abs(t.bpm - 137) <= 0.04 * 137
    v = check.judge(100, t)
    assert v.status == check.UNSURE and "supports both" in v.reason
    assert check.judge(115, t).status == check.WRONG           # a label the audio does not support at all is still wrong


def test_silent_audio_says_so_in_plain_words():
    assert "too short or silent" in verdict(120, np.zeros(SR * 10, dtype=np.float32)).reason


def test_a_stereo_file_with_sound_only_on_one_side_is_still_measured(tmp_path):
    x = song(120, 0)
    p = write(tmp_path / "r.wav", np.stack([np.zeros_like(x), x], axis=1), SR)
    assert np.abs(load_mono(p)).max() > 0.1
    assert check.check_file(p, 120).status == check.OK


def test_the_onset_curve_peaks_at_the_start_of_a_sound_not_its_end():
    rng = np.random.RandomState(0)
    x = (1e-4 * rng.randn(SR * 3)).astype(np.float32)
    x[SR:int(1.3 * SR)] += 0.5 * rng.randn(int(0.3 * SR)).astype(np.float32)
    env = onset_envelope(x)
    from tempocheck.features import FPS
    start, end = int(1.0 * FPS), int(1.3 * FPS)
    assert env[start - 3:start + 3].max() > 3 * max(env[end - 1:end + 3].max(), 1e-9)


def test_numbers_glued_to_other_digits_are_not_a_bpm():
    assert bpm_from_name("a1120bpm") is None and bpm_from_name("take3_95bpm") == 95


def test_csv_with_a_byte_order_mark_is_read(tmp_path):
    write(tmp_path / "a.wav", song(120, 0), SR)
    (tmp_path / "l.csv").write_bytes("file,bpm\na.wav,120\n".encode("utf-8-sig"))
    items, problems = read_csv(tmp_path / "l.csv")
    assert len(items) == 1 and not problems


def test_a_long_problem_list_is_cut_with_a_count(tmp_path, capsys):
    write(tmp_path / "a.wav", song(120, 0), SR)
    rows = "\n".join(f"gone{i}.wav,120" for i in range(60))
    (tmp_path / "l.csv").write_text("file,bpm\na.wav,120\n" + rows + "\n", encoding="utf-8")
    assert main(["check", str(tmp_path / "l.csv")]) == 0
    out = capsys.readouterr().out
    assert "60 label problems" in out and "and 10 more" in out and out.count("file not found") == 50


def test_only_a_failure_gives_exit_code_1_a_warning_does_not(tmp_path):
    write(tmp_path / "half.wav", song(128, 9), SR)
    (tmp_path / "l.csv").write_text("file,bpm\nhalf.wav,64\n", encoding="utf-8")
    assert main(["check", str(tmp_path / "l.csv")]) == 0
