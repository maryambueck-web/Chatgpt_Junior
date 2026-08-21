# Security Policy

Juni SafeChatGPT is a safety-critical application — it mediates what a child sees. We take reports seriously and appreciate the effort of anyone who reports responsibly.

## Reporting a Vulnerability

**Please do not open a public issue for a security vulnerability.**

Instead, report it privately via [GitHub Security Advisories](https://github.com/maryambueck-web/Chatgpt_Junior/security/advisories/new) for this repository. Include:

- A description of the issue and its potential impact
- Steps to reproduce (exact input/request where relevant)
- The affected file(s) or component, if known

We'll acknowledge reports as quickly as we can and keep you updated as we investigate and fix the issue. Please allow time for a fix before any public disclosure.

## What counts as a security report vs. a regular bug

| Report privately (security advisory) | Report publicly (regular issue) |
| --- | --- |
| PIN brute-force bypass, lockout bypass | A prompt that slips past the safety classifier |
| SQL/command injection, path traversal | A UI bug, typo, or missing feature |
| Exposure of another family's data (session/data isolation break) | Missing test coverage |
| Secrets or API keys leaking into logs, responses, or the repo | Deploy/config documentation gaps |

A classifier miss (an unsafe message that should have been `BLOCK`ed but was `ALLOW`ed) is a serious quality bug and we want it reported — but since it doesn't expose data or grant unauthorized access, a public issue with the exact input is fine and helps us add a regression test faster. See [CONTRIBUTING.md](CONTRIBUTING.md#reporting-a-safety-gap).

## Scope

This is a proof-of-concept project (see [Limitations](README.md#limitations) in the README) and is **not** intended for multi-tenant or unattended production use without the hardening described in [docs/production_deployment.md](docs/production_deployment.md). Reports about the inherent limitations already documented there (shared PIN instead of real auth, text-only image moderation, etc.) are welcome as discussion but are known, not new findings.

## Supported Versions

This project does not yet maintain multiple release branches — security fixes are applied to `main` only.
