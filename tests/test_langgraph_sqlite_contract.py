"""Actual LangGraph operation types against the null-drift gateway boundary."""

import asyncio
import json
import unittest
from unittest.mock import Mock

try:
    from langgraph.store.base import (
        BaseStore,
        GetOp,
        ListNamespacesOp,
        MatchCondition,
        PutOp,
        SearchOp,
    )
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

    def test_namespace_search_returns_real_items(self):
        client = Mock()
        client.post.return_value.json.return_value = {
            "records": [
                {
                    "namespace": ["tenant", "agent"],
                    "key": "first",
                    "value": json.dumps({"v": 7}),
                    "revision": 1,
                }
            ]
        }
        store = NullDriftGatewayStore(client=client)
        items = store.search(("tenant",), limit=10, offset=0)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].value, {"v": 7})
        self.assertEqual(client.post.call_args.kwargs["json"]["operation"], "search")

    def test_list_namespaces(self):
        client = Mock()
        client.post.return_value.json.return_value = {
            "namespaces": [["tenant", "agent"], ["tenant", "other"]]
        }
        store = NullDriftGatewayStore(client=client)
        result = store.batch([ListNamespacesOp(match_conditions=())])[0]
        self.assertEqual(result, [("tenant", "agent"), ("tenant", "other")])
        self.assertEqual(
            client.post.call_args.kwargs["json"]["operation"], "namespaces"
        )

    def test_namespace_prefix_suffix_wildcards_depth_and_pagination(self):
        client = Mock()
        client.post.return_value.json.return_value = {
            "namespaces": [
                ["tenant", "alpha", "draft"],
                ["tenant", "beta", "draft"],
                ["tenant", "beta", "published"],
                ["other", "beta", "draft"],
                ["tenant", "alpha", "draft", "deep"],
            ]
        }
        store = NullDriftGatewayStore(client=client)
        result = store.list_namespaces(
            prefix=("tenant", "*"),
            suffix=("draft",),
            limit=10,
        )
        self.assertEqual(
            result, [("tenant", "alpha", "draft"), ("tenant", "beta", "draft")]
        )
        result = store.list_namespaces(
            prefix=("tenant",), max_depth=2, limit=1, offset=1
        )
        self.assertEqual(result, [("tenant", "beta")])
        self.assertEqual(
            client.post.call_args.kwargs["json"]["operation"], "namespaces"
        )

    def test_namespace_invalid_pagination_fails_closed(self):
        store = NullDriftGatewayStore(client=Mock())
        with self.assertRaises(ValueError):
            store.batch([ListNamespacesOp(offset=-1)])
        with self.assertRaises(ValueError):
            store.batch(
                [
                    ListNamespacesOp(
                        match_conditions=(
                            MatchCondition(match_type="prefix", path=("tenant",)),
                        ),
                        max_depth=-1,
                    )
                ]
            )

    def test_unsupported_operations_are_not_silent(self):
        store = NullDriftGatewayStore(client=Mock())
        with self.assertRaises(NotImplementedError):
            store.batch([SearchOp(("tenant",), query="semantic")])
        store.batch([PutOp(("tenant",), "key", None)])


if __name__ == "__main__":
    unittest.main()
