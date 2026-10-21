# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Fixed

- Treat any unmatched elements as Hamming-distance mismatches when comparing different-sized hypervectors, so a truncated anchor cannot appear to be an exact match. Add cleanup and distance regression tests.

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
