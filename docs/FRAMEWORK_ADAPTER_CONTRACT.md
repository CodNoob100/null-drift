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

The gateway's dominant-state recall is not a durable multi-key index. An
upstream-compatible adapter must use a separate authoritative keyed backend
(or a new, explicitly supported gateway API) and retain namespace isolation.
Do not silently claim that recall preserves every previously written key.

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
