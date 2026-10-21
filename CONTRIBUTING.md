# Contributing to null-drift

[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](https://github.com/CodNoob100/null-drift/pulls)
[![Good First Issues](https://img.shields.io/github/issues/CodNoob100/null-drift/good%20first%20issue)](https://github.com/CodNoob100/null-drift/issues?q=is%3Aissue+is%3Aopen+label%3A%22good+first+issue%22)

First off, thank you for considering contributing to `null-drift`! It's people like you that make open source such a great community.

## 🚀 Getting Started

If you are new to the project, the best place to start is by looking at the **Good First Issues** label on our GitHub repository. These issues are specifically curated to be isolated, require zero knowledge of the deep mathematical phase space architecture, and focus heavily on improving the Developer Experience (DX).

### Development setup

The gateway and daemon are **both Rust services**. You can use Docker Compose for a quick check, or run the two Rust binaries in separate terminals.

**Option A — Docker Compose** (from the repository root):

```bash
docker compose -f docker/docker-compose.yml up --build -d
curl -fsS http://127.0.0.1:8000/health
```

The gateway listens on `127.0.0.1:8000` through the provided Compose file. Its `/health` endpoint returns HTTP 503 until the daemon is reachable. The first start may download the embedding model.

**Option B — Rust workspace** (Rust toolchain required):

```bash
git clone https://github.com/CodNoob100/null-drift.git
cd null-drift
cargo run -p nulld
```

In a separate terminal in the same checkout:

```bash
NULLD_URL=http://127.0.0.1:3000 cargo run -p gateway-rs
```

Check `curl -fsS http://127.0.0.1:8000/health` once the model has initialized. Never expose either service to untrusted networks without external authentication and authorization; thread IDs are **not** access credentials.

For small Rust changes, run the same commands that the main compliance workflow checks:

```bash
cargo fmt --check
cargo clippy --workspace --lib --bins -- -D warnings
cargo test --workspace --lib --bins
```

Python client adapters are in `nulldrift_agents.py`. They are prototypes, not guaranteed drop-in CrewAI or LangGraph implementations. Python formatting is checked using `black --check .` and `flake8 . --max-line-length=120`. See [README.md](README.md) for the supported API and current limitations.

## 💡 Submitting Feature Requests & Bug Reports

To help us triage issues efficiently, please observe our **Issue Naming Conventions**. When opening a new issue, your title must start with one of the following prefixes:
- `[BUG]` - Reporting a bug or error.
- `[FEATURE]` - Suggesting a new feature or enhancement.
- `[DOCS]` - Proposing improvements to documentation.
- `[DX]` - Suggesting improvements to Developer Experience (tooling, workflows, etc.).

*Note: If you use the provided GitHub Issue Templates, these prefixes will be added to your title automatically!*

**Feature Requests** should be well thought out. Please include:
1. The specific problem you are trying to solve.
2. A detailed explanation of your proposed solution.
3. Any alternatives you have considered.

## ⚖️ Code Quality & CI Rules

To maintain high engineering standards, our CI pipeline strictly enforces the following rules using custom automated bots. **Your PR will fail if applicable blocking checks are not met:**

1. **No Dead Code:** The use of `#[allow(dead_code)]` and `#[allow(unused)]` is strictly forbidden. 
2. **TODO Formats & Lifespan:** 
   - Every `TODO` comment *must* contain a link to a tracking issue (e.g., `// TODO(issue #123)` or `// TODO(https://github.com/...)`).
   - `TODO` comments automatically expire after **30 days**. If a `TODO` is older than 30 days (verified automatically via `git blame`), the CI build will fail.
3. **Strict Formatting & Linting:** 
   - **Rust:** Code must pass `cargo fmt --check` and `cargo clippy` with a strict zero-warnings policy (`-D warnings`).
   - **Python:** Code must pass `black --check` and `flake8` for style compliance.
4. **Dependency Auditing:** 
   - `cargo tree --duplicates` reports transitive dependency duplication as a non-blocking warning; duplicates in upstream dependency graphs are not automatically considered actionable bugs.
   - Security scanners such as `cargo-audit` and `osv-scanner` run **non-blocking**; they produce advisory results and do not guarantee zero vulnerabilities.
5. **No Secret Leaks:** Never commit secrets or credentials. The current Gitleaks scanner runs in an **advisory** workflow and is not a substitute for review.
6. **Branch Protection:** The `main` branch is protected by GitHub rules and required status checks. Use Pull Requests for changes to `main`; merge commits, squash merges, and rebases must all be valid. Commit message conventions are not evidence of whether a change came through a PR. Check the active GitHub branch protection settings for bypass privileges and required reviews.

## 🤝 Adding SDK Integrations

`null-drift` aims to natively support all major AI agent frameworks (e.g., `CrewAI`, `LangGraph`, `AutoGen`). If you are contributing a new framework adapter to `nulldrift_agents.py`, you must:
1. Ensure the adapter natively forwards the `thread_id` to support the daemon's Multi-Tenant Architecture.
2. Implement isolated tests for the adapter within the `tests/integration/` suite.
3. Verify that the adapter seamlessly triggers asynchronous `/snapshot` and `/restore` sequences for Time-To-Idle (TTI) compliance.

## 🛠️ Pull Request Process

1. **Create a new branch** for your feature or bugfix (`git checkout -b feature/my-awesome-feature`).
2. **Make your changes.**
3. **Run Formatting and Linting:**
   We enforce strict Rust formatting and zero-warnings policies in our CI pipeline.
   ```bash
   cargo fmt
   cargo clippy -- -D warnings
   ```
4. **Commit your changes.** Please use descriptive commit messages.
5. **Push to your fork and submit a Pull Request** against the `main` branch.

## 📝 Maintaining a Changelog

To keep track of all the changes, features, and bug fixes in each release, we maintain a `CHANGELOG.md` file based on the [Keep a Changelog](https://keepachangelog.com/en/1.0.0/) format.
When submitting a Pull Request, please ensure you update the `CHANGELOG.md` file in the `[Unreleased]` section with a brief description of your changes. Categorize your changes under `Added`, `Changed`, `Deprecated`, `Removed`, `Fixed`, or `Security`.

## 🤖 Automated Bots and CI

We utilize several automated bots to maintain repository health:
- **Dependabot:** Automatically updates `cargo` dependencies and GitHub Actions.
- **Compliance Bots:** Enforces Rust formatting, Clippy, unit tests, Python formatting/linting and repository-specific rules. GitHub branch protection (not CI log text) controls whether direct pushes can be rejected.
- **Security Scanners:** Runs advisory checks (including `cargo-audit`, OSV and Gitleaks). Review the findings: scanner success does not prove there are no vulnerabilities or secrets.

By submitting a Pull Request, you agree that your contributions will be licensed under the project's AGPL-3.0 License.
