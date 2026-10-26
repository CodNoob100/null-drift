"""Offline unit tests for the standard-library gateway readiness probe."""
import io
import json
import unittest
from unittest.mock import patch
from urllib.error import URLError

from scripts.check_gateway_health import check_health


class GatewayHealthTests(unittest.TestCase):
    def test_ready(self):
        with patch("scripts.check_gateway_health.urllib.request.urlopen") as open_url:
            open_url.return_value.__enter__.return_value = io.BytesIO(
                json.dumps({"status": "ok"}).encode("utf-8")
            )
            self.assertTrue(check_health("http://127.0.0.1:8000/"))
            self.assertEqual(
                open_url.call_args.args[0], "http://127.0.0.1:8000/health"
            )

    def test_unavailable_status(self):
        with patch("scripts.check_gateway_health.urllib.request.urlopen") as open_url:
            open_url.return_value.__enter__.return_value = io.BytesIO(
                json.dumps({"status": "unavailable"}).encode("utf-8")
            )
            self.assertFalse(check_health("http://127.0.0.1:8000"))

    def test_transport_failure(self):
        with patch(
            "scripts.check_gateway_health.urllib.request.urlopen",
            side_effect=URLError("offline"),
        ):
            with self.assertRaises(URLError):
                check_health("http://127.0.0.1:8000")


if __name__ == "__main__":
    unittest.main()
