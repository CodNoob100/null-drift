# Database-free framework memory: research and native design

## Constraint

No SQLite, SQL engine, document database, vector database, or separate
traditional database service. Use null-drift's existing Rust HRSA/AMN and
postcard `.nd` snapshot lifecycle. This proposal is not a claim that an
approximate attractor is a lossless dictionary.

## Literature

- Key-value memory in the brain (Neuron, 2025),
  https://doi.org/10.1016/j.neuron.2025.02.029:
  distinct retrieval keys and content values enable discriminability
  without conflating exact identity with associative similarity.
- HeLa-Mem (ACL 2026), https://aclanthology.org/2026.acl-long.625/:
  association, consolidation, and spreading activation; useful for
  semantic navigation, not proof of exact deletion.
- RippleMem (arXiv 2608.13334, August 2026):
  cue-rich episodic anchors and associative expansion.
- Autonomous retrieval for continuous learning in associative memory
  networks (2025), https://pmc.ncbi.nlm.nih.gov/articles/PMC12418250/:
  autonomous rehearsal and consolidation under local plasticity.
- LangGraph BaseStore contract:
  https://reference.langchain.com/python/langgraph.store/base/BaseStore

## Proposed native architecture

1. **Identity channel.** Canonicalize a tuple namespace and key into a
   domain-separated identity digest. Never use similarity scores to decide
   whether two keys are equal. Reject invalid/ambiguous inputs.
2. **Associative channel.** Inject value-derived hypervectors into the
   existing AMN/HRSA memory. Use cues and activation for *discovery*,
   relevance ranking, and pattern completion, never as an exact-key oracle.
3. **Native lifecycle ledger.** Extend the existing versioned postcard
   thread snapshot with a bounded collection of identity records, including
   version, timestamps, tombstone flag, and a stable reference to memory
   content. This is a native memory metadata structure, not SQL or a
   separate database. It must have explicit capacity, eviction, and
   durability guarantees. Avoid a hidden infinite hashmap that recreates
   a database by another name.
4. **Deletion.** Tombstone identity first and make recall respect it;
   separately handle AMN removal/compaction. A tombstone does not guarantee
   physical erasure of earlier snapshots; secure deletion needs a policy.
5. **Enumeration.** Namespace search/listing must traverse the native
   identity ledger, not guess keys from dominant-state recall.
6. **Durability.** Snapshot atomicity is already implemented using a
   temporary file, sync, and rename. Add versioned migrations, recovery
   tests, and explicit write acknowledgment semantics. Current inject
   acknowledges before a snapshot: it is not crash-durable.
7. **Framework boundary.** LangGraph `batch`/`abatch` translate to
   native keyed endpoints. No silent success for unsupported operations.
   CrewAI's actual installed storage interface must be checked separately.

## Acceptance criteria

- Two keys in the same namespace survive interleaved writes and overwrite.
- Delete one key without altering the other; namespace pagination stable.
- Restart after explicit snapshot restores exact identities and metadata.
- Crash before snapshot is documented as potentially lossy, or use a
  native append-only event journal with checksums and replay.
- Capacity/eviction and associative false-positive rates are measured.
- Multi-tenant isolation and malicious key validation are tested.
- No SQL/SQLite/third-party DB dependencies introduced.

## Status

Research/design only. Native ledger, deletion, namespace APIs, and durability
tests remain unimplemented; do not count this document as contract completion.
