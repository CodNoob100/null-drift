# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Changed

- Update the embedding, HTTP, and projection RNG dependencies to compatible current major versions; enable reqwest query serialization explicitly and switch to FastEmbed `TextInitOptions`.

### Security

- Validate daemon thread IDs before using them in persisted state filenames; reject unsafe IDs with HTTP 400 and add regression tests.

### Added

- `/health` endpoint to the `nulld` daemon returning HTTP 200 with `{"status": "ok"}` for Docker/Kubernetes readiness probes.
