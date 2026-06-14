# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **Token Accumulation Benchmark Script**: Added `scripts/token_benchmark.py` to accurately simulate and visually graph the massive API cost savings of the $\mathcal{O}(1)$ projection array vs standard linear context window accumulation across 100 consecutive agent turns.
- **Decoupled Rust Architecture**: Completely replaced the Python FastAPI gateway with `gateway-rs`, a native Rust microservice using `axum` and the C++ ONNX runtime (`fastembed`). Achieves an end-to-end embedding injection pipeline in under 31ms.
- **Dimension-Agnostic Engine**: `nulld` no longer hardcodes 384 dimensions. It natively detects the dimensionality of incoming vectors and dynamically instantiates matching $W_{proj}$ mathematical Phase Space matrices on-the-fly.
- **Bring-Your-Own-Embedding (BYOE)**: Python SDK adapters (`NullDriftCrewStorage` and `NullDriftLangGraphStore`) now accept an optional `embedding_function`. If provided, embeddings are generated strictly on the client (e.g., using OpenAI or local Ollama) and injected straight to `nulld`, completely bypassing the gateway.

### Changed
- **Lock-Free Object Pool**: Removed the massive `Mutex` bottleneck around the `fastembed` ONNX model in `gateway-rs`. Implemented a lock-free round-robin object pool that scales embedding inference instances to available CPU cores, boosting throughput from 15 RPS to ~90 RPS.
- **Serialization Framework Migration**: Replaced the deprecated `bincode` serialization library with the highly secure `postcard` framework for `.nd` file checkpointing (Resolves RUSTSEC-2025-0141).

### Removed
- **Python Gateway**: Fully deleted the `gateway/` directory and deprecated `sentence-transformers` inference from the core stack.

### Security
- **Python Dependencies Pinned**: Pinned `fastapi`, `pydantic`, `torch`, `uvicorn`, and `requests` in `gateway/requirements.txt` to their latest secure patched versions to resolve multiple severe CVSS vulnerabilities.
## [0.2.0] - 2026-06-11

### Added
- **Multi-Tenant Architecture**: Converted the singleton `DaemonState` to a `moka::future::Cache` storing isolated `ThreadState` environments, scaling to thousands of concurrent agents on a single daemon.
- **LangGraph & CrewAI Native Integrations**: Added `nulldrift_agents.py` containing drop-in SDK adapters (`NullDriftCrewStorage`, `NullDriftLangGraphStore`) to provide seamless memory sync for popular AI frameworks.
- **Time-To-Idle (TTI) Disk Paging**: Inactive `ThreadState` instances are automatically swapped to disk (`state_{thread_id}.nd`) after 24 hours of inactivity to save RAM, with instant on-demand hydration.
- **Deterministic Projector**: The global 15MB 10,000D projection matrix is now seeded deterministically via `rand_pcg::Pcg64`, guaranteeing survival across daemon reboots.
- **Docker Compose Test Architecture**: Created `docker-compose.test.yml` for fully isolated native ML framework integration testing.

### Changed
- **Strict $O(1)$ Memory Fix**: Completely purged `step_history: Vec<String>` from the core `ThreadState`. The daemon now strictly guarantees $< 50$ KB memory limits per thread regardless of injection count.
- **Mathematical $\mathcal{O}(1)$ Recall**: Fixed a fatal $O(N^2)$ algorithm in the `/recall` endpoint. The daemon no longer computes 500 billion backwards time-shifts for 10,000 vectors. It now executes exactly 1 Hamming Distance comparison on the current `active_state`, dropping recall time from hours to ~1 microsecond.
- Updated all API routes (`/inject`, `/recall`, `/snapshot`, `/restore`) to use the `?thread_id=` parameter.

### Fixed
- Fixed an asynchronous deadlock in `gateway-rs` by wrapping the synchronous C++ ONNX threadpool (`fastembed`) inside `tokio::task::spawn_blocking`, allowing it to flawlessly handle thousands of concurrent TCP streams without hanging.
- Fixed incompatible `bincode::deserialize` library mismatch when loading the phase space from disk during `/restore`.

### Added
- **Advanced Benchmarking Suite**: Engineered a comprehensive test suite in `tests/advanced/` to validate the mathematics:
  - `throughput_test.py`: Asynchronously bombs the multi-tenant architecture with 10,000 concurrent thread injections.
  - `needle_test.py`: Injects a High-Salience Needle followed by 10,000 chaotic noise permutations to prove immunity to catastrophic interference.
  - `monitor_o1.py`: Hooks natively into `nulld.exe` via `psutil` to generate `matplotlib` graphs visually proving the flat $\mathcal{O}(1)$ memory bounds.

### Added
- **SECURITY.md**, **CONTRIBUTING.md**, and **CHANGELOG.md** to establish community guidelines and open-source standards.
- High-concurrency `demo.gif` to the README demonstrating the performance of the pure Rust daemon.
- $O(1)$ memory scaling benchmark graph (`benchmark_memory.png`) comparing `null-drift` against standard VectorDBs like Chroma and pgvector.
- Integration tests (`docker_load_test.py` and `load_test.py`) for stress testing the Axum memory daemon and FastAPI gateway.
- Initial release of the Holographic Reversible State Accumulator (HRSA).
- `tokio::sync::RwLock` implementation for lock-free, highly concurrent memory state reads.
- Bipolar phase space projection using a Gaussian Random Matrix ($W_{proj}$).
- Geometric decay implementation for temporal permutations (fading noise).
- Attractor Memory Network (AMN) associative cleanup for high-salience anchors.
- Microsecond zero-loss binary state serialization using `bincode` (`state.nd`).
- Dockerized `FastAPI` Python ML Gateway using `sentence-transformers` (`all-MiniLM-L6-v2`) to act as the embedding ingestion layer.
