"""Tests against the installed real LangGraph BaseStore protocol."""

import asyncio
import tempfile
import unittest
from pathlib import Path

try:
    from langgraph.store.base import BaseStore, GetOp, ListNamespacesOp, PutOp, SearchOp
    from nulldrift_langgraph_sqlite import NullDriftSQLiteStore
except ImportError:
    BaseStore = None


@unittest.skipIf(BaseStore is None, "langgraph-checkpoint is not installed")
class RealLangGraphStoreTests(unittest.TestCase):
    def test_multi_key_overwrite_delete_and_restart(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "memories.db"
            store = NullDriftSQLiteStore(path)
            self.assertIsInstance(store, BaseStore)
            store.put(("tenant", "agent"), "first", {"v": 1})
            store.put(("tenant", "agent"), "second", {"v": 2})
            store.put(("tenant", "other"), "first", {"v": 3})
            store.put(("tenant", "agent"), "first", {"v": 4})
            reopened = NullDriftSQLiteStore(path)
            self.assertEqual(reopened.get(("tenant", "agent"), "first").value, {"v": 4})
            self.assertEqual(reopened.get(("tenant", "agent"), "second").value, {"v": 2})
            self.assertEqual(reopened.get(("tenant", "other"), "first").value, {"v": 3})
            reopened.delete(("tenant", "agent"), "first")
            self.assertIsNone(reopened.get(("tenant", "agent"), "first"))
            self.assertEqual(reopened.get(("tenant", "agent"), "second").value, {"v": 2})

    def test_batch_search_namespace_and_async(self):
        with tempfile.TemporaryDirectory() as directory:
            store = NullDriftSQLiteStore(Path(directory) / "store.db")
            result = store.batch(
                [
                    PutOp(("tenant", "a"), "one", {"kind": "note"}),
                    PutOp(("tenant", "b"), "two", {"kind": "other"}),
                    GetOp(("tenant", "a"), "one"),
                    SearchOp(("tenant",), filter={"kind": "note"}),
                    ListNamespacesOp(),
                ]
            )
            self.assertIsNone(result[0])
            self.assertIsNone(result[1])
            self.assertEqual(result[2].value, {"kind": "note"})
            self.assertEqual([item.key for item in result[3]], ["one"])
            self.assertEqual(result[4], [("tenant", "a"), ("tenant", "b")])
            async_result = asyncio.run(
                store.abatch([GetOp(("tenant", "b"), "two")])
            )
            self.assertEqual(async_result[0].value, {"kind": "other"})

    def test_unsupported_semantic_query_fails_explicitly(self):
        with tempfile.TemporaryDirectory() as directory:
            store = NullDriftSQLiteStore(Path(directory) / "store.db")
            with self.assertRaises(NotImplementedError):
                store.batch([SearchOp(("tenant",), query="similar text")])


if __name__ == "__main__":
    unittest.main()
