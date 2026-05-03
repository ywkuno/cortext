# GitHub Copilot Instructions

This project uses CodePrism.

Before broad exploration, create a focused slice for the current task:

```bash
codeprism prime "topic or symbol"
```

When local edits already exist, prefer:

```bash
codeprism prime "topic or symbol" --changed
```

For a read-only target repo, route artifacts outside the repo:

```bash
codeprism prime "topic or symbol" --root PATH_TO_REPO --artifact-dir PATH_TO_ARTIFACTS --readonly-root
```

Use the generated `.contextopt/slices/*.md` file as the first source for project structure, important files, and symbol locations. For a specific mapped node, prefer `codeprism get NODE_ID` before opening whole raw files. Verify in raw files before changing code.
