"""tempocheck: does the BPM label on a music file match the audio?"""
from ._version import __version__
from .check import Verdict, check_file, judge

__all__ = ["__version__", "Verdict", "check_file", "judge"]
