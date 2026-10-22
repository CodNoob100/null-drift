import json
import unittest
from unittest.mock import AsyncMock, patch

import httpx

from nulldrift_agents import NullDriftLangGraphStore


class TestLangGraphHTTPErrors(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.client = AsyncMock(spec=httpx.AsyncClient)
        client_patch = patch(
            "nulldrift_agents.httpx.AsyncClient", return_value=self.client
        )
        client_patch.start()
        self.addCleanup(client_patch.stop)
        self.store = NullDriftLangGraphStore(gateway_url="http://gateway.invalid")

    async def test_put_logs_http_error_statuses(self):
        for status in (404, 503):
            with self.subTest(status=status):
                self.client.post.return_value = httpx.Response(
                    status,
                    request=httpx.Request("POST", "http://gateway.invalid/inject"),
                )
                with self.assertLogs(level="ERROR") as logs:
                    result = await self.store.aput(
                        ("test",), "key", {"state": "active"}
                    )
                self.assertIsNone(result)
                self.assertIn("NullDrift LangGraph async put failed:", logs.output[0])
                self.assertIn(str(status), logs.output[0])

    async def test_get_logs_http_error_statuses(self):
        for status in (404, 503):
            with self.subTest(status=status):
                self.client.get.return_value = httpx.Response(
                    status,
                    text="not JSON",
                    request=httpx.Request("GET", "http://gateway.invalid/recall"),
                )
                with self.assertLogs(level="ERROR") as logs:
                    result = await self.store.aget(("test",), "key")
                self.assertIsNone(result)
                self.assertIn("NullDrift LangGraph async get failed:", logs.output[0])
                self.assertIn(str(status), logs.output[0])

    async def test_network_errors_are_still_logged(self):
        for operation in ("put", "get"):
            with self.subTest(operation=operation):
                getattr(
                    self.client, "post" if operation == "put" else "get"
                ).side_effect = httpx.ConnectError("connection refused")
                with self.assertLogs(level="ERROR") as logs:
                    if operation == "put":
                        result = await self.store.aput(("test",), "key", {})
                    else:
                        result = await self.store.aget(("test",), "key")
                self.assertIsNone(result)
                self.assertIn(
                    f"async {operation} failed: connection refused", logs.output[0]
                )

    async def test_successful_requests_are_not_logged_as_errors(self):
        self.client.post.return_value = httpx.Response(
            200, request=httpx.Request("POST", "http://gateway.invalid/inject")
        )
        self.client.get.return_value = httpx.Response(
            200,
            json={
                "recovered_text": json.dumps(
                    {"key": "key", "value": {"state": "active"}}
                )
            },
            request=httpx.Request("GET", "http://gateway.invalid/recall"),
        )
        with self.assertNoLogs(level="ERROR"):
            self.assertIsNone(await self.store.aput(("test",), "key", {}))
            self.assertEqual(
                await self.store.aget(("test",), "key"), {"state": "active"}
            )

    async def test_invalid_json_is_not_suppressed(self):
        for body in ("not JSON", json.dumps({"recovered_text": "not JSON"})):
            with self.subTest(body=body):
                self.client.get.return_value = httpx.Response(
                    200,
                    text=body,
                    request=httpx.Request("GET", "http://gateway.invalid/recall"),
                )
                with self.assertRaises(json.JSONDecodeError):
                    await self.store.aget(("test",), "key")

    async def test_unrelated_errors_are_not_suppressed(self):
        self.client.post.side_effect = RuntimeError("unexpected error")
        self.client.get.side_effect = RuntimeError("unexpected error")
        with self.assertRaisesRegex(RuntimeError, "unexpected error"):
            await self.store.aput(("test",), "key", {})
        with self.assertRaisesRegex(RuntimeError, "unexpected error"):
            await self.store.aget(("test",), "key")
