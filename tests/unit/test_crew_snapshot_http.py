"""Unit tests for status handling in the synchronous Crew-style adapter.

These tests mock HTTP responses and do not require a running gateway.
"""

import unittest
from unittest.mock import patch

import httpx

from nulldrift_agents import NullDriftCrewStorage


class CrewSnapshotStatusTests(unittest.TestCase):
    def setUp(self):
        client_patch = patch("nulldrift_agents.httpx.Client")
        self.mock_client_factory = client_patch.start()
        self.addCleanup(client_patch.stop)
        self.adapter = NullDriftCrewStorage(
            gateway_url="http://localhost:8000/", thread_id="starter"
        )
        self.client = self.mock_client_factory.return_value

    def test_successful_checkpoint_requests_check_http_status(self):
        for method_name, route in [
            ("take_snapshot", "/snapshot"),
            ("restore_from_snapshot", "/restore"),
        ]:
            with self.subTest(route=route):
                self.client.reset_mock()
                getattr(self.adapter, method_name)()
                self.client.post.assert_called_once_with(
                    f"http://localhost:8000{route}",
                    params={"thread_id": "starter"},
                )
                self.client.post.return_value.raise_for_status.assert_called_once_with()

    def test_checkpoint_http_errors_are_logged(self):
        for method_name, route in [
            ("take_snapshot", "/snapshot"),
            ("restore_from_snapshot", "/restore"),
        ]:
            with self.subTest(route=route):
                self.client.reset_mock()
                request = httpx.Request("POST", f"http://localhost:8000{route}")
                response = httpx.Response(503, request=request)
                self.client.post.return_value.raise_for_status.side_effect = (
                    httpx.HTTPStatusError(
                        "backend unavailable", request=request, response=response
                    )
                )
                with patch("nulldrift_agents.logging.error") as log_error:
                    getattr(self.adapter, method_name)()
                self.client.post.return_value.raise_for_status.assert_called_once_with()
                log_error.assert_called_once()


if __name__ == "__main__":
    unittest.main()
