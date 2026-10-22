"""Offline result checks; no gateway or noise-event injection is required."""

import contextlib
import io
from pathlib import Path
import runpy
import subprocess
import sys
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "advanced" / "needle_test.py"
NEEDLE_TEST = runpy.run_path(str(SCRIPT))


class NeedleRecallTests(unittest.TestCase):
    def test_exact_needle_succeeds_and_preserves_message(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            NEEDLE_TEST["check_recall"](NEEDLE_TEST["NEEDLE"])
        self.assertIn("[SUCCESS] Needle perfectly recovered", output.getvalue())
        self.assertNotIn("[FAILURE]", output.getvalue())

    def test_wrong_or_missing_needle_raises_and_preserves_message(self):
        for recovered in ("wrong result", None, ""):
            with self.subTest(recovered=recovered):
                output = io.StringIO()
                with contextlib.redirect_stdout(output):
                    with self.assertRaisesRegex(
                        AssertionError, "did not recover the needle"
                    ):
                        NEEDLE_TEST["check_recall"](recovered)
                self.assertIn("[FAILURE] Needle was lost", output.getvalue())
                self.assertNotIn("[SUCCESS]", output.getvalue())

    def test_mismatch_fails_process_even_with_optimization(self):
        code = "import runpy, sys; module = runpy.run_path(sys.argv[1]); module['check_recall'](None)"
        for flags in ([], ["-O"]):
            with self.subTest(flags=flags):
                result = subprocess.run(
                    [sys.executable, *flags, "-c", code, str(SCRIPT)],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("[FAILURE]", result.stdout)
                self.assertIn("AssertionError", result.stderr)

    def test_matching_result_exits_successfully(self):
        code = (
            "import runpy, sys; module = runpy.run_path(sys.argv[1]); "
            "module['check_recall'](module['NEEDLE'])"
        )
        result = subprocess.run(
            [sys.executable, "-c", code, str(SCRIPT)],
            capture_output=True,
            text=True,
            timeout=10,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("[SUCCESS]", result.stdout)
