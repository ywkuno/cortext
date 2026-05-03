# Public Launch Checklist

Use this checklist before making the repository public.

## Recommendation

Do not run `git init` again inside this repository. The current repo already has clean commits and an `origin` remote.

Recommended path:

1. Keep this repository as the source of truth.
2. Keep generated `.contextopt/` outputs ignored.
3. Push the current branch to the GitHub repo.
4. Verify GitHub Actions on the remote.

Only create a fresh orphan branch or new repository if you want to hide or squash local development history before public release.

## Preflight

```bash
git status --short --ignored
git log --oneline -8
pytest
ruff check .
contextopt init
contextopt map .
contextopt export --format json --out .contextopt/context-pack.json
contextopt activity adapt-tool-log examples/tool-events.sample.jsonl --out .contextopt/activity-events.jsonl
contextopt activity normalize examples/activity-stream.sample.jsonl --out .contextopt/activity-stream.json
contextopt slice main --out .contextopt/slices/main.md
contextopt visualize --activity examples/activity-stream.sample.jsonl --context .contextopt/slices/main.json --outdir .contextopt/visual
contextopt stats
```

Expected:

- tests pass
- Ruff passes
- generated files remain ignored
- viewer opens locally
- no personal paths or secrets are present in tracked files

## Hygiene Scan

```bash
git ls-files | rg "^\\.contextopt/"
rg -n "(token|secret|credential|private key)" -S . --glob "!.git/**" --glob "!.contextopt/**" --glob "!*.egg-info/**" --glob "!__pycache__/**"
rg -n "(local path|user profile|home directory)" -S . --glob "!.git/**" --glob "!.contextopt/**" --glob "!*.egg-info/**" --glob "!__pycache__/**"
```

Expected:

- no tracked `.contextopt/` files
- no obvious secret tokens
- no local personal filesystem paths in tracked files

## GitHub Setup

If the remote already exists:

```bash
git remote -v
git push -u origin master
```

If you want to use `main` before public launch:

```bash
git branch -m master main
git push -u origin main
```

Then set the default branch to `main` in GitHub repository settings.

Recommended GitHub repo metadata:

- Description: `Local-first codebase maps, context slices, and visual replay for AI coding agents.`
- Topics: `ai`, `agents`, `context`, `developer-tools`, `visualization`, `static-analysis`
- Website: leave blank until a docs/demo page exists

## GitHub Verification

After pushing:

```bash
gh run list --limit 5
gh run watch
```

Verify:

- GitHub Actions passes on the remote
- README screenshot renders
- license, contributing, and security policy are visible
- issue and pull request templates render

## Optional Clean-History Path

Use this only if you decide the development history should not be public.

```bash
git switch --orphan public-main
git add -A
git commit -m "Initial public release"
git branch -D master
git branch -m main
git remote set-url origin https://github.com/<owner>/<repo>.git
git push -u origin main
```

This rewrites the public story into one commit. It is cleaner for launch, but loses the useful internal progression already captured in the current history.
