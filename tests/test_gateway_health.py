"""Offline unit tests for the standard-library gateway readiness probe."""

import io
import json
import unittest
from unittest.mock import patch
from urllib.error import URLError

from scripts.check_gateway_health import check_health, validate_local_url


class GatewayHealthTests(unittest.TestCase):
    def test_ready(self):
        with patch(
            "scripts.check_gateway_health.urllib.request.build_opener"
        ) as open_url:
            payload = io.BytesIO(json.dumps({"status": "ok"}).encode("utf-8"))
            open_url.return_value.open.return_value.__enter__.return_value = payload
            self.assertTrue(check_health("http://127.0.0.1:8000/"))
            self.assertEqual(
                open_url.return_value.open.call_args.args[0],
                "http://127.0.0.1:8000/health",
            )

    def test_unavailable_status(self):
        with patch(
            "scripts.check_gateway_health.urllib.request.build_opener"
        ) as open_url:
            payload = io.BytesIO(json.dumps({"status": "unavailable"}).encode("utf-8"))
            open_url.return_value.open.return_value.__enter__.return_value = payload
            self.assertFalse(check_health("http://127.0.0.1:8000"))

    def test_local_url_validation(self):
        for url in (
            "http://127.0.0.1:8000",
            "http://localhost:8000",
            "http://[::1]:8000",
        ):
            self.assertEqual(validate_local_url(url), url)
        for url in (
            "http://127.0.0.1:8000@evil.example:80",
            "http://localhost.evil.example:8000",
            "http://127.0.0.1:8000/other",
            "https://127.0.0.1:8000",
            "http://127.0.0.1:bad",
            "http://127.0.0.1:8000?redirect=evil",
        ):
            with self.subTest(url=url), self.assertRaises(ValueError):
                validate_local_url(url)

    def test_transport_failure(self):
        with patch("scripts.check_gateway_health.urllib.request.build_opener") as mock:
            mock.return_value.open.side_effect = URLError("offline")
            with self.assertRaises(URLError):
                check_health("http://127.0.0.1:8000")


if __name__ == "__main__":
    unittest.main()
