# Contributing to null-drift

First off, thank you for considering contributing to `null-drift`! It's people like you that make open source such a great community.

## 🚀 Getting Started

If you are new to the project, the best place to start is by looking at the **Good First Issues** label on our GitHub repository. These issues are specifically curated to be isolated, require zero knowledge of the deep mathematical phase space architecture, and focus heavily on improving the Developer Experience (DX).

### Local Development Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/CodNoob100/null-drift.git
   cd null-drift
   ```
2. **Run the Rust Daemon:**
   ```bash
   cargo run --bin nulld
   ```
3. **Run the Python Gateway:**
   ```bash
   cd gateway
   pip install -r requirements.txt
   python main.py
   ```

## ⚖️ Code Quality & CI Rules

To maintain high engineering standards, our CI pipeline strictly enforces the following rules using custom automated bots. **Your PR will fail if these are not met:**

1. **No Dead Code:** The use of `#[allow(dead_code)]` and `#[allow(unused)]` is strictly forbidden. 
2. **TODO Formats & Lifespan:** 
   - Every `TODO` comment *must* contain a link to a tracking issue (e.g., `// TODO(issue #123)` or `// TODO(https://github.com/...)`).
   - `TODO` comments automatically expire after **30 days**. If a `TODO` is older than 30 days (verified automatically via `git blame`), the CI build will fail.
3. **Strict Formatting & Linting:** 
   - **Rust:** Code must pass `cargo fmt --check` and `cargo clippy` with a strict zero-warnings policy (`-D warnings`).
   - **Python:** Code must pass `black --check` and `flake8` for style compliance.
4. **Dependency Auditing:** 
   - The dependency tree must not contain duplicate versions of the same crate (`cargo tree --duplicates`).
   - All dependencies are audited for known CVEs via `cargo-audit` and `osv-scanner`.
5. **No Secret Leaks:** Hardcoded secrets and credentials are automatically flagged and blocked by `gitleaks`.
6. **Branch Protection:** The `main` branch is strictly protected. Force pushing and branch deletion are globally disabled. Status checks (including all CI rules above) must pass before a Pull Request can be merged.

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

## 🤖 Automated Bots and CI

We utilize several automated bots to maintain repository health:
- **Dependabot:** Automatically updates `cargo` dependencies and GitHub Actions.
- **Compliance Bots:** Enforces `cargo fmt`, zero-warnings `cargo clippy`, and blocks direct pushes to `main`.
- **Security Scanners:** Runs `cargo-audit` and `gitleaks` to ensure no vulnerable dependencies or leaked secrets enter the codebase.

By submitting a Pull Request, you agree that your contributions will be licensed under the project's AGPL-3.0 License.
