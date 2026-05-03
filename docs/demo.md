# Cortext Demo

This walkthrough shows the public context-saving loop for Cortext on any local repository. The visual map is included as an inspection bonus; the main path is slice-first.

## 1. Install

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

## 2. Prime A Task

```bash
contextopt init
contextopt prime "main"
```

This creates a local `.contextopt/context.db` SQLite graph and a focused `.contextopt/slices/main.md` file. Generated `.contextopt/` files are local working artifacts and should not be committed.

During an edit session, seed the slice with changed, staged, and untracked Git files:

```bash
contextopt prime "current task" --changed
```

The command prints source, full-context, and slice token estimates plus an estimated saving percentage.

## 3. Review Token Estimates

```bash
contextopt stats
```

The stats command reports local estimated token counts for source, graph, and context-pack outputs. These are estimates for comparison, not benchmark claims.

## 4. Install Agent Helpers

```bash
contextopt install-integrations --target all --force
```

Restart Codex/Claude after installing global skills. The helpers tell agents to run `contextopt prime "<task>"` before broad file reads.

The prime/slice workflow writes:

- `.contextopt/slices/main.md` for an assistant-readable context slice
- `.contextopt/slices/main.json` for the viewer context overlay

## 5. Replay Activity

```bash
contextopt activity adapt-tool-log examples/tool-events.sample.jsonl --out .contextopt/activity-events.jsonl
contextopt activity normalize examples/activity-stream.sample.jsonl --out .contextopt/activity-stream.json
```

The adapter is intentionally simple and safe. It converts explicit tool-event rows into Cortext activity JSONL. It does not read private agent session logs.

## 6. Open The Optional Viewer

```bash
contextopt visualize \
  --activity examples/activity-stream.sample.jsonl \
  --context .contextopt/slices/main.json \
  --outdir .contextopt/visual
```

Open `.contextopt/visual/index.html` in a browser.

The viewer supports:

- repo-tree and cluster-grid layouts
- search, kind filter, role filter, and layer toggles
- selected-node inspection with incoming/outgoing edges
- activity replay with run/agent filters and touched-only mode
- context overlays that highlight included slice nodes and show slice-vs-full token estimates

## Screenshot

![Cortext brain map](assets/cortext-brain-map.png)
