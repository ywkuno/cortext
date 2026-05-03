# /context-query

Use the existing Cortext map to answer a targeted codebase question.

Input: `$ARGUMENTS`

Run:

```bash
contextopt prime "$ARGUMENTS"
```

Then read the generated `.contextopt/slices/*.md` file and inspect only the highest-relevance raw files if more detail is needed. Answer with file paths and line references where possible.
