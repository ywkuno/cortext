# Security Policy

CodePrism is a local-first developer tool. Its core commands should not send repository contents, generated maps, session logs, or source snippets to external services.

## Supported Versions

CodePrism is alpha software. Security fixes are applied to the current `main` branch and the latest public release when releases are available.

## Reporting A Vulnerability

Use GitHub private vulnerability reporting for this repository when available. If that is not available, open a minimal public issue that says you have a security concern, but do not include exploit details, secrets, private source, local paths, or sensitive logs.

Please include:

- affected command or workflow
- operating system and Python version
- whether the issue requires a malicious repository, malicious input file, or local user action
- a minimal synthetic reproduction when possible

Do not include:

- private repository contents
- authentication tokens or secrets
- raw agent session logs
- customer data
- local filesystem paths from private machines

## Security Scope

In scope:

- unintended network access from default CodePrism commands
- path traversal or unsafe file writes
- unsafe handling of generated artifacts
- accidental disclosure through public docs, fixtures, traces, or release artifacts
- denial-of-service behavior from normal repository inputs

Out of scope:

- issues that require publishing private data in a public issue
- vulnerabilities in unrelated third-party tools used outside CodePrism
- benchmark differences caused only by local token-estimation heuristics

## Design Expectations

- Default workflows stay local-first.
- Generated artifacts stay inspectable.
- Read-only root workflows must not write into the target repository.
- Live Trace should contain command metadata only, not private source bodies.
- Large context outputs should stay capped unless a user explicitly opts in.
