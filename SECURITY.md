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
2. **Denial of Service (DoS):** Any malformed payload that bypasses the Axum `DefaultBodyLimit` (64KB) or causes uncontrolled memory allocation.
3. **Bincode Deserialization:** Any vulnerability allowing Remote Code Execution (RCE) or arbitrary memory overwrites during the `state.nd` deserialization phase.

If you find a mechanism that violates these boundaries, please report it immediately.

---

## 4. Automated Boundary Enforcement

To protect our Threat Model against accidental or malicious regressions, we run dedicated Security Bots in our CI pipeline:

- **cargo-audit**: Prevents dependencies with known CVEs from being merged.
- **gitleaks**: Actively blocks commits containing hardcoded secrets, API keys, or leaked credentials.

Thank you for helping keep the continuous AI memory ecosystem safe!
