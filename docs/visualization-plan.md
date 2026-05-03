# Visualization Plan

## Scope

- MVP1 is the mapper and context export layer.
- MVP2 is the visual brain map: stable graph JSON plus a local static viewer.
- MVP3 is animated pixel brain / agent replay on top of activity streams.
- MVP4 is token optimization: stats, slices, and query-first context workflows.

## Why visualize the map?

Most context-optimization tools stop at “compress repo into machine-readable output”.
That helps the AI, but not the human.

We want a **human-readable CodePrism brain map**:

- understand repo shape at a glance
- spot hotspots, giant files, isolated modules, and dependency tangles
- debug why the AI is reading certain files
- make the mapping feel trustworthy and inspectable

## Core UX goals

### 1. Interactive structure map
- zoom / pan
- drag nodes around
- click nodes to inspect details
- highlight direct neighbors for the selected node
- show incoming and outgoing edges in the selected-node panel
- filter by type (file / class / function / doc / route / API / test)
- search by path or symbol name

### 2. Multiple layouts
Phase 1 uses a simple grouped layout.
Future layouts:
- file tree layout
- force graph layout
- dependency DAG
- layered architecture view
- package/module cluster view

### 3. AI context overlay
The real power move:
- show which nodes were included in a context pack
- show which nodes the AI touched during a task
- heatmap the “most-read” or “most-referenced” files
- compare full repo token estimates against exported context slices

### 4. Human trust layer
Every node should be inspectable:
- source path
- line range
- extracted summary/metadata
- edges to neighbors
- why it was included in context

## Data model additions

Current graph model already supports nodes + edges.
For richer visualization we should add:

- stable node IDs: `folder::<path>`, `file::<path>`, `doc::<path>`, `function::<path>::<name>`, `class::<path>::<name>`, `method::<path>::<name>`, `heading::<path>::<name>`, `route::<route>`, `module::<name>`
- parent-child hierarchy edges:
  - folders contain files/docs
  - files/docs contain symbols/headings/routes
  - classes contain methods
- node weight / size metrics
- importance score
- change frequency score
- context hit count
- cluster ID / module ID
- optional file hash

## Recommended implementation phases

### Phase A — MVP2 reliable scaffold
- JSON export
- static HTML viewer
- drag / zoom / inspect / search / filter
- selected-node neighbor highlighting
- optional activity stream loading

### Phase B — MVP2.5 clarity
- clean overview by default
- layer toggles for structure, symbols, imports, modules, tests, activity, and labels
- selected-node focus mode
- hover tooltips
- label-density rules
- fit-to-visible-map behavior

### Phase C — MVP2.6 repo tree
- repo tree layout as the default
- multi-column grouping by top-level repo district
- cluster grid as a selectable alternate view
- symbols and imports as overlays instead of the base structure
- activity marker and replay controls independent of layout mode

### Phase D — MVP2.7 semantic roles
- classify nodes by semantic role in `meta.role`
- role filter and role legend
- role colors/badges for agent instructions, repo controls, packages, docs, tests, source, examples, generated/cache, and dependencies
- keep generated/cache/dependency-heavy areas collapsed or hidden by default

### Phase E — MVP3 replay
- event list, timeline, speed control, and reset
- lightweight marker movement with `requestAnimationFrame`
- event highlighting by `node_id`, `from_node_id`, `to_node_id`, or `path`
- one marker per `agent_id`
- short activity trails between replayed source and target nodes
- replay HUD with aggregate event, agent, duration, and token estimates
- searchable event list for jumping to matching agents, event types, and paths
- run and agent filters
- jump-to-node from the active event
- touched-only map mode for replay debugging
- no animation work when paused

### Phase F — MVP4 token loop
- `codeprism stats`
- `codeprism slice <path-or-symbol>`
- query-first docs for agent workflows
- slice JSON manifests loaded as `context-overlay.json`
- highlighted context-included nodes in the viewer
- slice token estimate compared against full graph context estimate

### Phase G — better graph intelligence
- explicit tree hierarchy
- dependency clustering
- hotspot sizing
- edge toggles

### Phase H — polished app
Build a real app under `apps/brain-viz`:
- React + TypeScript + Vite
- Cytoscape.js or Sigma.js
- side panels and search
- timeline scrubber
- context inclusion overlays

## Suggested tech choices

### Fastest to MVP
- export JSON from Python CLI
- render with static HTML + vanilla JS or D3

### Better product-grade path
- Python CLI backend
- React frontend
- websocket or file watcher for live refresh

## MVP acceptance criteria

- `codeprism visualize` generates a folder with a browser-openable viewer
- `codeprism visualize --activity examples/activity-stream.sample.jsonl` copies/normalizes activity data into the viewer folder
- viewer loads local graph JSON
- user can pan, zoom, drag, search, filter, highlight, and inspect nodes
- viewer can show the current activity event and highlight a touched node by `node_id` or `path`
- viewer can move a lightweight marker between `from_node_id` and `to_node_id`
- viewer handles at least a few thousand nodes without falling over
