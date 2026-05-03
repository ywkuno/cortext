# /context-slice

Create a focused Cortext slice before reading broad file trees.

Input: `$ARGUMENTS`

Run:

```bash
contextopt prime "$ARGUMENTS"
```

If there are local edits, staged changes, or new files, run:

```bash
contextopt prime "$ARGUMENTS" --changed
```

For a read-only target repo, route artifacts outside the repo:

```bash
contextopt prime "$ARGUMENTS" --root PATH_TO_REPO --artifact-dir PATH_TO_ARTIFACTS --readonly-root
```

Then read the generated slice Markdown first. Inspect raw files only after the slice identifies the likely relevant paths and symbols.
