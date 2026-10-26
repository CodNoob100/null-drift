"""Durable LangGraph BaseStore implementation backed by SQLite.

Requires langgraph-checkpoint (which provides langgraph.store.base).
Unlike the gateway's dominant recall, this store preserves multiple keys.
Semantic/vector search and TTL are intentionally unsupported.
"""

import asyncio
import json
import sqlite3
from datetime import datetime, timezone

from langgraph.store.base import (
    BaseStore,
    GetOp,
    Item,
    ListNamespacesOp,
    PutOp,
    SearchItem,
    SearchOp,
)


class NullDriftSQLiteStore(BaseStore):
    """Real LangGraph storage contract with an authoritative keyed index."""

    def __init__(self, path):
        super().__init__()
        self.path = str(path)
        with self._connect() as db:
            db.execute(
                "CREATE TABLE IF NOT EXISTS memories ("
                "namespace TEXT NOT NULL, key TEXT NOT NULL, value TEXT NOT NULL, "
                "created_at TEXT NOT NULL, updated_at TEXT NOT NULL, "
                "PRIMARY KEY(namespace, key))"
            )

    def _connect(self):
        return sqlite3.connect(self.path, timeout=10)

    @staticmethod
    def _namespace(value):
        if not isinstance(value, tuple) or any(
            not isinstance(part, str) or not part for part in value
        ):
            raise ValueError("namespace must be a tuple of nonempty strings")
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"))

    @staticmethod
    def _item(row, search=False):
        cls = SearchItem if search else Item
        return cls(
            namespace=tuple(json.loads(row[0])),
            key=row[1],
            value=json.loads(row[2]),
            created_at=datetime.fromisoformat(row[3]),
            updated_at=datetime.fromisoformat(row[4]),
        )

    def batch(self, ops):
        results = []
        with self._connect() as db:
            for op in ops:
                if isinstance(op, GetOp):
                    ns = self._namespace(op.namespace)
                    row = db.execute(
                        "SELECT namespace,key,value,created_at,updated_at "
                        "FROM memories WHERE namespace=? AND key=?",
                        (ns, op.key),
                    ).fetchone()
                    results.append(self._item(row) if row else None)
                elif isinstance(op, PutOp):
                    ns = self._namespace(op.namespace)
                    if op.ttl not in (None,) and type(op.ttl).__name__ != "NotProvided":
                        raise NotImplementedError("TTL is not supported")
                    if op.value is None:
                        db.execute(
                            "DELETE FROM memories WHERE namespace=? AND key=?",
                            (ns, op.key),
                        )
                    else:
                        if not isinstance(op.value, dict):
                            raise TypeError("value must be a dictionary")
                        now = datetime.now(timezone.utc).isoformat()
                        db.execute(
                            "INSERT INTO memories VALUES (?,?,?,?,?) "
                            "ON CONFLICT(namespace,key) DO UPDATE SET "
                            "value=excluded.value,updated_at=excluded.updated_at",
                            (ns, op.key, json.dumps(op.value), now, now),
                        )
                    results.append(None)
                elif isinstance(op, SearchOp):
                    if op.query is not None:
                        raise NotImplementedError("semantic search is not supported")
                    rows = db.execute(
                        "SELECT namespace,key,value,created_at,updated_at "
                        "FROM memories ORDER BY namespace,key"
                    ).fetchall()
                    matches = []
                    for row in rows:
                        namespace = tuple(json.loads(row[0]))
                        value = json.loads(row[2])
                        if namespace[: len(op.namespace_prefix)] != op.namespace_prefix:
                            continue
                        if op.filter and any(value.get(k) != v for k, v in op.filter.items()):
                            continue
                        matches.append(self._item(row, search=True))
                    results.append(matches[op.offset : op.offset + op.limit])
                elif isinstance(op, ListNamespacesOp):
                    rows = db.execute("SELECT DISTINCT namespace FROM memories").fetchall()
                    namespaces = set()
                    for (encoded,) in rows:
                        namespace = tuple(json.loads(encoded))
                        if op.match_conditions:
                            matched = True
                            for condition in op.match_conditions:
                                path = condition.path
                                if condition.match_type == "prefix":
                                    target = namespace[: len(path)]
                                elif condition.match_type == "suffix":
                                    target = namespace[-len(path) :]
                                else:
                                    raise ValueError("unknown match condition")
                                if len(target) != len(path) or any(
                                    p != "*" and p != v for p, v in zip(path, target)
                                ):
                                    matched = False
                                    break
                            if not matched:
                                continue
                        if op.max_depth is not None:
                            namespace = namespace[: op.max_depth]
                        namespaces.add(namespace)
                    ordered = sorted(namespaces)
                    results.append(ordered[op.offset : op.offset + op.limit])
                else:
                    raise TypeError("unsupported LangGraph store operation")
        return results

    async def abatch(self, ops):
        return await asyncio.to_thread(self.batch, list(ops))
