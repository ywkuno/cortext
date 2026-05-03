---
name: cortext
description: Use when working in a repository that has Cortext installed, especially before large refactors, bug hunts, or codebase exploration. Helps assistants create focused context slices before reading broad file trees.
---

# Cortext Skill

Use this skill to reduce token usage while working on large codebases.

Cortext's main job is context saving and token optimization. The visual map is useful for inspection, but the default agent workflow should be query-first and slice-first.

## Workflow

1. Start with a task-oriented slice, not a broad file-tree scan:

```bash
contextopt prime "topic, file, symbol, or bug"
```

For work already in progress, include changed files:

```bash
contextopt prime "topic, file, symbol, or bug" --changed
```

For a read-only checkout or external target repo, route artifacts outside the repo:

```bash
contextopt prime "topic, file, symbol, or bug" --root PATH_TO_REPO --artifact-dir PATH_TO_ARTIFACTS --readonly-root
```

2. Read the generated slice Markdown first. By default it is under `.contextopt/slices/`; with `--artifact-dir`, it is under that artifact directory.
3. Open only the raw files named in the slice unless the slice is clearly insufficient.
4. For broader orientation, refresh the map and stats:

```bash
contextopt map .
contextopt stats
```

5. Use the visual map as a bonus inspection layer, not the first step:

```bash
contextopt visualize --context .contextopt/slices/<slice>.json
```

## Rules

- Prefer deterministic context pack facts over guesses.
- If the map is stale, refresh it.
- Do not send private project files to external APIs.
- Ask for raw files only after consulting the slice or map.
- Treat token counts as estimates, not billing-grade measurements.
- Prefer `--changed` when there are local edits, staged changes, or new files.
- Use `--artifact-dir` and `--readonly-root` when the target repository must stay untouched.
