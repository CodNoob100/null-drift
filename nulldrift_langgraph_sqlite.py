"""Legacy filename: database-free LangGraph gateway adapter.

This module uses only null-drift gateway endpoints. It deliberately rejects
operations the gateway cannot implement faithfully. No SQL or local DB.
"""

import asyncio
import json
from datetime import datetime, timezone

import httpx
from langgraph.store.base import (
    BaseStore,
    GetOp,
    Item,
    ListNamespacesOp,
    PutOp,
    SearchOp,
)


def _namespace_matches(namespace, condition):
    """Match one LangGraph prefix/suffix condition, including '*' labels."""
    pattern = condition.path
    if len(pattern) > len(namespace):
        return False
    if condition.match_type == "prefix":
        labels = namespace[: len(pattern)]
    elif condition.match_type == "suffix":
        labels = namespace[len(namespace) - len(pattern) :]
    else:
        raise ValueError(f"Unknown namespace match type: {condition.match_type}")
    return all(
        wanted == "*" or wanted == actual for wanted, actual in zip(pattern, labels)
    )


class NullDriftGatewayStore(BaseStore):
    """LangGraph BaseStore adapter backed by the daemon's exact-key ledger.

    Namespace/key operations use native postcard-backed records, not the
    daemon's separate approximate HRSA/AMN recall mechanism.
    """

    def __init__(self, gateway_url="http://127.0.0.1:8000", client=None):
        super().__init__()
        self.gateway_url = gateway_url.rstrip("/")
        self.client = client or httpx.Client(timeout=5.0)

    def close(self):
        self.client.close()

    def _memory(self, operation, namespace, **kwargs):
        response = self.client.post(
            self.gateway_url + "/memory",
            json={"operation": operation, "namespace": list(namespace), **kwargs},
        )
        response.raise_for_status()
        return response.json()

    def batch(self, ops):
        results = []
        for op in ops:
            if isinstance(op, GetOp):
                record = self._memory("get", op.namespace, key=op.key).get("record")
                if record is None:
                    results.append(None)
                    continue
                now = datetime.now(timezone.utc)
                results.append(
                    Item(
                        namespace=op.namespace,
                        key=op.key,
                        value=json.loads(record["value"]),
                        created_at=now,
                        updated_at=now,
                    )
                )
            elif isinstance(op, PutOp):
                if op.ttl is not None and type(op.ttl).__name__ != "NotProvided":
                    raise NotImplementedError("TTL is not supported")
                if op.value is None:
                    self._memory("delete", op.namespace, key=op.key)
                else:
                    self._memory("put", op.namespace, key=op.key, value=op.value)
                results.append(None)
            elif isinstance(op, SearchOp):
                if op.query is not None or op.filter is not None:
                    raise NotImplementedError(
                        "Semantic search and filters are not supported"
                    )
                payload = self._memory(
                    "search",
                    op.namespace_prefix,
                    offset=op.offset,
                    limit=op.limit,
                )
                now = datetime.now(timezone.utc)
                results.append(
                    [
                        Item(
                            namespace=tuple(record["namespace"]),
                            key=record["key"],
                            value=json.loads(record["value"]),
                            created_at=now,
                            updated_at=now,
                        )
                        for record in payload["records"]
                    ]
                )
            elif isinstance(op, ListNamespacesOp):
                if op.offset < 0 or op.limit < 0:
                    raise ValueError("Namespace pagination must be nonnegative")
                if op.max_depth is not None and op.max_depth < 0:
                    raise ValueError("Namespace max_depth must be nonnegative")
                conditions = op.match_conditions or ()
                payload = self._memory("namespaces", ())
                namespaces = [
                    tuple(namespace)
                    for namespace in payload["namespaces"]
                    if all(
                        _namespace_matches(namespace, condition)
                        for condition in conditions
                    )
                ]
                if op.max_depth is not None:
                    namespaces = [
                        namespace[: op.max_depth] for namespace in namespaces
                    ]
                namespaces = sorted(set(namespaces))
                results.append(namespaces[op.offset : op.offset + op.limit])
            else:
                raise NotImplementedError("Unsupported LangGraph operation")
        return results

    async def abatch(self, ops):
        return await asyncio.to_thread(self.batch, list(ops))
