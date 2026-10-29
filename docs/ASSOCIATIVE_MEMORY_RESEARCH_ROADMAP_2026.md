# Evidence-led associative memory expansion plan (2026-10-26)

## Non-negotiable architecture
Use Rust-native bounded associative structures and postcard .nd snapshots. Do not introduce SQLite, SQL, relational databases, or external database services. Exact namespace/key identity must remain distinct from approximate AMN/HRSA retrieval. Preserve backward compatibility with existing thread snapshots.

## Research translated into testable engineering

| Source | Mechanism | Candidate experiment | Gate |
|---|---|---|---|
| Key-value memory in the brain (Neuron 2025) | Discriminative retrieval keys versus high-fidelity values | Measure exact-key fidelity under semantic collisions; never substitute approximate recall for exact reads | 100% exact-key accuracy in synthetic collision tests |
| HeLa-Mem (ACL 2026) | Episodic graph, co-activation, semantic consolidation | Bounded in-memory co-occurrence edges, weighted traversal, periodic distillation into separate summaries | Improve multi-hop retrieval without losing original events |
| RippleMem (Aug 2026 preprint) | Multiple hybrid cues and event-centric associative expansion | Combine namespace, lexical, temporal and AMN cues; bounded expansion from anchors | Higher multi-evidence recall than isolated nearest-neighbor |
| Autonomous retrieval (2025) | Inhibitory plasticity and rehearsal of stored attractors | Offline rehearsal simulation with visitation penalties, bounded iteration and replay audit | Reduce forgetting while preventing false-memory proliferation |
| Synapse (ACL 2026) | Spreading activation, lateral inhibition, temporal decay | Ablate activation, inhibition and decay independently | Higher temporal multi-hop accuracy with bounded latency |
| AnchorMem (ACL 2026) | Fact anchors plus intact event context | Link exact facts to immutable episode references; retrieve source context with each answer | Improve provenance and reduce unsupported reconstructions |

## Prioritized implementation tracks

### P0: Correctness and baseline
- Compile daemon and gateway; pass rustfmt, Black and actual LangGraph operation tests.
- Exercise gateway -> daemon put/get/delete/search/list, restart recovery, invalid input, concurrent writes, and snapshot corruption.
- Preserve JSON value roundtrips and atomic persistence before acknowledging mutations.
- Record baseline exact-match accuracy, retrieval recall@k, p95 latency, bytes per memory and restart fidelity.

### P1: Bounded associative expansion
- Add a bounded, versioned native episode-edge structure keyed by exact ledger identities.
- Support explicit provenance, co-activation counts, edge aging and deterministic traversal; no uncontrolled graph growth.
- Hybrid seed selection from exact identity, lexical cues, time and optional HRSA/AMN similarity.
- Bounded spreading activation with inhibition and deduplication; always return source IDs and evidence paths.

### P2: Consolidation and continual learning
- Implement opt-in rehearsal with per-run visit penalties and strict compute budgets.
- Generate derived semantic summaries separately from raw episodic evidence; preserve original records.
- Add versioned postcard migration tests and crash-safe checkpoint behavior.

### P3: Evaluation and safe rollout
- Benchmark LoCoMo and LongMemEval-S where dataset and license permit; also synthetic multi-hop, interference and adversarial cues.
- Compare exact-only, vector-only, hybrid, hybrid+graph, graph+consolidation, and rehearsal ablations.
- Report improvements and regressions with measured values, not claimed paper results.
- Keep advanced retrieval feature-flagged until accuracy, provenance, memory and latency gates pass.

## Verified status (2026-10-29 maintenance review)
Research synthesis remains design work, not paper replication.
Draft PR #188 at `e1b9ec1` passed four exact-head workflows on
2026-10-28: native Rust (23 daemon tests and one gateway proxy test),
seven real-package LangGraph contract tests using mocked HTTP,
compliance and advisory security scanning. The native ledger is wired
to daemon/gateway with staged postcard writes and reload/rollback tests.
Real end-to-end process restart, directory-sync/power-loss durability,
authentication and measured benchmark ablations remain open.
HeLa-Mem graph, RippleMem multi-cue, Synapse inhibition, AnchorMem
provenance and autonomous rehearsal are proposed, **not implemented**.
Do not promote them without code, tests and ablation evidence.

## References
- https://www.sciencedirect.com/science/article/pii/S0896627325001722
- https://aclanthology.org/2026.acl-long.625/
- https://arxiv.org/abs/2608.13334
- https://pmc.ncbi.nlm.nih.gov/articles/PMC12418250/
- https://aclanthology.org/2026.findings-acl.1108/
- https://aclanthology.org/2026.findings-acl.1736/
