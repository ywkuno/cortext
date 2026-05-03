# /context-query

Use the existing CodePrism map to answer a targeted codebase question.

Input: `$ARGUMENTS`

Run:

```bash
codeprism prime "$ARGUMENTS"
```

For read-only target repos, use `codeprism prime "$ARGUMENTS" --root PATH_TO_REPO --artifact-dir PATH_TO_ARTIFACTS --readonly-root`.

Then read the generated slice Markdown. If a specific node ID is relevant, run `codeprism get NODE_ID`. If a whole file might be needed, run `codeprism read PATH --mode signatures` or `codeprism read PATH --mode diff` before opening the full file. Answer with file paths and line references where possible.

If the task depends on whether the map is fresh or whether the slice actually saved context, run `codeprism gain`.
