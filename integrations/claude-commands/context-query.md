# /context-query

Use the existing Cortext map to answer a targeted codebase question.

Input: `$ARGUMENTS`

Run:

```bash
contextopt prime "$ARGUMENTS"
```

For read-only target repos, use `contextopt prime "$ARGUMENTS" --root PATH_TO_REPO --artifact-dir PATH_TO_ARTIFACTS --readonly-root`.

Then read the generated slice Markdown and inspect only the highest-relevance raw files if more detail is needed. Answer with file paths and line references where possible.
