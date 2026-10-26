"""Legacy filename: database-free LangGraph gateway adapter.

This module uses only null-drift gateway endpoints. It deliberately rejects
operations the gateway cannot implement faithfully. No SQL or local DB.
"""

import asyncio
import json
from datetime import datetime, timezone

import httpx
from langgraph.store.base import BaseStore, GetOp, Item, PutOp

from nulldrift_agents import encode_namespace


class NullDriftGatewayStore(BaseStore):
    """Conservative LangGraph BaseStore adapter for keyed gateway threads.

    Each (namespace, key) is mapped to a separate gateway thread.
    The gateway's dominant-state recall is not a multi-record index.
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
            else:
                raise NotImplementedError("Unsupported LangGraph operation")
        return results

    async def abatch(self, ops):
        return await asyncio.to_thread(self.batch, list(ops))
