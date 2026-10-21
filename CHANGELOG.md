# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Fixed

- Reconstruct historical HRSA state using a single modulo-based cyclic offset rather than one full 10,000D permutation per requested historical step. Add equivalence and extreme-step regression tests.

### Fixed

- Remove the post-merge commit-message check that falsely failed CI for legitimate squash merges. GitHub branch protection remains responsible for enforcing PR-only merges.

### Changed

- Update the embedding, HTTP, and projection RNG dependencies to compatible current major versions; enable reqwest query serialization explicitly and switch to FastEmbed `TextInitOptions`.

- Report CI failures in pull-request checks without opening repeated issues, and treat transitive duplicate dependency versions as advisory output.

### Security

- Validate daemon thread IDs before using them in persisted state filenames; reject unsafe IDs with HTTP 400 and add regression tests.

### Added

- `/health` endpoint to the `nulld` daemon returning HTTP 200 with `{"status": "ok"}` for Docker/Kubernetes readiness probes.
