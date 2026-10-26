"""Issue #178: the benchmark's latency summary is a pure, testable helper."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.benchmark import latency_summary  # noqa: E402


def test_single_sample_is_the_mean():
    assert latency_summary([12.0]) == "12.00 ms"


def test_multiple_samples_average():
    assert latency_summary([10.0, 20.0, 30.0]) == "20.00 ms"


def test_empty_samples_are_explicit():
    assert latency_summary([]) == "unavailable (no samples)"
