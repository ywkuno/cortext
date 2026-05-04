# GitHub Copilot Instructions

This project uses CodePrism.

Before broad exploration, create a focused slice for the current task:

```bash
codeprism prime "topic or symbol"
```

When local edits already exist, prefer:

```bash
codeprism prime "topic or symbol" --changed
```

For a read-only target repo, route artifacts outside the repo:

```bash
codeprism prime "topic or symbol" --root PATH_TO_REPO --artifact-dir PATH_TO_ARTIFACTS --readonly-root
```

Use the generated `.codeprism/slices/*.md` file as the first source for project structure, important files, and symbol locations. Run `codeprism gain` when you need the estimated savings/freshness report. For a specific mapped node, prefer `codeprism references NODE_ID` and `codeprism get NODE_ID`. For a whole file, prefer `codeprism read PATH --mode signatures` or `--mode diff` before opening the full source. If a context command warns that the map is stale, use `--refresh`; use `--strict-fresh` when stale context should fail. Verify in raw files before changing code.

CodePrism writes a local `.codeprism/live-trace.jsonl` event stream for its own commands. `codeprism visualize --outdir .codeprism/visual` auto-loads that trace when present, which is useful for inspecting the context workflow without reading private agent session logs.
