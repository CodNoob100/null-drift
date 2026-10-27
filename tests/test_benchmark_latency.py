import pytest

from scripts.benchmark import summarize_latency


def test_summarize_latency_single_sample():
    assert summarize_latency([12.5]) == (12.5, 12.5, 12.5)


def test_summarize_latency_multiple_samples():
    assert summarize_latency([8, 12, 16, 24]) == (15, 8, 24)


def test_summarize_latency_empty_samples():
    with pytest.raises(ValueError, match="cannot be empty"):
        summarize_latency([])
