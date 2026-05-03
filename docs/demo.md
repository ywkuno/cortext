# CodePrism Demo

This walkthrough shows the public context-saving loop for CodePrism on any local repository. The visual map is included as an inspection bonus; the main path is slice-first.

## 1. Install

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

## 2. Prime A Task

```bash
codeprism init
codeprism prime "main"
```

This creates a local `.contextopt/context.db` SQLite graph and a focused `.contextopt/slices/main.md` file. Generated `.contextopt/` files are local working artifacts and should not be committed.

During an edit session, seed the slice with changed, staged, and untracked Git files:

```bash
codeprism prime "current task" --changed
```

The command prints source, full-context, and slice token estimates plus an estimated saving percentage.

For a read-only checkout or a CI smoke run, keep artifacts outside the target repo:

```bash
codeprism prime "current task" --root PATH_TO_REPO --artifact-dir PATH_TO_ARTIFACTS --readonly-root
```

Replace `PATH_TO_REPO` and `PATH_TO_ARTIFACTS` with normal project and output paths for your machine. With `--readonly-root`, CodePrism refuses to write generated artifacts under `--root`.

## 3. Review Token Estimates

```bash
codeprism stats
```

The stats command reports local estimated token counts for source, graph, and context-pack outputs. These are estimates for comparison, not benchmark claims.

## 4. Install Agent Helpers

```bash
codeprism setup
codeprism doctor
```

Restart Codex/Claude after installing global skills. The helpers tell agents to run `codeprism prime "<task>"` before broad file reads.

The prime/slice workflow writes:

- `.contextopt/slices/main.md` for an assistant-readable context slice
- `.contextopt/slices/main.json` for the viewer context overlay

Read progressively instead of opening whole files by default:

```bash
codeprism read src/app.py --mode map
codeprism read src/app.py --mode signatures
codeprism read src/app.py --mode diff
```

Fetch exact source for a mapped node before opening whole files:

```bash
codeprism get function::src/app.py::main
```

Use `--mode full` only when the cheaper map, signatures, diff, slice, or exact node output is insufficient. The get command prints only the mapped source span for that node, with line and token estimate metadata.

## 5. Replay Activity

```bash
codeprism activity adapt-tool-log examples/tool-events.sample.jsonl --out .contextopt/activity-events.jsonl
codeprism activity normalize examples/activity-stream.sample.jsonl --out .contextopt/activity-stream.json
```

The adapter is intentionally simple and safe. It converts explicit tool-event rows into CodePrism activity JSONL. It does not read private agent session logs.

## 6. Open The Optional Viewer

```bash
codeprism visualize \
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

![CodePrism brain map](assets/cortext-brain-map.png)
