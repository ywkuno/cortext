# /context-slice

Create a focused CodePrism slice before reading broad file trees.

Input: `$ARGUMENTS`

Run:

```bash
codeprism prime "$ARGUMENTS"
```

If there are local edits, staged changes, or new files, run:

```bash
codeprism prime "$ARGUMENTS" --changed
```

For a read-only target repo, route artifacts outside the repo:

```bash
codeprism prime "$ARGUMENTS" --root PATH_TO_REPO --artifact-dir PATH_TO_ARTIFACTS --readonly-root
```

Then read the generated slice brief first (`.codeprism/slices/<name>.brief.md`). Open the full slice only when the slice brief is insufficient. Slices are capped to about 8K estimated tokens by default; budgets above 16K require `--allow-large-context`. If the slice says it was capped, keep narrowing with `codeprism query`, `codeprism references NODE_ID`, `codeprism get NODE_ID`, and `codeprism read PATH --mode signatures` or `--mode diff` before opening whole raw files. Do not rerun a broad prime only because the conversation compacted. Run `codeprism gain` when you need the savings/freshness report. If the map may be stale, run `codeprism watch . --once` or use `--refresh` on the context command.
