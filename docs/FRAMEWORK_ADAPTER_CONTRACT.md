# Framework adapter compatibility contract

The classes in `nulldrift_agents.py` are **HTTP convenience wrappers**, not
verified implementations of the upstream framework storage interfaces. Their
local `StorageBackend` and `BaseStore` declarations are empty placeholders.
Do not advertise them as drop-in integrations until the contracts below pass.

## LangGraph (issue #183)

The upstream `langgraph.store.base.BaseStore` supports `batch` and `abatch`
operations and keyed `get`/`put`/`delete`, namespace listing, and
prefix-scoped search. `get` returns an `Item` with metadata, not a bare
dictionary. The present `NullDriftLangGraphStore.aget` returns a dictionary,
and `aput` stores a single `{"key": ..., "value": ...}` payload under
a deterministic SHA-256-derived thread ID for the namespace and key. This
separates namespace-only and keyed identities and bounds identifier length.

Snapshot and restore accept an optional key: supply the same namespace and key
used for `aput` to target that specific thread. Omitting the key targets the
namespace-only thread, **not** all keys in that namespace. Cross-restart
persistence remains unverified.

The legacy gateway's dominant-state `/recall` is not a durable multi-key
index. Draft PR #188 adds a separate bounded native `IdentityLedger`,
a daemon `/memory` endpoint and a gateway `/memory` proxy. The optional
`NullDriftGatewayStore` in `nulldrift_langgraph_sqlite.py` (legacy filename,
no SQL dependency) implements real LangGraph `BaseStore` `batch`/`abatch`
operations against the exact-key API. Approximate recall must never
substitute for exact namespace/key lookup.

Required acceptance tests, with the real installed LangGraph dependency:

1. Construct the concrete `BaseStore` subclass and exercise `batch` and
   `abatch` with `GetOp`, `PutOp`, `SearchOp`, and `ListNamespacesOp`.
2. Write two keys to the same namespace, read both back, overwrite one,
   delete one, and verify the other survives.
3. Verify namespace prefix searches, list/filter/pagination semantics,
   and collision-free encoding for tuple boundaries.
4. Check return types (`Item`, search results, and operation-order alignment)
   and both sync and async graph usage.
5. Test network errors and restart/persistence behavior without swallowing
   failures that should reach the caller.

References:
- https://reference.langchain.com/python/langgraph.store/base/BaseStore
- https://github.com/langchain-ai/docs/blob/main/src/oss/langgraph/stores.mdx

## CrewAI (issue #184)

Current CrewAI memory documents a custom `StorageBackend` protocol in
`crewai.memory.storage.backend` that is supplied to `Memory(storage=...)`.
Do not assume the current wrapper's `save(payload)` and `search(query)`
methods match the protocol. Inspect the exact installed CrewAI version's
protocol and data models, implement every required method, and test the
actual `Memory` integration with the real package. Scope, record identity,
metadata, search, deletion, and reset must be supported or explicitly
rejected; a single dominant recalled payload is not an equivalent record
store. Preserve tenant isolation and fail visibly on unsupported operations.

Reference:
- https://github.com/crewAIInc/crewAI/blob/main/docs/v1.12.1/en/concepts/memory.mdx

## Test tiers

- **Offline wrapper tests:** mock the gateway HTTP boundary; no framework
  compatibility claim. See `tests/test_agent_wrapper_contracts.py`.
- **Framework contract tests:** install pinned framework versions, exercise
  their real storage interfaces, and assert full key/namespace semantics.
- **Gateway integration tests:** exercise real gateway requests, snapshot and
  restore, and persistence across restart with isolated thread IDs.

Keep tests deterministic and never fabricate benchmark or compatibility
results. No production deployment or migration should depend on the wrappers
until the contract tests are green.


## Database-free implementation status

**Draft PR #188 implementation (not merged/released):** the daemon has a
bounded native `IdentityLedger` with exact put/get/delete, prefix search,
namespace enumeration and postcard `framework_memory.nd` persistence.
The gateway forwards `/memory` requests and daemon HTTP errors.
`NullDriftGatewayStore` uses this endpoint, not `/inject`/`/recall`,
and passed seven tests with the installed real LangGraph `BaseStore`
package and a mocked HTTP boundary. The Rust daemon passed 23 tests
(including staged-write rollback, snapshot reload and concurrent tenant
writes); a gateway proxy test also passed at head `e1b9ec1` in
2026-10-28 GitHub Actions.

**Still unverified:** real daemon + gateway + LangGraph end-to-end
process/restart integration, OS/power-loss durability, authentication,
and official CrewAI `StorageBackend` compatibility. Semantic search,
filters and TTL remain unsupported and fail explicitly. `Item` timestamps
are synthesized at read time, not persisted provenance. The snapshot
writer does not sync the parent directory after rename. The separate
`nulldrift_agents.py` wrappers remain convenience APIs. No SQL or
external database is introduced.

See `docs/DB_FREE_FRAMEWORK_MEMORY_RESEARCH.md` for the literature-backed
native AMN/HRSA design and acceptance criteria.
