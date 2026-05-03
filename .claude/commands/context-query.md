# /context-query

Use the existing CodePrism map to answer a targeted codebase question.

Input: `$ARGUMENTS`

Run:

```bash
codeprism prime "$ARGUMENTS"
```

For read-only target repos, use `codeprism prime "$ARGUMENTS" --root PATH_TO_REPO --artifact-dir PATH_TO_ARTIFACTS --readonly-root`.

Then read the generated slice Markdown. If a specific node ID is relevant, run `codeprism get NODE_ID` before opening whole raw files. Answer with file paths and line references where possible.
