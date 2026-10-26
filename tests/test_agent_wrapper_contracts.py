"""Offline HTTP contract tests for the current null-drift agent wrappers.

These do not establish compatibility with upstream LangGraph or CrewAI interfaces.
"""

import unittest
from unittest.mock import AsyncMock, Mock

import httpx

from nulldrift_agents import (
    NullDriftCrewStorage,
    NullDriftLangGraphStore,
    encode_namespace,
)


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


class NamespaceEncodingTests(unittest.TestCase):
    def test_tuple_boundaries_are_distinct(self):
        self.assertNotEqual(
            encode_namespace(("a_b", "c")), encode_namespace(("a", "b_c"))
        )

    def test_keys_are_isolated(self):
        self.assertNotEqual(
            encode_namespace(("team",), "first"),
            encode_namespace(("team",), "second"),
        )

    def test_namespace_only_and_keyed_identity_differ(self):
        self.assertNotEqual(
            encode_namespace(("team", "agent")),
            encode_namespace(("team",), "agent"),
        )

    def test_long_namespaces_produce_bounded_stable_ids(self):
        namespace = ("tenant-" + "x" * 2000, "agent")
        first = encode_namespace(namespace, "key-" + "y" * 2000)
        self.assertEqual(first, encode_namespace(namespace, "key-" + "y" * 2000))
        self.assertEqual(len(first), 67)
        self.assertTrue(first.startswith("lg_"))

    def test_rejects_empty_namespace(self):
        with self.assertRaises(ValueError):
            encode_namespace(())


class LangGraphWrapperTests(unittest.IsolatedAsyncioTestCase):
    async def test_put_routes_namespace_and_key(self):
        storage = NullDriftLangGraphStore()
        try:
            storage.client.post = AsyncMock(return_value=Mock())
            await storage.aput(("team", "agent"), "key-1", {"value": 1})
            args, kwargs = storage.client.post.call_args
            self.assertTrue(args[0].endswith("/inject"))
            self.assertEqual(
                kwargs["params"], {"thread_id": encode_namespace(("team", "agent"), "key-1")}
            )
            self.assertIn('"key": "key-1"', kwargs["json"]["text"])
        finally:
            await storage.client.aclose()

    async def test_put_and_get_use_same_keyed_thread(self):
        storage = NullDriftLangGraphStore()
        try:
            storage.client.post = AsyncMock(return_value=Mock())
            recovered = '{"key": "key-1", "value": {"value": 1}}'
            storage.client.get = AsyncMock(
                return_value=Mock(json=lambda: {"recovered_text": recovered})
            )
            await storage.aput(("team", "agent"), "key-1", {"value": 1})
            self.assertEqual(
                await storage.aget(("team", "agent"), "key-1"), {"value": 1}
            )
            self.assertEqual(
                storage.client.post.call_args.kwargs["params"],
                storage.client.get.call_args.kwargs["params"],
            )
        finally:
            await storage.client.aclose()

    async def test_put_propagates_transport_failure(self):
        storage = NullDriftLangGraphStore()
        try:
            storage.client.post = AsyncMock(
                side_effect=httpx.ConnectError("gateway offline")
            )
            with self.assertRaises(httpx.ConnectError):
                await storage.aput(("team",), "key-1", {"value": 1})
        finally:
            await storage.client.aclose()

    async def test_get_propagates_transport_failure(self):
        storage = NullDriftLangGraphStore()
        try:
            storage.client.get = AsyncMock(
                side_effect=httpx.ConnectError("gateway offline")
            )
            with self.assertRaises(httpx.ConnectError):
                await storage.aget(("team",), "key-1")
        finally:
            await storage.client.aclose()

    async def test_embedding_failure_is_not_silent(self):
        def broken_embedding(_payload):
            raise RuntimeError("embedding failed")

        storage = NullDriftLangGraphStore(embedding_function=broken_embedding)
        try:
            storage.client.post = AsyncMock()
            with self.assertRaisesRegex(RuntimeError, "embedding failed"):
                await storage.aput(("team",), "key-1", {"value": 1})
            storage.client.post.assert_not_awaited()
        finally:
            await storage.client.aclose()

    async def test_keyed_snapshot_targets_written_thread(self):
        storage = NullDriftLangGraphStore()
        try:
            storage.client.post = AsyncMock(return_value=Mock())
            await storage.aput(("team",), "key-1", {"value": 1})
            write_thread = storage.client.post.call_args.kwargs["params"]
            await storage.take_snapshot(("team",), "key-1")
            self.assertEqual(
                storage.client.post.call_args.kwargs["params"], write_thread
            )
            await storage.restore_from_snapshot(("team",), "key-1")
            self.assertEqual(
                storage.client.post.call_args.kwargs["params"], write_thread
            )
        finally:
            await storage.client.aclose()

    async def test_snapshot_and_restore_use_same_namespace_thread(self):
        storage = NullDriftLangGraphStore()
        try:
            storage.client.post = AsyncMock(return_value=Mock())
            await storage.take_snapshot(("team", "agent"))
            first = storage.client.post.call_args.kwargs["params"]
            await storage.restore_from_snapshot(("team", "agent"))
            second = storage.client.post.call_args.kwargs["params"]
            self.assertEqual(first, second)
            self.assertEqual(first, {"thread_id": encode_namespace(("team", "agent"))})
        finally:
            await storage.client.aclose()

    async def test_put_rejects_non_dictionary_value(self):
        storage = NullDriftLangGraphStore()
        try:
            storage.client.post = AsyncMock()
            with self.assertRaises(TypeError):
                await storage.aput(("team",), "key-1", ["not a dict"])
            storage.client.post.assert_not_awaited()
        finally:
            await storage.client.aclose()

    async def test_get_ignores_non_object_recall_payload(self):
        storage = NullDriftLangGraphStore()
        try:
            storage.client.get = AsyncMock(
                return_value=Mock(json=lambda: {"recovered_text": '["unexpected"]'})
            )
            self.assertIsNone(await storage.aget(("team",), "key-1"))
        finally:
            await storage.client.aclose()

    async def test_get_ignores_mismatched_key(self):
        storage = NullDriftLangGraphStore()
        try:
            recovered = '{"key": "other", "value": {"x": 1}}'
            response = Mock(json=lambda: {"recovered_text": recovered})
            storage.client.get = AsyncMock(return_value=response)
            self.assertIsNone(await storage.aget(("team",), "wanted"))
            self.assertEqual(
                storage.client.get.call_args.kwargs["params"],
                {"thread_id": encode_namespace(("team",), "wanted")},
            )
        finally:
            await storage.client.aclose()


if __name__ == "__main__":
    unittest.main()
