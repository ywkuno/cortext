# Cortext Roadmap

## Milestone names

- MVP1 = mapper and context export.
- MVP2 = visual brain map.
- MVP3 = animated pixel brain / agent replay.
- MVP4 = token optimization and targeted context slices.

Context saving is the main product direction. Visuals are the inspection and gamified replay layer, not the primary value claim.

## Phase 0 — Starter scaffold

- CLI skeleton
- Scanner
- SQLite graph
- Python extractor
- Markdown exporter
- Claude/Codex/Copilot integration templates

## MVP1 — Mapper and Context Export

- Robust ignore handling
- Incremental cache using file hashes
- Better JS/TS parsing
- Next.js route detector
- Import graph visualization export
- `contextopt query` ranking improvements
- Context pack size budgets

## MVP2 — Visual Brain Map

- JSON export
- Stable graph JSON schema
- Stable node IDs across repeated map runs
- Parent-child hierarchy edges
- Generated static HTML viewer
- Pan / zoom / drag / search / filter / inspect
- Selected-node direct-neighbor highlighting
- Incoming and outgoing edge lists in the selected-node panel
- Optional JSONL activity stream normalization and basic replay
- File-clustered tree-like layout
- Browser app scaffold in `apps/brain-viz`

## MVP2.5 — Visual Clarity Pass

- Default clean overview that hides external modules, imports, and symbol-level detail.
- Layer toggles for structure, symbols, imports, external modules, tests, activity, and labels.
- Focus mode for inspecting the selected node plus its direct neighborhood.
- Hover tooltips for quick node inspection.
- Label-density rules so large maps do not turn into text soup.
- Real fit-to-visible-map behavior.

## MVP2.6 — Repo Tree Layout

- Repo tree is the default visual layout, matching the folder hierarchy users expect.
- The repo tree splits top-level folders into multiple columns so large projects do not become one tall spine.
- Cluster grid remains available as an alternate layout mode.
- Structure stays the base map; imports, symbols, tests, and modules remain optional overlays.
- Activity replay rides on top of either layout.

## MVP2.7 — Semantic Roles / Repo Legend

- Nodes keep their technical `kind`, and also get a semantic `meta.role`.
- Roles include agent instructions, repo controls, packages, source, tests, docs, examples, generated/cache, dependencies, and project files.
- Viewer role filter and role legend make special files easier to spot.
- Role colors and badges distinguish AI-facing docs, Git/repo policy, package files, and dependencies without using red for normal control files.
- Generated/ignored/dependency-heavy areas should stay collapsed or hidden by default; future work can add cheap ghost nodes with counts.

## MVP3 — Animated Pixel Brain / Agent Replay

- Richer JSONL activity stream with optional estimated and actual token counts
- Event replay timeline, event list, speed control, next, and reset
- Moving agent markers over known graph nodes
- Deterministic path interpolation between touched nodes
- Short-lived activity trails between replayed source and target nodes
- Replay HUD with event count, agent count, active event, and estimated tokens
- Standalone `contextopt activity normalize` command for safe JSONL-to-replay payloads
- Searchable event list for jumping to agents, event types, and paths
- Safe tool-event adapter example via `contextopt activity adapt-tool-log`
- Run and agent filters, jump-to-node, and touched-only replay map mode
- Context inclusion overlays
- Pixel renderer scaffold in `apps/pixel-brain`

## MVP4 — Token Optimization

- `contextopt stats` for source, graph, and context-pack token estimates
- `contextopt slice <path-or-symbol>` for targeted Markdown context packs
- `contextopt prime <task>` as the one-command agent preflight: map, estimate, slice, then read the slice first
- Slice JSON manifests for context-inclusion overlays
- Viewer compares slice tokens against full graph context estimate
- Viewer highlights context-included nodes
- Query-first workflow docs for Codex/Claude usage
- Local Codex/Claude skill installation so agents actually use slices before broad reads
- Honest estimated token reporting rather than benchmark claims
- Next: rank slices by imports, changed files, docs mentions, call graph signals, and recent activity
- Next: benchmark Cortext slices against full-source packs and other repo-packing tools using reproducible fixtures

## Phase 5 — Agent integrations

- Claude Skill packaging script
- Claude Code slash commands
- Codex workflow prompts
- Copilot instruction templates
- VS Code task definitions
- `contextopt install-integrations`
- Project command for slice-first work: `/context-slice`

## Phase 6 — Advanced graph intelligence

- Tree-sitter support
- Call graph for supported languages
- Symbol rename tracking
- Git diff-aware context updates
- Risk hotspots: huge files, circular deps, stale docs
- Optional local LLM summaries via Ollama

## Phase 7 — Project OS integration

- Agent task queue
- Context snapshots per issue
- before/after graph diff for PRs
- CI job that checks context pack freshness
- Web UI or Tauri desktop app
