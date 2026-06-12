# Security Policy

[![Security: Active](https://img.shields.io/badge/Security-Active_Monitoring-success.svg)]()

## Supported Versions

Currently, only the latest `main` branch of `null-drift` is officially supported with security updates. 

| Version | Supported          |
| ------- | ------------------ |
| `main`  | :white_check_mark: |

## 1. Reporting a Vulnerability

We take the security of `null-drift` very seriously. If you discover a vulnerability, **do not open a public issue.**

Please report any security issues privately by emailing `anshuman.dwibedi.dev@gmail.com`. We will acknowledge receipt of your vulnerability report within 48 hours and strive to send you regular updates about our progress.

---

## 2. Security SLAs and Patch Timelines

We operate under strict Security Patch Service Level Agreements (SLAs) based on the CVSS score of the vulnerability. 

We commit to the following patch timelines from the date of disclosure:

| Severity | CVSS Range | Patch SLA |
|----------|------------|-----------|
| **Critical** | `9.0 – 10.0` | 7 days |
| **High**     | `7.0 – 8.9`  | 21 days |
| **Medium**   | `4.0 – 6.9`  | Next scheduled release |
| **Low**      | `0.0 – 3.9`  | Evaluated case-by-case |

---

## 3. Our Threat Model

`null-drift`'s security boundaries are strictly defined. We are particularly interested in vulnerabilities related to:

1. **State Poisoning:** We utilize `tokio::sync::RwLock` specifically to prevent panic-induced lock poisoning. Any vector capable of deadlocking or permanently poisoning the `Hrsa` state is a high-priority vulnerability.
2. **Denial of Service (DoS):** Any malformed payload that bypasses the `axum` `DefaultBodyLimit` (64KB) in the core daemon or causes uncontrolled memory allocation.
3. **ONNX Runtime Exploits:** The `gateway-rs` microservice executes ML inference using `fastembed` and the C++ ONNX runtime. Any maliciously crafted text injection that achieves Remote Code Execution (RCE) via ONNX runtime buffer overflows is treated as a Critical CVE.
4. **Postcard Deserialization:** Any vulnerability allowing Remote Code Execution (RCE) or arbitrary memory overwrites during the `state.nd` deserialization phase.
5. **Multi-Tenant State Isolation:** We utilize `moka::future::Cache` to map and isolate distinct AI agents. Any vulnerability allowing Cross-Tenant State Leakage (reading or modifying a `ThreadState` belonging to another `thread_id`) is a critical vulnerability.

If you find a mechanism that violates these boundaries, please report it immediately.

---

## 4. Recently Patched Vulnerabilities

We continuously stress-test the architecture against extreme concurrency limits to proactively identify and patch denial-of-service (DoS) vectors:
- **Algorithmic Complexity DoS (Patched in v0.2.0):** An $O(N^2)$ vector in the HRSA `/recall` endpoint previously allowed a single thread to lock the CPU for hours by triggering 500 billion nested permutations. This was mathematically optimized to a strict $O(1)$ constant bound (1 microsecond retrieval).
- **Asynchronous Deadlocking (Patched in v0.2.0):** The `gateway-rs` inference microservice was patched to prevent malicious flooding of the async runtime. Synchronous C++ ONNX calls are now strictly wrapped via `tokio::task::spawn_blocking`, rendering the gateway immune to TCP starvation under massive load.

---

## 5. Automated Boundary Enforcement

To protect our Threat Model against accidental or malicious regressions, we run dedicated Security Bots in our CI pipeline:

- **cargo-audit**: Prevents dependencies with known CVEs from being merged.
- **gitleaks**: Actively blocks commits containing hardcoded secrets, API keys, or leaked credentials.

Thank you for helping keep the continuous AI memory ecosystem safe!
