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

    def batch(self, ops):
        results = []
        for op in ops:
            if isinstance(op, GetOp):
                thread_id = encode_namespace(op.namespace, op.key)
                response = self.client.get(
                    self.gateway_url + "/recall", params={"thread_id": thread_id}
                )
                response.raise_for_status()
                text = response.json().get("recovered_text")
                if not text:
                    results.append(None)
                    continue
                record = json.loads(text)
                if not isinstance(record, dict) or record.get("key") != op.key:
                    results.append(None)
                    continue
                value = record.get("value")
                if not isinstance(value, dict):
                    results.append(None)
                    continue
                now = datetime.now(timezone.utc)
                results.append(
                    Item(
                        namespace=op.namespace,
                        key=op.key,
                        value=value,
                        created_at=now,
                        updated_at=now,
                    )
                )
            elif isinstance(op, PutOp):
                if op.value is None:
                    raise NotImplementedError(
                        "Gateway does not expose keyed deletion"
                    )
                if not isinstance(op.value, dict):
                    raise TypeError("value must be a dictionary")
                if op.ttl is not None and type(op.ttl).__name__ != "NotProvided":
                    raise NotImplementedError("Gateway does not support TTL")
                thread_id = encode_namespace(op.namespace, op.key)
                response = self.client.post(
                    self.gateway_url + "/inject",
                    params={"thread_id": thread_id},
                    json={
                        "text": json.dumps({"key": op.key, "value": op.value}),
                        "salience": 1.0,
                    },
                )
                response.raise_for_status()
                results.append(None)
            else:
                raise NotImplementedError(
                    "Gateway has no authoritative namespace enumeration or "
                    "keyed multi-record search"
                )
        return results

    async def abatch(self, ops):
        return await asyncio.to_thread(self.batch, list(ops))
