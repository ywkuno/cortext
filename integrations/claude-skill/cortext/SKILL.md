---
name: codeprism
description: Use when working in a repository that has CodePrism installed, especially before large refactors, bug hunts, or codebase exploration. Helps assistants create focused context slices before reading broad file trees.
---

# CodePrism Skill

Use this skill to reduce token usage while working on large codebases.

CodePrism's main job is context saving and token optimization. The visual map is useful for inspection, but the default agent workflow should be query-first and slice-first.

## Workflow

1. Start with a task-oriented slice, not a broad file-tree scan:

```bash
codeprism prime "topic, file, symbol, or bug"
```

For work already in progress, include changed files:

```bash
codeprism prime "topic, file, symbol, or bug" --changed
```

For a read-only checkout or external target repo, route artifacts outside the repo:

```bash
codeprism prime "topic, file, symbol, or bug" --root PATH_TO_REPO --artifact-dir PATH_TO_ARTIFACTS --readonly-root
```

2. Read the generated slice Markdown first. By default it is under `.codeprism/slices/`; with `--artifact-dir`, it is under that artifact directory.
   CodePrism also writes a local Live Trace event to `.codeprism/live-trace.jsonl`, or to `<artifact-dir>/live-trace.jsonl` when `--artifact-dir` is used.
3. Use exact retrieval for specific mapped nodes before opening whole raw files:

```bash
codeprism get NODE_ID
codeprism references NODE_ID
```

4. Use progressive file reads before full files:

```bash
codeprism read PATH --mode map
codeprism read PATH --mode signatures
codeprism read PATH --mode diff
```

5. If a context command warns that the map is stale, refresh before trusting the graph:

```bash
codeprism read PATH --mode signatures --refresh
codeprism get NODE_ID --strict-fresh
```

6. Open full raw files only when the slice, exact node source, signatures, and diff are clearly insufficient.
7. For broader orientation, refresh the map and check the savings/freshness report:

```bash
codeprism map .
codeprism stats
codeprism gain
```

8. Use local project memory when the task needs durable handoff context:

```bash
codeprism onboard --notes "project purpose, build/test commands, and safety notes"
codeprism memory read project
```

9. If CodePrism behavior seems stale, check the installed helpers:

```bash
codeprism doctor
```

10. Use the visual map as a bonus inspection layer, not the first step:

```bash
codeprism visualize --context .codeprism/slices/<slice>.json
```

When `.codeprism/live-trace.jsonl` exists, `codeprism visualize` auto-loads it for replay. Use this to inspect what CodePrism commands touched without reading private agent session logs.

## Rules

- Prefer deterministic context pack facts over guesses.
- If the map is stale, refresh it.
- Prefer `--refresh` for normal stale-map recovery and `--strict-fresh` when stale context should fail the command.
- Use `codeprism gain` when you need to confirm estimated savings or map freshness.
- Use `codeprism references` before broad search when a mapped node is central to the task.
- Do not send private project files to external APIs.
- Ask for raw files only after consulting the slice, map, `codeprism get`, or `codeprism read --mode signatures/diff` output.
- Treat token counts as estimates, not billing-grade measurements.
- Prefer `--changed` when there are local edits, staged changes, or new files.
- Use `--artifact-dir` and `--readonly-root` when the target repository must stay untouched.
- Treat Live Trace as a local audit aid, not as proof of exact model billing tokens.
