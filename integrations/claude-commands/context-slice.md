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

Then read the generated `.contextopt/slices/*.md` file first. Inspect raw files only after the slice identifies the likely relevant paths and symbols.
