# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.0] - 2026-06-11

### Added
- **Multi-Tenant Architecture**: Converted the singleton `DaemonState` to a `moka::future::Cache` storing isolated `ThreadState` environments, scaling to thousands of concurrent agents on a single daemon.
- **LangGraph & CrewAI Native Integrations**: Added `nulldrift_agents.py` containing drop-in SDK adapters (`NullDriftCrewStorage`, `NullDriftLangGraphStore`) to provide seamless memory sync for popular AI frameworks.
- **Time-To-Idle (TTI) Disk Paging**: Inactive `ThreadState` instances are automatically swapped to disk (`state_{thread_id}.nd`) after 24 hours of inactivity to save RAM, with instant on-demand hydration.
- **Deterministic Projector**: The global 15MB 10,000D projection matrix is now seeded deterministically via `rand_pcg::Pcg64`, guaranteeing survival across daemon reboots.
- **Docker Compose Test Architecture**: Created `docker-compose.test.yml` for fully isolated native ML framework integration testing.

### Changed
- **Strict $O(1)$ Memory Fix**: Completely purged `step_history: Vec<String>` from the core `ThreadState`. The daemon now strictly guarantees $< 50$ KB memory limits per thread regardless of injection count.
- Updated all API routes (`/inject`, `/recall`, `/snapshot`, `/restore`) to use the `?thread_id=` parameter.

### Fixed
- Fixed incompatible `bincode::deserialize` library mismatch when loading the phase space from disk during `/restore`.

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
