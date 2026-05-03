# Cortext

[![Tests](https://github.com/ywkuno/cortext/actions/workflows/tests.yml/badge.svg)](https://github.com/ywkuno/cortext/actions/workflows/tests.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

Local-first context saving and token optimization for AI coding agents.

Cortext helps an assistant avoid reading the whole tree. It maps files, symbols, imports, routes, docs, and hierarchy into a local graph, then creates focused context slices for the task at hand.

The goal is simple: **map first, slice next, read raw files only when they matter.**

![Cortext brain map](docs/assets/cortext-brain-map.png)

## What It Does

- Builds a local SQLite graph of your repository.
- Extracts deterministic structure from Python, Markdown, and JavaScript/TypeScript files.
- Reuses file hashes so unchanged files are not rescanned.
- Runs `contextopt prime "<task>"` to map the repo and write a targeted slice in one step.
- Estimates context size and creates targeted Markdown slices for focused work.
- Exports Markdown, JSON, DOT, and static browser visualizations.
- Generates stable graph data for tool integration and optional visual inspection.
- Replays JSONL activity streams over the graph with agent markers, trails, timeline controls, and token estimates.

## Status

Cortext is alpha software. The current release is meant for local development workflows where you want a smaller, inspectable starting point before handing a codebase to an AI assistant.

The core loop is usable today:

- map a repository into a local SQLite graph
- estimate context size and generate focused slices
- install Codex/Claude/Copilot helpers that nudge agents toward slice-first exploration
- export Markdown, JSON, DOT, and static HTML views
- inspect/search/filter the visual map as a bonus layer
- replay safe JSONL activity events

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
contextopt prime "main"
contextopt visualize --context .contextopt/slices/main.json --outdir .contextopt/visual
```

Read the generated `.contextopt/slices/main.md` before opening broad raw file trees. Open `.contextopt/visual/index.html` in a browser when you want the optional graph view.
See [docs/demo.md](docs/demo.md) for the full activity replay and context-overlay walkthrough.

## Agent Install

Install local helper prompts and skills so Codex, Claude, and Copilot start with Cortext before broad exploration:

```bash
contextopt install-integrations --target all --force
```

This copies project helpers into `.claude/commands/` and `.github/copilot-instructions.md`, and installs the Cortext skill into local Codex and Claude skill folders. Restart Codex/Claude after installing global skills.

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
| `contextopt prime "topic"` | Map the repo, write a focused slice, and print a savings report. |
| `contextopt prime "topic" --changed` | Seed the slice with changed, staged, and untracked Git files. |
| `contextopt visualize` | Generate a static browser viewer. |
| `contextopt activity adapt-tool-log` | Convert simple safe tool-event JSONL into Cortext activity JSONL. |
| `contextopt activity normalize` | Normalize safe JSONL activity events into replay JSON. |
| `contextopt query "topic"` | Rank relevant files and symbols. |
| `contextopt stats` | Estimate source, graph, and pack token sizes. |
| `contextopt slice <target>` | Export focused Markdown plus a JSON context overlay manifest. |
| `contextopt install-integrations` | Install local Codex/Claude/Copilot helper files. |

## Token-Saving Workflow

Use Cortext as a preflight step before broad code reading:

```bash
contextopt prime "billing webhook"
contextopt visualize --context .contextopt/slices/billing-webhook.json --outdir .contextopt/visual
```

That gives an assistant a smaller, inspectable starting point. The prime command maps the repo, writes Markdown for the assistant, writes a JSON manifest for the viewer, and prints source/full-context/slice token estimates plus estimated savings.

During active edits, seed the slice from Git changes:

```bash
contextopt prime "what I am changing" --changed
```

The assistant should read the slice first, then verify important details in raw source files before editing.

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

Near-term work is focused on improving slice ranking, adding git-diff-aware context, measuring real token savings, and deepening static extraction without making the tool heavyweight. Visual polish is still planned, but context savings stay the main product. See `docs/roadmap.md` for the current plan.

## License

MIT. See `LICENSE`.
