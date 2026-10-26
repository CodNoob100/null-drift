# Choose your null-drift setup path

This guide separates a **first working request** from **source-level development**. Commands below are based on the repository's Compose file, Rust crates and CI workflow; they have **not** been independently executed in a Docker environment as part of this documentation change.

## Path A: try the service (Docker)

**Prerequisites:** Git, Docker Engine/Desktop with the Compose v2 plugin, enough disk/RAM for two Rust builds and the FastEmbed model download, and internet access for the first model download. No Python or local Rust toolchain is required.

```sh
git clone https://github.com/CodNoob100/null-drift.git
cd null-drift
docker compose -f docker/docker-compose.yml up --build -d
docker compose -f docker/docker-compose.yml ps
curl -fsS http://127.0.0.1:8000/health
```

If the first health request fails while the embedding model is initializing, wait for readiness instead of repeatedly restarting containers (POSIX shell; up to about 3 minutes):

```sh
ready=0
for attempt in $(seq 1 36); do
  if curl --fail --silent --show-error --max-time 3 http://127.0.0.1:8000/health; then
    ready=1
    break
  fi
  sleep 5
done
if [ "$ready" -ne 1 ]; then
  echo 'Gateway did not become healthy; inspect Compose logs' >&2
  docker compose -f docker/docker-compose.yml ps
  docker compose -f docker/docker-compose.yml logs --tail=100 gateway nulld
  exit 1
fi
```

This timeout is illustrative; first-time model downloads can take longer. A failed readiness check is a diagnostic, not proof of a permanently broken installation.

**Expected health response once both services are ready:** `{"status":"ok"}`. Model initialization may take time on first startup; if health is unavailable, inspect logs instead of assuming success:

```sh
docker compose -f docker/docker-compose.yml logs --tail=100 gateway nulld
```

Try an inject and recall:

```sh
curl -fsS -X POST 'http://127.0.0.1:8000/inject?thread_id=first_try' \
  -H 'Content-Type: application/json' \
  -d '{"text":"My first null-drift observation","salience":1.0}'
curl -fsS 'http://127.0.0.1:8000/recall?thread_id=first_try'
```

The recall response includes a `recovered_text` field, which may be `null`: retrieval is approximate and not a lossless-store guarantee. To stop without deleting the named checkpoint volume:

```sh
docker compose -f docker/docker-compose.yml down
```

**Do not use `down -v` unless you intend to delete the persisted named volume.** The Compose configuration binds the gateway to localhost (`127.0.0.1:8000`) and keeps the daemon on an internal Docker network. Thread IDs are **not** authentication. Never expose either service to untrusted networks without an external security boundary.

### Troubleshooting

- `docker compose` missing: install Docker Compose v2; older `docker-compose` syntax is not the documented path.
- Health returns HTTP 503: gateway cannot reach a healthy daemon yet. Check `ps` and both services' logs; startup and model download can take time.
- Port 8000 already allocated: stop the conflicting local service or adjust the host-side port mapping in your local Compose configuration.
- Build/model download fails: inspect the specific Docker build or gateway log error, available disk/memory, and network access; do not treat a running container as proof of a ready model.
- Inject returns a non-2xx status: preserve the status/body and consult logs; do not assume data was stored.

## Path B: power-developer workflow

**Prerequisites:** Rust toolchain with Cargo, Python for lint/tests, and optionally Docker for full-stack testing. The current CI uses Rust nightly, `cargo fmt --check`, `cargo clippy --workspace --lib --bins -- -D warnings`, and `cargo test --workspace --lib --bins`.

From repository root, run the **service-independent Rust checks** (no running gateway or FastEmbed model initialization required). Cargo may still fetch Rust dependencies/toolchains on first use; these commands are not guaranteed to work without internet:

```sh
cargo +nightly fmt --check
cargo +nightly clippy --workspace --lib --bins -- -D warnings
cargo +nightly test --workspace --lib --bins
```

Install the nightly toolchain and components with `rustup toolchain install nightly` and `rustup component add --toolchain nightly rustfmt clippy` if absent. CI also checks Python formatting and linting with Black and Flake8. A green formatting/lint run does **not** mean Python adapter unit tests ran; see [issue #173](https://github.com/CodNoob100/null-drift/issues/173).

For manual service inspection, source entry points are:

- `crates/nulld/src/main.rs`: daemon, default port 3000, `HOST`, `PORT`, `CLEANUP_THRESHOLD`, snapshot/restore.
- `crates/gateway-rs/src/main.rs`: gateway, default port 8000, `HOST`, `PORT`, `NULLD_URL`, FastEmbed initialization.
- `crates/null-drift-core/src/`: projection, HRSA and attractor implementation.
- `nulldrift_agents.py`: prototype Python adapters, **not** verified drop-in framework integrations.

To manually run both Rust services, use **separate terminals**, choose a private working directory for daemon checkpoint files, and explicitly set bind/network variables. Unlike Docker Compose, manual startup does not provide service orchestration or automatic restarts. Example on a trusted local development machine:

```sh
# Terminal 1, repository root (writes checkpoint files in current working directory)
HOST=127.0.0.1 PORT=3000 cargo run -p nulld
# Terminal 2, repository root
HOST=127.0.0.1 PORT=8000 NULLD_URL=http://127.0.0.1:3000 cargo run -p gateway-rs
```

After the gateway starts, check `curl -fsS http://127.0.0.1:8000/health` before sending writes. Stop each process with Ctrl-C; unlike the Compose named volume, manually created checkpoints remain in the daemon process's working directory.

These source-run commands are guidance, not a verified end-to-end smoke test; the gateway may download an embedding model. Inspect `Cargo.toml` workspace/package names if commands differ on your branch. The daemon checkpoint location depends on its process working directory, so do not run it from a directory containing valuable similarly named state files.

### Investigation and benchmarks

Use `docker compose -f docker/docker-compose.yml logs -f gateway nulld` for integrated logs. `python scripts/benchmark.py` requires a running gateway and reports end-to-end latencies, **not** independently measured memory or asymptotic complexity. Record commit SHA, hardware, model cache state, sample counts and exact commands. The `tests/advanced/needle_test.py` workload sends many requests; run only against an isolated local instance. For checkpoint regression work, preserve #159's fail-closed behavior: existing unreadable/corrupt files must error rather than silently reset.

Before contributing, check [open issues](https://github.com/CodNoob100/null-drift/issues), [open PRs](https://github.com/CodNoob100/null-drift/pulls), [CONTRIBUTING.md](../CONTRIBUTING.md), and the [security notes](SECURITY.md). Keep experimental high-impact resource/retention changes separate from onboarding; draft [PR #160](https://github.com/CodNoob100/null-drift/pull/160) is not deployed or merged.
