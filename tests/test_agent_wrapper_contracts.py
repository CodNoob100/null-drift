"""Offline HTTP contract tests for the current null-drift agent wrappers.

These do not establish compatibility with upstream LangGraph or CrewAI interfaces.
"""

import unittest
from unittest.mock import AsyncMock, Mock

from nulldrift_agents import NullDriftCrewStorage, NullDriftLangGraphStore


class CrewStorageTests(unittest.TestCase):
    def test_save_routes_thread_and_payload(self):
        storage = NullDriftCrewStorage(thread_id="crew-a")
        try:
            storage.client.post = Mock(return_value=Mock())
            storage.save({"task": "hello"})
            args, kwargs = storage.client.post.call_args
            self.assertTrue(args[0].endswith("/inject"))
            self.assertEqual(kwargs["params"], {"thread_id": "crew-a"})
            self.assertIn('"task": "hello"', kwargs["json"]["text"])
        finally:
            storage.client.close()

    def test_search_returns_empty_when_no_memory(self):
        storage = NullDriftCrewStorage(thread_id="crew-b")
        try:
            storage.client.get = Mock(return_value=Mock(json=lambda: {}))
            self.assertEqual(storage.search("missing"), [])
            self.assertEqual(
                storage.client.get.call_args.kwargs["params"],
                {"thread_id": "crew-b"},
            )
        finally:
            storage.client.close()


class LangGraphWrapperTests(unittest.IsolatedAsyncioTestCase):
    async def test_put_routes_namespace_and_key(self):
        storage = NullDriftLangGraphStore()
        try:
            storage.client.post = AsyncMock(return_value=Mock())
            await storage.aput(("team", "agent"), "key-1", {"value": 1})
            args, kwargs = storage.client.post.call_args
            self.assertTrue(args[0].endswith("/inject"))
            self.assertEqual(kwargs["params"], {"thread_id": "team_agent"})
            self.assertIn('"key": "key-1"', kwargs["json"]["text"])
        finally:
            await storage.client.aclose()

    async def test_get_ignores_mismatched_key(self):
        storage = NullDriftLangGraphStore()
        try:
            recovered = '{"key": "other", "value": {"x": 1}}'
            response = Mock(json=lambda: {"recovered_text": recovered})
            storage.client.get = AsyncMock(return_value=response)
            self.assertIsNone(await storage.aget(("team",), "wanted"))
        finally:
            await storage.client.aclose()


if __name__ == "__main__":
    unittest.main()
