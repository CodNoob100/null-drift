# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Fixed

- Handle HTTP 4xx/5xx in the LangGraph async snapshot and restore helpers: they caught only `httpx.RequestError`, so `raise_for_status()`'s `HTTPStatusError` escaped the logging path and propagated to the caller. Regression tests cover 4xx/5xx, transport failures, and the silent-success path via `httpx.MockTransport`.
- Refuse to silently initialize an empty thread when a persisted checkpoint exists but is corrupt or unreadable. Only a missing snapshot creates a new state; return an explicit error and preserve the existing bytes. Add valid/corrupt/missing checkpoint regression tests.

### Fixed

- Use the same Hamming-distance cleanup threshold and dimension-safe vector comparison for current-state recall as for historical recall. Return null for unrelated or malformed anchors rather than selecting an arbitrary nearest match or indexing past a truncated vector. Add regression tests.

### Fixed

- Count unmatched dimensions in Hamming distance so a short or truncated attractor cannot appear to be an exact cleanup match. Regression tests cover unequal vector lengths and exact-match thresholds.

### Fixed

- Coalesce concurrent first access or disk hydration of the same thread through the Moka async cache initializer. All requests now share one cached `ThreadState`, preventing a race that could lose accepted events. Add concurrent-start regression tests without changing snapshot serialization or the HTTP API.

### Fixed

- Persist manual and idle-eviction checkpoints through uniquely named, exclusive-create temporary files, sync bytes and rename within the snapshot directory; keep an existing checkpoint intact if writing a replacement fails. This is not a full power-loss durability guarantee because directory sync is not performed.

### Security

- Bound daemon projection-matrix allocations to 64 million total `f32` entries (256 MB matrix storage); reject new embedding dimensions above 4096 or when the shared matrix budget is exhausted, and validate thread IDs before projector construction. Include budget and overflow regression tests.

## [0.3.0] - 2026-10-21

### Added

- Daemon and gateway `/health` routes; gateway readiness probes daemon reachability.
- New regression tests for thread ID validation, historical recall equivalence, and deterministic projection migration.
- Evidence-backed README, cited research references, and an explicit evidence ledger.

### Changed

- Upgrade FastEmbed, reqwest, rand, rand_distr and rand_pcg together, adjusting API use and enabling reqwest query serialization.
- Align Cargo workspace package versions with the v0.3.0 release.
- Make duplicate transitive dependency version detection advisory instead of opening repeated CI issues.
- Replace unverified memory, recall, security and token-savings assertions with supported descriptions and documented limitations.

### Fixed

- Avoid work proportional to historical recall steps by using a bounded cyclic offset.
- Remove post-merge commit-message CI heuristic that incorrectly failed on legitimate squash merges.
- Integration readiness now requires a successful gateway health response.

### Security

- Validate daemon thread IDs before constructing snapshot paths; invalid values produce HTTP 400.
- Document lack of built-in tenant authorization, dynamic allocation risks, best-effort persistence and non-blocking security scanners.

### Compatibility notes

- Thread IDs that fail the new validation are rejected; migrate existing thread names before upgrading.
- Dependency versions changed, including a major FastEmbed upgrade. A seeded projection regression test covers the sampled compatibility case, not all deployment or serialized-state scenarios.
- No prebuilt release binaries are supplied; use the repository source and Docker Compose configuration.

**Compare:** https://github.com/CodNoob100/null-drift/compare/v0.2.1...v0.3.0
