# Contributing

Thanks for helping improve CodePrism.

## Development Setup

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

## Checks

Run these before opening a pull request:

```bash
pytest
ruff check .
codeprism map .
codeprism export --format json --out .contextopt/context-pack.json
```

Generated `.contextopt/` artifacts are local working files and should usually stay out of commits.
Use `examples/contextopt.config.example.toml` if you need to document config values without committing local `.contextopt/config.toml`.

## Project Principles

- Keep the default path local-first.
- Prefer deterministic static extraction before LLM summarization.
- Keep generated context artifacts inspectable.
- Avoid exaggerated benchmark claims.
- Keep Windows, macOS, and Linux CLI behavior in mind.
- Add dependencies only when they clearly improve the core workflow.

## Pull Request Notes

Please describe:

- the user-facing behavior changed
- tests or CLI smoke checks run
- any schema changes to exported graph or activity data
- any known limitations
