# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2026-06-10

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
