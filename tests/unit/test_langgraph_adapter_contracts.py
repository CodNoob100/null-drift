"""Small isolated HTTP contract tests for the async LangGraph-style adapter.

No gateway, embedding model, or CrewAI/LangGraph installation is required.
"""

import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from nulldrift_agents import NullDriftLangGraphStore


class LangGraphAdapterContractTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        client_patch = patch("nulldrift_agents.httpx.AsyncClient")
        self.client_factory = client_patch.start()
        self.addCleanup(client_patch.stop)
        self.client = self.client_factory.return_value
        self.client.post = AsyncMock(return_value=MagicMock())
        self.client.get = AsyncMock(return_value=MagicMock())
        self.client.aclose = AsyncMock()
        self.store = NullDriftLangGraphStore(gateway_url="http://localhost:8000/")
        self.namespace = ("team", "research")

    async def test_put_forwards_namespace_key_and_value(self):
        await self.store.aput(self.namespace, "finding", {"answer": 42})
        self.client.post.assert_awaited_once_with(
            "http://localhost:8000/inject",
            params={"thread_id": "team_research"},
            json={
                "text": '{"key": "finding", "value": {"answer": 42}}',
                "salience": 1.0,
            },
        )
        self.client.post.return_value.raise_for_status.assert_called_once_with()

    async def test_get_returns_only_matching_key(self):
        response = self.client.get.return_value
        response.json.return_value = {
            "recovered_text": '{"key": "finding", "value": {"answer": 42}}'
        }
        result = await self.store.aget(self.namespace, "finding")
        self.assertEqual(result, {"answer": 42})
        self.client.get.assert_awaited_once_with(
            "http://localhost:8000/recall", params={"thread_id": "team_research"}
        )
        response.raise_for_status.assert_called_once_with()

        self.client.get.reset_mock()
        mismatch = await self.store.aget(self.namespace, "different")
        self.assertIsNone(mismatch)

    async def test_get_returns_none_when_no_memory_matches(self):
        self.client.get.return_value.json.return_value = {"recovered_text": None}
        self.assertIsNone(await self.store.aget(self.namespace, "missing"))

    async def test_checkpoint_calls_forward_namespace_and_check_status(self):
        for operation, route in (
            (self.store.take_snapshot, "/snapshot"),
            (self.store.restore_from_snapshot, "/restore"),
        ):
            with self.subTest(route=route):
                self.client.post.reset_mock()
                await operation(self.namespace)
                self.client.post.assert_awaited_once_with(
                    f"http://localhost:8000{route}",
                    params={"thread_id": "team_research"},
                )
                self.client.post.return_value.raise_for_status.assert_called_once_with()

    async def test_async_context_manager_closes_http_client(self):
        async with self.store as opened:
            self.assertIs(opened, self.store)
        self.client.aclose.assert_awaited_once_with()


if __name__ == "__main__":
    unittest.main()
