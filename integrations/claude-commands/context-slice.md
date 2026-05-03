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

Then read the generated slice Markdown first. Use `codeprism get NODE_ID` for exact mapped source, and `codeprism read PATH --mode signatures` or `--mode diff` before opening whole raw files.
