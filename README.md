# CodePrism

[![Tests](https://github.com/ywkuno/codeprism/actions/workflows/tests.yml/badge.svg)](https://github.com/ywkuno/codeprism/actions/workflows/tests.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

Local-first context saving for AI coding agents.

CodePrism gives an agent a task-sized map before it reads your code. It scans files, symbols, imports, routes, docs, and hierarchy into a local graph, then writes focused Markdown slices for the work in front of you.

The goal is simple: **map first, slice next, read raw files only when they matter.**

![CodePrism brain map](docs/assets/cortext-brain-map.png)

## Three Commands

```bash
pip install -e ".[dev]"
codeprism setup
codeprism prime "server boot path"
codeprism gain
codeprism mcp --list-tools
```

`codeprism setup` installs Codex/Claude/Copilot helper files and verifies them with `codeprism doctor`. `codeprism prime` maps the repo, writes a focused slice, and prints estimated token savings. `codeprism gain` reports estimated savings again later and warns when the map is stale. `codeprism mcp --list-tools` shows the MCP tools available to agent clients.

The legacy `contextopt` command remains available for existing scripts while the public CLI moves to `codeprism`. Internal Python imports still use the `contextopt` package.

For external or read-only repositories:

```bash
codeprism prime "server boot path" --root PATH_TO_REPO --artifact-dir PATH_TO_ARTIFACTS --readonly-root
```

## Why It Exists

Agents waste context when they brute-read file trees, repeated shell output, generated folders, and source files that are only loosely related to the current task. CodePrism is the local preflight layer: it gives the agent a compact, inspectable starting point so the expensive reasoning window stays focused.

## What It Does

- Builds a local SQLite graph of your repository.
- Extracts deterministic structure from Python, Markdown, JavaScript/TypeScript, and Java files.
- Uses a broad static fallback for common languages such as C/C++, C#, Go, Rust, Ruby, PHP, Kotlin, Swift, shell, PowerShell, and Lua.
- Reuses file hashes so unchanged files are not rescanned.
- Runs `codeprism prime "<task>"` to map the repo and write a targeted slice in one step.
- Fetches exact mapped source with `codeprism get <node-id>` so agents can inspect one symbol or file before opening broader code.
- Reads files through token-aware modes with `codeprism read <path> --mode map|signatures|diff|full`.
- Shows graph references with `codeprism references <node-id>`.
- Estimates context size and creates targeted Markdown slices for focused work.
- Reports estimated saved tokens and stale-map status with `codeprism gain`.
- Writes local project memory with `codeprism onboard` and `codeprism memory`.
- Produces reproducible savings reports with `codeprism benchmark`.
- Routes generated artifacts outside a target repo with `--artifact-dir` and `--readonly-root`.
- Exports Markdown, JSON, DOT, and static browser visualizations.
- Generates stable graph data for tool integration and optional visual inspection.
- Replays JSONL activity streams over the graph with agent markers, trails, timeline controls, and token estimates.

## Status

CodePrism is alpha software. The current release is meant for local development workflows where you want a smaller, inspectable starting point before handing a codebase to an AI assistant.

The core loop is usable today:

- map a repository into a local SQLite graph
- estimate context size and generate focused slices
- check whether the graph is stale before trusting map output
- expose core context tools through an optional MCP server
- install and verify Codex/Claude/Copilot helpers that nudge agents toward slice-first exploration
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

MCP support uses the official Python MCP SDK and is optional:

```bash
pip install -e ".[mcp]"
codeprism mcp --list-tools
```

`codeprism init` creates `.contextopt/config.toml` for local settings. Generated `.contextopt/` files are ignored by Git; see `examples/contextopt.config.example.toml` for the default config shape.

## Quick Start

```bash
codeprism init
codeprism prime "main"
codeprism visualize --context .contextopt/slices/main.json --outdir .contextopt/visual
```

Read the generated `.contextopt/slices/main.md` before opening broad raw file trees. Open `.contextopt/visual/index.html` in a browser when you want the optional graph view.
See [docs/demo.md](docs/demo.md) for the full activity replay and context-overlay walkthrough.

For read-only checkouts or CI jobs, route generated artifacts outside the repository:

```bash
codeprism prime "server boot" --root PATH_TO_REPO --artifact-dir PATH_TO_ARTIFACTS --readonly-root
```

Use a project-specific temp or output directory for `PATH_TO_ARTIFACTS` on Windows, macOS, or Linux.

## Agent Install

Install local helper prompts and skills so Codex, Claude, and Copilot start with CodePrism before broad exploration:

```bash
codeprism setup
codeprism doctor
```

This copies project helpers into `.claude/commands/` and `.github/copilot-instructions.md`, and installs the CodePrism skill into local Codex and Claude skill folders. `codeprism doctor` reports whether those files are installed and current. Restart Codex/Claude after installing global skills.

## Activity Replay

CodePrism can normalize a JSONL event stream and replay touched nodes in the viewer:

```bash
codeprism activity adapt-tool-log examples/tool-events.sample.jsonl --out .contextopt/activity-events.jsonl
codeprism activity normalize examples/activity-stream.sample.jsonl --out .contextopt/activity-stream.json
codeprism visualize --activity examples/activity-stream.sample.jsonl --outdir .contextopt/visual
```

Activity rows can reference `node_id`, `from_node_id`, `to_node_id`, or `path`. Malformed rows are skipped and reported as warnings in the generated activity file.
Optional `estimated_tokens` and `actual_tokens` fields power the replay HUD without requiring CodePrism to read private agent session logs.
The viewer activity panel includes local event search, run/agent filters, jump-to-node, and a touched-only map mode.

## CLI Commands

| Command | Purpose |
| --- | --- |
| `codeprism init` | Create a local `.contextopt/config.toml` file. |
| `codeprism map .` | Scan the repo and update the SQLite graph. |
| `codeprism export --format md` | Export a Markdown context pack. |
| `codeprism export --format json` | Export stable graph JSON. |
| `codeprism export --format dot` | Export DOT graph data. |
| `codeprism prime "topic"` | Map the repo, write a focused slice, and print a savings report. |
| `codeprism prime "topic" --changed` | Seed the slice with changed, staged, and untracked Git files. |
| `codeprism prime "topic" --artifact-dir <dir> --readonly-root` | Write prime artifacts outside the target repo and refuse root writes. |
| `codeprism get <node-id>` | Print exact source for a mapped file, doc, or symbol node. |
| `codeprism references <node-id>` | Show incoming and outgoing graph references for a node. |
| `codeprism read <path> --mode map` | Print mapped nodes for a file without source bodies. |
| `codeprism read <path> --mode signatures` | Print mapped symbols/headings/routes without source bodies. |
| `codeprism read <path> --mode diff` | Print only the working-tree diff for one path. |
| `codeprism read <path> --mode full` | Explicitly print the full file. |
| `codeprism visualize` | Generate a static browser viewer. |
| `codeprism activity adapt-tool-log` | Convert simple safe tool-event JSONL into CodePrism activity JSONL. |
| `codeprism activity normalize` | Normalize safe JSONL activity events into replay JSON. |
| `codeprism query "topic"` | Rank relevant files and symbols. |
| `codeprism stats` | Estimate source, graph, and pack token sizes. |
| `codeprism gain` | Report estimated token savings and map freshness. |
| `codeprism slice <target>` | Export focused Markdown plus a JSON context overlay manifest. |
| `codeprism benchmark <root>` | Write a reproducible local token-savings report. |
| `codeprism onboard` | Write local project memory under `.contextopt/memory/`. |
| `codeprism memory list/read/write` | Manage inspectable local memory files. |
| `codeprism mcp --list-tools` | List optional MCP tools for agent clients. |
| `codeprism setup` | Install and verify agent helper files in one step. |
| `codeprism install-integrations` | Install local Codex/Claude/Copilot helper files. |
| `codeprism doctor` | Check whether installed helper files are present and current. |

## Token-Saving Workflow

Use CodePrism as a preflight step before broad code reading:

```bash
codeprism prime "billing webhook"
codeprism gain
codeprism read src/app.py --mode signatures
codeprism get function::src/app.py::billing_webhook
codeprism references function::src/app.py::billing_webhook
codeprism visualize --context .contextopt/slices/billing-webhook.json --outdir .contextopt/visual
```

That gives an assistant a smaller, inspectable starting point. The prime command maps the repo, writes Markdown for the assistant, writes a JSON manifest for the viewer, and prints source/full-context/slice token estimates plus estimated savings. The gain command repeats the savings report and warns if files changed after the last map. The read command lets an agent inspect file shape before bodies, and the get command uses stable node IDs from slices, query results, or graph JSON to return only the requested source span.

During active edits, seed the slice from Git changes:

```bash
codeprism prime "what I am changing" --changed
```

The assistant should read the slice first, then verify important details in raw source files before editing.

For a repository that should not receive generated files, use:

```bash
codeprism prime "what I need" --root PATH_TO_REPO --artifact-dir PATH_TO_ARTIFACTS --readonly-root
```

This writes `context.db`, Markdown slices, and JSON manifests under the artifact directory instead of `.contextopt/` in the target repo.

For an MCP client, install the optional extra and launch the local stdio server:

```bash
pip install -e ".[mcp]"
codeprism mcp --root PATH_TO_REPO
```

The MCP server currently exposes `prime`, `gain`, `query`, `read`, `get`, and `references`. It is intentionally local-first and does not call external APIs.

To create a local project memory file for future agent sessions:

```bash
codeprism onboard --notes "Build/test commands, project purpose, and safety notes."
codeprism memory read project
```

To reproduce token-saving examples:

```bash
codeprism benchmark examples/benchmarks/basic-python --query report --out .contextopt/benchmarks/basic-python.json
```

## Privacy Model

- No network calls are made by default.
- Generated artifacts live under `.contextopt/` by default, or under `--artifact-dir` when supplied.
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
codeprism map .
codeprism export --format json --out .contextopt/context-pack.json
codeprism read README.md --mode signatures
codeprism get "heading::README.md::Quick Start"
codeprism gain
codeprism visualize --activity examples/activity-stream.sample.jsonl --outdir .contextopt/visual
codeprism slice main --out .contextopt/slices/main.md
codeprism visualize --context .contextopt/slices/main.json --outdir .contextopt/visual
codeprism setup --target project
codeprism doctor
```

CI runs tests, Ruff, and a CLI smoke path across Python 3.10, 3.11, and 3.12.

## Roadmap

Near-term work is focused on improving slice ranking, adding git-diff-aware context, benchmark fixtures for measured token savings, and deepening static extraction without making the tool heavyweight. Visual polish is still planned, but context savings stay the main product. See `docs/roadmap.md` for the current plan.

## Support

If CodePrism saves you time or tokens, sponsorship helps fund parser coverage, MCP support, reproducible benchmarks, and public docs. GitHub funding is configured in `.github/FUNDING.yml`; Ko-fi can be enabled there once a public Ko-fi handle is configured.

## License

MIT. See `LICENSE`.
