# null-drift

**Experimental, self-hosted memory-state service for AI agents.** The repository combines a Rust HTTP gateway, a Rust state daemon, and Python client adapters. It explores fixed-width hyperdimensional representations with salience-weighted updates and anchor matching; it does **not** provide infinite lossless memory, proven cost savings, or a production security boundary.

[![CI](https://github.com/CodNoob100/null-drift/actions/workflows/compliance.yml/badge.svg)](https://github.com/CodNoob100/null-drift/actions/workflows/compliance.yml) [![License: AGPL-3.0](https://img.shields.io/badge/license-AGPL--3.0-blue.svg)](LICENSE) [![Contributions welcome](https://img.shields.io/badge/contributions-welcome-blue.svg)](CONTRIBUTING.md)

## What is implemented?

| Component | Role | Source |
| --- | --- | --- |
| `gateway-rs` | Axum HTTP service; embeds incoming text with FastEmbed `AllMiniLML6V2` and forwards to the daemon | [`crates/gateway-rs/src/main.rs`](crates/gateway-rs/src/main.rs) |
| `nulld` | Per-thread 10,000-dimensional HRSA state, attractor matching, `/inject`, `/recall`, snapshot/restore, health checks | [`crates/nulld/src/main.rs`](crates/nulld/src/main.rs) |
| `null-drift-core` | Seeded random projection, cyclic permutation, superposition, Hamming-distance cleanup | [`crates/null-drift-core/src`](crates/null-drift-core/src) |
| `nulldrift_agents.py` | Prototype synchronous/async clients using CrewAI/LangGraph-inspired interfaces; not verified drop-in implementations of those frameworks | [`nulldrift_agents.py`](nulldrift_agents.py) |

The default `AllMiniLML6V2` model produces 384-dimensional embeddings according to its [model card](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2); FastEmbed initializes it in the gateway. External embeddings can be sent **directly to the daemon** using its `embedding` JSON field. The public gateway `/inject` endpoint currently accepts `text` and `salience`, but does **not** forward a client-provided embedding. See the [gateway request type](crates/gateway-rs/src/main.rs) and [daemon request type](crates/nulld/src/main.rs).

## Quick start

From the repository root, with Docker and Docker Compose installed:

```bash
docker compose -f docker/docker-compose.yml up --build -d
curl -fsS http://127.0.0.1:8000/health
```

Compose publishes the gateway on **127.0.0.1:8000**, not to the public network. The gateway health route returns HTTP 200 (`{"status":"ok"}`) when the daemon is reachable, otherwise HTTP 503. Startup can involve downloading an embedding model. See the [Compose file](docker/docker-compose.yml) and [gateway health handler](crates/gateway-rs/src/main.rs).

### Gateway API

```bash
curl -fsS -X POST "http://127.0.0.1:8000/inject?thread_id=demo_1" \
  -H "Content-Type: application/json" \
  -d '{"text":"A remembered observation","salience":0.95}'
curl -fsS "http://127.0.0.1:8000/recall?thread_id=demo_1"
curl -fsS -X POST "http://127.0.0.1:8000/snapshot?thread_id=demo_1"
curl -fsS -X POST "http://127.0.0.1:8000/restore?thread_id=demo_1"
```

`thread_id` defaults to `default`. Valid IDs are 1–128 ASCII letters/digits, `-`, `_`, and single `.` characters (not `.` alone and no `..`); invalid IDs return HTTP 400. The daemon's `/inject` handler accepts an `embedding` array, `text`, and `salience` for direct embedding use. Snapshot/restore uses Postcard-serialized `state_<thread_id>.nd` files under the daemon working directory, backed by the named volume in the provided Compose configuration. Checkpoints are staged to a same-directory temporary file and renamed after writing and syncing file contents; failed writes preserve the previous checkpoint, but storage-level failures and un-synced parent directories still limit crash/power-loss durability. An existing checkpoint that cannot be read or decoded now causes a server error rather than silently resetting that thread; preserve the file for manual recovery. [Daemon source](crates/nulld/src/main.rs) · [Postcard format](https://docs.rs/postcard/latest/postcard/)

**Security:** Thread IDs select state; they are **not authentication or tenant authorization**. Neither service currently implements built-in caller authentication. Keep the services on trusted networks and put authentication, authorization, TLS and request limiting at a deployment boundary before allowing untrusted callers. Do not publicly expose the daemon. See the [source](crates/nulld/src/main.rs), [Compose binding](docker/docker-compose.yml), and [security policy](docs/SECURITY.md).

## How the memory state works

1. A deterministic Gaussian matrix maps an embedding into a **10,000-element** array of ±1 values ([projection implementation](crates/null-drift-core/src/spl.rs)).
2. Each injection circularly rotates the running float state and adds the new bipolar vector scaled by `salience` ([HRSA implementation](crates/null-drift-core/src/hrsa.rs)).
3. When `salience >= 0.90`, the daemon also stores the bipolar vector and its text in an **append-only attractor list** ([daemon](crates/nulld/src/main.rs); [index](crates/null-drift-core/src/amn.rs)).
4. Recall binarizes the active state and looks for the closest stored attractor in **Hamming distance**, subject to a cleanup threshold (default 3,000 mismatches; configurable using `CLEANUP_THRESHOLD`); otherwise `recovered_text` is `null`. Optional `steps_ago` applies a modulo-based inverse rotation before lookup. Returned text is a best-match estimate, **not guaranteed reconstruction** of a specific earlier event ([recall handler](crates/nulld/src/main.rs); [HRSA](crates/null-drift-core/src/hrsa.rs)).

High-dimensional distributed representations are an established research family: see [Kanerva (2009), *Hyperdimensional Computing*](https://doi.org/10.1007/s12559-009-9009-8) and [Plate (1995), *Holographic Reduced Representations*](https://doi.org/10.1109/72.377968). These papers motivate broad techniques; **they do not independently validate null-drift's retrieval quality, efficiency or persistence claims.**

### Capacity and computational limits

- The active HRSA array is fixed at 10,000 `f32` values (~40,000 bytes before overhead). A default 384×10,000 `f32` projection is ~15.36 MB decimal (~14.65 MiB).
- **Total process memory is not O(1) in event count:** each high-salience event adds an attractor vector and text. Projector allocations now have an independent budget: a new dimension must be 1–4096, and all cached projection matrices together can contain at most 64 million `f32` entries (256 MB for matrix data, excluding overhead). A previously unseen dimension that would exceed the budget returns HTTP 503; unsupported dimensions return HTTP 400. Existing cached dimensions remain usable. These guards **do not** bound attractor, thread-cache, request, model, or overall process memory.
- The [Moka cache](https://docs.rs/moka/latest/moka/future/struct.Cache.html) is configured for at most 10,000 thread entries and a 24-hour *time-to-idle* expiration; this is an entry-count policy, not a strict total-RAM ceiling. Concurrent first access to the same thread is coalesced into one initialization using Moka's per-key async loader. Eviction writes state to disk on a best-effort basis.
- A `steps_ago` lookup uses a cyclic offset rather than proportional work for each step, but matching stored anchors still scales with the number of anchors ([core](crates/null-drift-core/src/hrsa.rs), [index](crates/null-drift-core/src/amn.rs)).

## Benchmarks: what the repository actually shows

The committed [benchmark-results artifact](docs/benchmarks/benchmark_results.txt) reports **50 injects and 10 recalls** with the following observed end-to-end timings:

| Recorded metric | Logged result |
| --- | ---: |
| Mean inject | 43.75 ms |
| Fastest inject | 32.91 ms |
| Slowest inject | 253.11 ms |
| Mean recall | 20.12 ms |
| Snapshot | 10.40 ms |

These are **archived measurements**, not independently reproduced or current-version guarantees. The artifact does not record a complete hardware/software environment, statistical uncertainty, or multiple trials; hardware and workload affect latency. The [benchmark script](scripts/benchmark.py) includes hard-coded memory and complexity statements which are **not memory measurements**. Re-run and record device, commit, dependencies, model cache status, repetitions, and distributions before comparing performance.

The [token benchmark](scripts/token_benchmark.py) is a **simulation**, not an API billing trace: it assumes 500 base tokens plus a fixed 200-token projected context, compared with accumulating synthetic conversation history. The resulting [chart](docs/assets/token_diff_benchmark.png) illustrates that assumption only; it does not demonstrate real provider savings, infinite memory, or retrieval accuracy. The [needle stress-test script](tests/advanced/needle_test.py) is a test scenario, not a statistically replicated reliability study.

## Testing, limitations and roadmap

CI performs Rust formatting, Clippy, unit tests and Python style checks ([compliance workflow](.github/workflows/compliance.yml)). External security tooling runs in a **non-blocking** workflow ([scanners](.github/workflows/security-scanners.yml)); a green scan workflow is not proof of no vulnerabilities. There is an [integration suite](tests/integration/test_frameworks.py), but a green standard CI run alone does not establish that the full Docker/inference/agent stack passed end-to-end testing.

Known work includes: enforce per-tenant authorization, bound projector and attractor memory, make snapshot writes atomic, test embeddings and API contracts end to end, benchmark reproducibly, and validate retrieval quality against baselines. See [security guidance](docs/SECURITY.md) and [contributing](CONTRIBUTING.md).

## References and evidence

For a claim-by-claim distinction between code evidence, third-party research, logged measurements and open questions, see [`docs/EVIDENCE.md`](docs/EVIDENCE.md). Relevant third-party primary references: [Kanerva 2009](https://doi.org/10.1007/s12559-009-9009-8), [Plate 1995](https://doi.org/10.1109/72.377968), [All-MiniLM-L6-v2 model card](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2), [Moka cache](https://docs.rs/moka/latest/moka/future/struct.Cache.html), [Axum request body limits](https://docs.rs/axum/latest/axum/extract/struct.DefaultBodyLimit.html), and [Postcard serialization](https://docs.rs/postcard/latest/postcard/).

## License

Licensed under [GNU AGPL v3](LICENSE). The AGPL includes source-availability obligations for modified network-accessible software; see the [GNU project explanation](https://www.gnu.org/licenses/why-affero-gpl.html). Commercial licensing inquiries should go to the repository maintainer.
