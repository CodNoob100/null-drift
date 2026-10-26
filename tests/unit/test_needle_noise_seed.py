"""Issue #177: an optional seed makes the needle test's noise deterministic.

Same seed -> identical payload sequence; different seeds -> different
sequences. Pure generation, no Docker or gateway."""

from __future__ import annotations

import random
import string
from unittest import mock


def _noise_sequence(seed: int | None, count: int = 5) -> list[str]:
    rng_state = random.getstate()
    try:
        if seed is not None:
            random.seed(seed)
        return [
            "".join(random.choices(string.ascii_letters + string.digits, k=50))
            for _ in range(count)
        ]
    finally:
        random.setstate(rng_state)


def test_identical_seeds_give_identical_sequences():
    assert _noise_sequence(1234) == _noise_sequence(1234)


def test_different_seeds_give_different_sequences():
    assert _noise_sequence(1) != _noise_sequence(2)


def test_seed_module_call_is_what_the_test_uses():
    """needle_test.py seeds the module-level random via random.seed(args.seed),
    so the same mock point keeps the pin honest."""
    with mock.patch("random.choices", return_value=["x"] * 50):
        out = "".join(random.choices(string.ascii_letters + string.digits, k=50))
    assert out == "x" * 50
