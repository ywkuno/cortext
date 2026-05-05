# Contributing

Thanks for considering a contribution to CodePrism. The project is early, but the bar is simple: keep the tool local-first, deterministic where possible, and honest about what its token estimates mean.

## Good First Areas

- Parser and extractor coverage for more languages.
- Better slice ranking without increasing default context size.
- Windows, macOS, and Linux CLI reliability.
- Benchmark fixtures that represent real repository shapes without private code.
- Documentation that helps agents use `prime`, `query`, `get`, `references`, and token-aware `read` before broad file reads.
- Lightweight visual-map improvements that do not slow down normal agent workflows.

## Local Setup

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

Run the core checks:

```bash
pytest
ruff check .
codeprism map .
codeprism benchmark-suite examples/benchmarks --out .codeprism/benchmarks/suite.json
python scripts/pre_release_proof.py --baseline-suite .codeprism/benchmarks/suite.json
```

Generated `.codeprism/` and `.contextopt/` artifacts are local working files and should not be committed.

## Development Principles

- Keep the default path local-only. Do not add network calls to core commands.
- Prefer static parsing, structured data, and deterministic graph facts before summarization.
- Keep generated artifacts inspectable as text, JSON, DOT, HTML, or SQLite.
- Preserve compatibility with the public `codeprism` CLI and the legacy `contextopt` command.
- Avoid heavyweight dependencies unless they clearly improve core mapping or retrieval.
- Treat token counts as estimates for comparison, not billing-grade measurements.

## Privacy

Do not include private source code, secrets, customer data, local filesystem paths, raw agent session logs, or personal identifiers in issues, fixtures, tests, docs, screenshots, or release notes.

When adding benchmark fixtures, use synthetic examples only. The fixture should show a real shape of code, not a real private project.

## Pull Requests

Before opening a pull request:

- Run `pytest`.
- Run `ruff check .`.
- Run the relevant CLI command manually when changing CLI behavior.
- Add or update tests for behavior changes.
- Update docs when a command, output format, benchmark, or agent workflow changes.
- Mention any schema or compatibility impact.

For public-release work, run:

```bash
python scripts/pre_release_proof.py --baseline-suite .codeprism/benchmarks/suite.json
```

## Benchmark Changes

Benchmark reports are useful only when they are reproducible and cautious. If a change affects benchmark output:

- Update `docs/benchmarks.md` when checked-in fixture results intentionally change.
- Include the relevant `codeprism benchmark-suite` or `benchmark-compare` output in the PR.
- Explain regressions honestly instead of hiding them.

## Security

Please do not report vulnerabilities by opening a public issue with exploit details. See [SECURITY.md](SECURITY.md) for the reporting path.
