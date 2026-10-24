# Security Policy

[![Security: Active](https://img.shields.io/badge/Security-Active_Monitoring-success.svg)]()

## Supported Versions

Currently, only the latest `main` branch of `null-drift` is officially supported with security updates. Published release tags (including `v0.3.0`) are not separately listed as supported versions.

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
5. **State Isolation:** The daemon uses a `thread_id` to select cached thread state. This is state separation, not a complete tenant authorization boundary; deployments must enforce appropriate access controls. Unauthorized state access is a high-priority security concern.

If you find a mechanism that violates these boundaries, please report it immediately.

---

## 4. Recently Patched Vulnerabilities

The following changes address specific resource and concurrency risks. They are not guarantees of immunity to denial-of-service or fixed response times:
- **Recall computation (changed in v0.2.0):** The recall path was refactored to avoid repeated inverse-permutation work. This does not establish a universal $O(1)$ bound for the entire request, constant memory use, or a one-microsecond response-time guarantee.
- **Blocking inference (changed in v0.2.0):** The gateway moves synchronous inference work to blocking worker threads with `tokio::task::spawn_blocking`. This helps avoid blocking async executor threads but does not guarantee availability under overload.

---

## 5. Automated Boundary Enforcement

The repository runs advisory security scanners on pull requests, `main` pushes, and a weekly schedule. Their successful workflow conclusion does **not** mean the project is vulnerability-free:

- **cargo-audit**: Checks Rust dependencies for known advisories, but its current invocation is nonblocking (`|| true`) and does not prevent merges.
- **Gitleaks**: Looks for potential secrets, but uses `--exit-code 0` and therefore does not block merges on findings.
- **OSV Scanner**: Checks dependencies against vulnerability data, but its current invocation is nonblocking (`|| true`).

OSV and Cargo Audit JSON outputs are not currently retained as CI artifacts; their findings cannot be inferred from a green workflow. See the [scanner workflow](../.github/workflows/security-scanners.yml) and the [evidence ledger](EVIDENCE.md) for verified limits and remaining validation needs.

Thank you for helping keep the continuous AI memory ecosystem safe!
