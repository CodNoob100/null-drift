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
