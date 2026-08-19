# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added

- `/health` endpoint to the `nulld` daemon returning HTTP 200 with `{"status": "ok"}` for Docker/Kubernetes readiness probes.
