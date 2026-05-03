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

2. Read the generated slice Markdown first. By default it is under `.contextopt/slices/`; with `--artifact-dir`, it is under that artifact directory.
3. Use exact retrieval for specific mapped nodes before opening whole raw files:

```bash
codeprism get NODE_ID
```

4. Open raw files only when the slice and exact node source are clearly insufficient.
5. For broader orientation, refresh the map and stats:

```bash
codeprism map .
codeprism stats
```

6. If CodePrism behavior seems stale, check the installed helpers:

```bash
codeprism doctor
```

7. Use the visual map as a bonus inspection layer, not the first step:

```bash
codeprism visualize --context .contextopt/slices/<slice>.json
```

## Rules

- Prefer deterministic context pack facts over guesses.
- If the map is stale, refresh it.
- Do not send private project files to external APIs.
- Ask for raw files only after consulting the slice, map, or `codeprism get` output.
- Treat token counts as estimates, not billing-grade measurements.
- Prefer `--changed` when there are local edits, staged changes, or new files.
- Use `--artifact-dir` and `--readonly-root` when the target repository must stay untouched.
