# Cortext

[![Tests](https://github.com/ywkuno/cortext/actions/workflows/tests.yml/badge.svg)](https://github.com/ywkuno/cortext/actions/workflows/tests.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

Local-first codebase maps, context slices, and visual replay for AI coding agents.

Cortext turns a repository into an inspectable project graph before an assistant reads the whole tree. It maps files, symbols, imports, routes, docs, hierarchy, and activity events, then exports compact context packs that humans and agents can both inspect.

The goal is simple: map first, query next, read raw files only when they matter.

![Cortext brain map](docs/assets/cortext-brain-map.png)

## What It Does

- Builds a local SQLite graph of your repository.
- Extracts deterministic structure from Python, Markdown, and JavaScript/TypeScript files.
- Reuses file hashes so unchanged files are not rescanned.
- Exports Markdown, JSON, DOT, and static browser visualizations.
- Generates stable graph data for visual inspection and tool integration.
- Keeps the visual map readable with multi-column repo-tree layout, cluster-grid fallback, layer toggles, focus mode, and hover tooltips.
- Labels files by semantic role, including agent instructions, repo controls, packages, source, tests, docs, examples, generated files, and dependencies.
- Replays JSONL activity streams over the graph with agent markers, trails, timeline controls, and token estimates.
- Estimates context size and creates targeted Markdown slices for focused work.

## Status

Cortext is an early MVP, but the core loop is usable:

- MVP1 = mapper and context export.
- MVP2 = visual brain map.
- MVP3 = animated pixel brain / agent replay.
- MVP4 = token stats and targeted context slices.

Token counts are local estimates based on text length. They are useful for comparing full-source, graph, context-pack, and slice sizes, but they are not benchmark claims.

## Install From Source

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

`contextopt init` creates `.contextopt/config.toml` for local settings. Generated `.contextopt/` files are ignored by Git; see `examples/contextopt.config.example.toml` for the default config shape.

## Quick Start

```bash
contextopt init
contextopt map .
contextopt stats
contextopt query "main"
contextopt slice main --out .contextopt/slices/main.md
contextopt visualize --context .contextopt/slices/main.json --outdir .contextopt/visual
```

Open `.contextopt/visual/index.html` in a browser to inspect the generated brain map.
See [docs/demo.md](docs/demo.md) for the full activity replay and context-overlay walkthrough.

## Activity Replay

Cortext can normalize a JSONL event stream and replay touched nodes in the viewer:

```bash
contextopt activity adapt-tool-log examples/tool-events.sample.jsonl --out .contextopt/activity-events.jsonl
contextopt activity normalize examples/activity-stream.sample.jsonl --out .contextopt/activity-stream.json
contextopt visualize --activity examples/activity-stream.sample.jsonl --outdir .contextopt/visual
```

Activity rows can reference `node_id`, `from_node_id`, `to_node_id`, or `path`. Malformed rows are skipped and reported as warnings in the generated activity file.
Optional `estimated_tokens` and `actual_tokens` fields power the replay HUD without requiring Cortext to read private agent session logs.
The viewer activity panel includes local event search, run/agent filters, jump-to-node, and a touched-only map mode.

## CLI Commands

| Command | Purpose |
| --- | --- |
| `contextopt init` | Create a local `.contextopt/config.toml` file. |
| `contextopt map .` | Scan the repo and update the SQLite graph. |
| `contextopt export --format md` | Export a Markdown context pack. |
| `contextopt export --format json` | Export stable graph JSON. |
| `contextopt export --format dot` | Export DOT graph data. |
| `contextopt visualize` | Generate a static browser viewer. |
| `contextopt activity adapt-tool-log` | Convert simple safe tool-event JSONL into Cortext activity JSONL. |
| `contextopt activity normalize` | Normalize safe JSONL activity events into replay JSON. |
| `contextopt query "topic"` | Rank relevant files and symbols. |
| `contextopt stats` | Estimate source, graph, and pack token sizes. |
| `contextopt slice <target>` | Export focused Markdown plus a JSON context overlay manifest. |

## Token-Saving Workflow

Use Cortext as a preflight step before broad code reading:

```bash
contextopt map .
contextopt stats
contextopt query "billing webhook"
contextopt slice "billing webhook" --out .contextopt/slices/billing-webhook.md
contextopt visualize --context .contextopt/slices/billing-webhook.json --outdir .contextopt/visual
```

That gives an assistant a smaller, inspectable starting point. The slice command writes both Markdown for the assistant and a JSON manifest for the viewer. The viewer highlights included nodes and shows the slice estimate against the full graph context estimate. The assistant should still verify important details in raw source files before editing.

## Privacy Model

- No network calls are made by default.
- Generated artifacts live under `.contextopt/`.
- Outputs are inspectable text, JSON, DOT, HTML, or SQLite.
- Optional LLM summarization is intentionally out of scope for the default path.

## Project Layout

```text
src/contextopt/        Python package and CLI
src/contextopt/exporters/
src/contextopt/extractors/
apps/brain-viz/       Future browser app scaffold
apps/pixel-brain/     Future replay renderer scaffold
docs/                 Architecture, roadmap, and schemas
examples/             Sample project and activity stream
integrations/         Claude, Codex, and Copilot templates
tests/                Regression tests
```

## Development

```bash
pip install -e ".[dev]"
pytest
ruff check .
contextopt map .
contextopt export --format json --out .contextopt/context-pack.json
contextopt visualize --activity examples/activity-stream.sample.jsonl --outdir .contextopt/visual
contextopt slice main --out .contextopt/slices/main.md
contextopt visualize --context .contextopt/slices/main.json --outdir .contextopt/visual
```

CI runs tests, Ruff, and a CLI smoke path across Python 3.10, 3.11, and 3.12.

## Roadmap

Near-term work is focused on making the visual map more useful, improving slice ranking, and adding deeper static extraction without making the tool heavyweight. See `docs/roadmap.md` for the current plan.

## Public Launch

Use [docs/public-launch-checklist.md](docs/public-launch-checklist.md) before pushing or making the repository public.

## License

MIT. See `LICENSE`.
