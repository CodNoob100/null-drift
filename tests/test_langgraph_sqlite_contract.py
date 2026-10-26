"""Actual LangGraph operation types against the null-drift gateway boundary."""

import asyncio
import json
import unittest
from unittest.mock import Mock

try:
    from langgraph.store.base import BaseStore, GetOp, PutOp, SearchOp
    from nulldrift_langgraph_sqlite import NullDriftGatewayStore
except ImportError:
    BaseStore = None


@unittest.skipIf(BaseStore is None, "langgraph-checkpoint is not installed")
class RealLangGraphGatewayTests(unittest.TestCase):
    def test_keyed_put_get_use_identical_thread(self):
        client = Mock()
        client.post.return_value.json.return_value = {
            "record": {"key": "first", "value": json.dumps({"v": 1})}
        }
        store = NullDriftGatewayStore(client=client)
        self.assertIsInstance(store, BaseStore)
        store.put(("tenant", "agent"), "first", {"v": 1})
        self.assertEqual(store.get(("tenant", "agent"), "first").value, {"v": 1})
        self.assertEqual(
            client.post.call_args.kwargs["json"]["namespace"],
            ["tenant", "agent"],
        )

    def test_missing_record_and_async_batch(self):
        client = Mock()
        client.post.return_value.json.return_value = {}
        store = NullDriftGatewayStore(client=client)
        self.assertIsNone(store.get(("tenant",), "missing"))
        self.assertEqual(
            asyncio.run(store.abatch([GetOp(("tenant",), "missing")])),
            [None],
        )

    def test_unsupported_operations_are_not_silent(self):
        store = NullDriftGatewayStore(client=Mock())
        with self.assertRaises(NotImplementedError):
            store.batch([SearchOp(("tenant",))])
        store.batch([PutOp(("tenant",), "key", None)])


if __name__ == "__main__":
    unittest.main()
