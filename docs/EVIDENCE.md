# Evidence and claim boundaries

This document records which `null-drift` statements are verifiable from source code or checked-in artifacts, and where further independent testing is required. Evidence reviewed for **v0.3.0**, October 21, 2026.

| Claim | Status | What actually supports it / caveat |
| --- | --- | --- |
| A Rust gateway embeds text using AllMiniLML6V2 | **Implemented** | [`gateway-rs`](../crates/gateway-rs/src/main.rs); [model card](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2) documents 384 output dimensions. |
| 10,000D weighted, permuted state | **Implemented** | [`hrsa.rs`](../crates/null-drift-core/src/hrsa.rs), [`spl.rs`](../crates/null-drift-core/src/spl.rs). This state is lossy: representation width alone does not prove long-term retrieval quality. |
| Associative anchor cleanup uses Hamming distance | **Implemented** | [`amn.rs`](../crates/null-drift-core/src/amn.rs), [`nulld`](../crates/nulld/src/main.rs). Not cosine similarity. |
| Per-thread storage has O(1) RAM across arbitrarily many events | **Not established; false for this implementation** | `AttractorIndex` appends on high salience. [`nulld`](../crates/nulld/src/main.rs) now bounds per-dimension projector creation (maximum 4096 input dimensions; maximum 64 million cached `f32` matrix entries); this **does not** bound attractors or total process memory. Cache capacity counts thread entries; see [Moka docs](https://docs.rs/moka/latest/moka/future/struct.Cache.html). |
| Infinite, lossless episodic memory / perfect recall | **Not established** | The projection compresses and superposes events. [`needle_test.py`](../tests/advanced/needle_test.py) is one scripted scenario, not a formal or general guarantee. |
| Token cost savings | **Simulation only** | [`token_benchmark.py`](../scripts/token_benchmark.py) assumes fixed 700-token context vs accumulated synthetic history; no production billing data. |
| 43.75 ms mean inject, 20.12 ms mean recall | **Archived repository results only** | [`benchmark_results.txt`](benchmarks/benchmark_results.txt), with [`benchmark.py`](../scripts/benchmark.py); hardware/commit and reproducibility metadata are insufficient for independent comparisons. |
| Gateway health reflects daemon availability | **Implemented** | [`gateway-rs`](../crates/gateway-rs/src/main.rs) probes daemon `/health`; does not prove inference quality or permanent readiness. |
| Multi-tenant security | **Isolation by ID, not authorization** | [`nulld`](../crates/nulld/src/main.rs) selects state using user-provided `thread_id`; no auth middleware is installed. Deployment must supply access controls. |
| State snapshots use Postcard | **Implemented** | [`nulld`](../crates/nulld/src/main.rs), [Postcard docs](https://docs.rs/postcard/latest/postcard/). Serialization format does not by itself guarantee safe size bounds, integrity, atomicity, or hostile-input resistance. |
| Strict 64 KiB limit blocks all memory DoS | **Not established** | Daemon uses `DefaultBodyLimit::max(64 * 1024)` on request extractors, not a global memory quota; see [Axum docs](https://docs.rs/axum/latest/axum/extract/struct.DefaultBodyLimit.html). |
| Security CI blocks vulnerable dependencies and secrets | **Not currently enforced** | [Scanner workflow](../.github/workflows/security-scanners.yml) marks scans as non-blocking; success is not equivalent to zero findings. |
| Standard CI checks pass | **Observed on main at review** | [GitHub workflow runs](https://github.com/CodNoob100/null-drift/actions/workflows/compliance.yml), but these do not include end-to-end Docker tests by default. |

## Research background (not independent validation)

- [Pentti Kanerva (2009), *Hyperdimensional Computing*](https://doi.org/10.1007/s12559-009-9009-8) — distributed representations using high-dimensional random vectors.
- [Tony Plate (1995), *Holographic Reduced Representations*](https://doi.org/10.1109/72.377968) — compositional distributed representations and cleanup memories.
- [All-MiniLM-L6-v2 model card](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2) — 384-dimensional sentence embeddings.
- [Moka Cache documentation](https://docs.rs/moka/latest/moka/future/struct.Cache.html) — expiry and entry-count/weight policy.
- [Tokio RwLock documentation](https://docs.rs/tokio/latest/tokio/sync/struct.RwLock.html) — asynchronous reader/writer synchronization, not a lock-free algorithm.
- [Postcard documentation](https://docs.rs/postcard/latest/postcard/) — serialization format and implementation constraints.

## Evidence required before stronger claims

Record benchmark environment, CPU, RAM, OS, exact commit and dependencies; at least repeated runs and error bars; a measured memory growth curve for high-salience anchors; realistic query-specific recall metrics against baseline methods; true token consumption and dollar billing measured on a named model; adversarial state and authorization testing; an end-to-end cloud integration workflow. Publish actual results and failure cases, rather than extrapolating from one chart or a synthetic token scenario.
