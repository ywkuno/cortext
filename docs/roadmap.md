# CodePrism Roadmap

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
- `codeprism query` ranking improvements
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

- Lightweight `.codeprism/live-trace.jsonl` for CodePrism command events
- `codeprism visualize` auto-loads the local Live Trace when no `--activity` file is supplied
- `--artifact-dir` routes Live Trace outside read-only target repos
- Low-cost cyber pulse marker and dashed activity beams in the static viewer
- Richer JSONL activity stream with optional estimated and actual token counts
- Event replay timeline, event list, speed control, next, and reset
- Moving agent markers over known graph nodes
- Deterministic path interpolation between touched nodes
- Short-lived activity trails between replayed source and target nodes
- Replay HUD with event count, agent count, active event, and estimated tokens
- Standalone `codeprism activity normalize` command for safe JSONL-to-replay payloads
- Searchable event list for jumping to agents, event types, and paths
- Safe tool-event adapter example via `codeprism activity adapt-tool-log`
- Run and agent filters, jump-to-node, and touched-only replay map mode
- Context inclusion overlays
- Pixel renderer scaffold in `apps/pixel-brain`

## MVP4 — Token Optimization

- `codeprism stats` for source, graph, and context-pack token estimates
- `codeprism slice <path-or-symbol>` for targeted Markdown context packs
- `codeprism prime <task>` as the one-command agent preflight: map, estimate, slice, then read the slice brief first
- Prime and slice Markdown are capped to about 8K estimated tokens by default so the generated context artifact does not cause premature compaction
- Every slice gets a compact `.brief.md` recovery artifact so compacted conversations can resume without rereading the full slice or rerunning a broad prime
- Slice budgets above 16K, including uncapped output, require explicit `--allow-large-context`
- `codeprism prime <task> --changed` seeds context from changed, staged, and untracked Git files
- `codeprism prime <task> --artifact-dir <dir> --readonly-root` supports read-only repos and CI artifact routing
- `codeprism get <node-id>` prints exact source for a mapped file, doc, or symbol node
- `codeprism read <path> --mode map|signatures|diff|full` supports progressive, token-aware file reading
- `codeprism references <node-id>` reports incoming and outgoing graph references
- `codeprism gain` reports estimated saved tokens and stale-map status
- Context-consuming commands warn on stale maps; `--refresh` incrementally remaps first and `--strict-fresh` fails instead of reading stale graph state
- Map-writing commands use a local inspectable `context.lock` so concurrent agents do not rewrite the graph at the same time
- `codeprism watch . --once` refreshes only when stale; `codeprism watch .` provides a lightweight polling feedback loop for active sessions
- `codeprism onboard` and `codeprism memory` create inspectable local project memory
- `codeprism benchmark` writes reproducible local token-savings reports
- `codeprism benchmark-suite examples/benchmarks` runs the checked-in Python, TypeScript, Java, and Kotlin fixture set and writes JSON plus a Markdown summary table documented in `docs/benchmarks.md`
- `codeprism benchmark-compare` compares two suite reports and can fail automation when a fixture regresses beyond a chosen savings threshold
- CI uploads benchmark JSON and Markdown reports as artifacts for trend review
- `codeprism audit-session <session>` audits local Codex JSONL sessions for CodePrism adoption timing, raw reads, search commands, compaction mentions, large outputs, and observed savings
- `codeprism mcp --list-tools` exposes the experimental MCP tool surface; `codeprism mcp` runs the optional SDK-backed server
- `codeprism setup` installs/refreshes agent helpers and runs `codeprism doctor`
- `codeprism doctor` checks whether helper files are present and current
- Prime output includes source, full-context, slice, estimated saving, file count, symbol count, and edge count
- Prime output reports when the slice was capped and shows the uncapped estimate
- Slice JSON manifests for context-inclusion overlays
- Viewer compares slice tokens against full graph context estimate
- Viewer highlights context-included nodes
- Query-first workflow docs for Codex/Claude usage
- Local Codex/Claude skill installation so agents actually use slices before broad reads
- Java package/import/type/method extraction
- Broad deterministic fallback for common non-Python languages, with honest limitations
- Honest estimated token reporting rather than benchmark claims
- Next: rank slices by call graph signals, richer docs mentions, recent activity, and per-language ownership hints
- Next: add an optional CI freshness check that runs `codeprism watch . --once` plus `codeprism gain`
- Next: add staged-diff support to `codeprism read --mode diff`
- Next: improve read signatures with language-aware argument/type summaries where deterministic parsers support them
- Next: expand MCP resources/prompts and document client setup for Codex, Claude, and other MCP clients
- Next: add richer reference extraction using deterministic call/reference edges where available

## Phase 5 — Agent integrations

- Claude Skill packaging script
- Claude Code slash commands
- Codex workflow prompts
- Copilot instruction templates
- VS Code task definitions
- `codeprism install-integrations`
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
