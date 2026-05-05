# AGENTS.md

## Project purpose

This repo implements CodePrism: a local-first codebase mapping tool that generates compact context packs, graph exports, and visual replay data for AI assistants.

## Ground rules for agents

- Keep code local-first. Do not add network calls unless explicitly requested.
- Prefer deterministic AST/static parsing before LLM summarization.
- Every generated context artifact must be inspectable text or SQLite.
- Avoid viral-project style claims. Use measured language and benchmark honestly.
- Keep the CLI working on Windows, macOS, and Linux.
- Do not introduce heavyweight dependencies unless there is a clear reason.

## Core commands

```bash
pip install -e ".[dev]"
pytest
ruff check .
codeprism map .
codeprism watch . --once
codeprism export --format md --out .codeprism/context-pack.md
codeprism export --format json --out .codeprism/context-pack.json
codeprism read README.md --mode signatures
codeprism get "heading::README.md::Quick Start"
codeprism references "heading::README.md::Quick Start"
codeprism visualize --activity examples/activity-stream.sample.jsonl --outdir .codeprism/visual
codeprism stats
codeprism gain
codeprism benchmark examples/benchmarks/basic-python --query report --out .codeprism/benchmarks/basic-python.json
codeprism benchmark-suite examples/benchmarks --out .codeprism/benchmarks/suite.json
codeprism benchmark-compare .codeprism/benchmarks/suite.json .codeprism/benchmarks/suite.json --out .codeprism/benchmarks/comparison.md
codeprism audit-session examples/codex-session.sample.jsonl
codeprism mcp --list-tools
codeprism setup --target project
codeprism doctor
```

## Architecture

- `src/contextopt/cli.py` — CLI entrypoint
- `src/contextopt/scanner.py` — file discovery and ignore handling
- `src/contextopt/extractors/` — language/document extractors
- `src/contextopt/graph.py` — graph model and SQLite persistence
- `src/contextopt/exporters/` — context pack exporters
- `integrations/` — Claude/Codex/Copilot integration templates
- `docs/` — design, roadmap, agent handoff
