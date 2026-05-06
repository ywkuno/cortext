# Release Guide

This guide keeps CodePrism releases consistent, public-safe, and honest about token savings.

## Release Principles

- Keep CodePrism local-first by default.
- Treat benchmark numbers as local estimates for comparison, not billing-grade measurements.
- Publish proof artifacts from the public-safe checkout only.
- Do not paste private source, local usernames, local drive paths, session logs, or customer/project names into release notes.
- Prefer measured wording over viral claims.

## Pre-Release Checklist

Start from a clean checkout:

```bash
git status --short --branch
pip install -e ".[dev]"
```

Generate a benchmark baseline if you do not already have one:

```bash
codeprism benchmark-suite examples/benchmarks --out .codeprism/benchmarks/suite.json
```

Build the proof packet:

```bash
python scripts/pre_release_proof.py --baseline-suite .codeprism/benchmarks/suite.json
```

When comparing against an older suite report, replace `.codeprism/benchmarks/suite.json` with the older `suite.json`.

The proof packet is written to `.codeprism/pre-release/` and includes:

- benchmark suite output
- benchmark trend comparison
- sample `audit-session` output
- pytest log
- Ruff log
- public hygiene scan
- `manifest.json`, a machine-readable summary of checks and artifact paths for release automation

## External Field-Note Context (Optional)

For release context only, we also track local field-note comparisons against the public repo set in `examples/field-notes/public-repos.json`.

Latest execution (2026-05-06 UTC): all 7 targets passed.

```bash
python scripts/run_field_notes.py --config examples/field-notes/public-repos.json --repos-root external --fail-on-missing
```

- Graphify
- Serena
- GSD
- jCodeMunch MCP
- LeanCTX
- CocoIndex Code
- codesight

All seven completed with non-empty slices under the default `--max-tokens 8000` budget. Treat this as product-intuition context, and keep this evidence separate from reproducible fixture claims: `.codeprism/field-notes/summary.md`.

## Optional Artifact Baseline

If you want to compare the local checkout against the latest successful public workflow artifact, install and authenticate the GitHub CLI, then run:

```bash
python scripts/benchmark_trend.py --repo kunolabs/codeprism --python-version 3.12
```

This is an explicit maintainer workflow. Normal CodePrism commands do not make network calls.

## Release Notes

Use `.github/RELEASE_TEMPLATE.md` as the release body starting point. Keep the release notes focused on user-visible behavior:

- what changed
- how the token-saving workflow is affected
- what was verified
- benchmark evidence, with caveats
- upgrade notes
- known limitations

GitHub generated release notes use `.github/release.yml` to group pull requests by category. Edit the generated notes before publishing so the final text stays clear and measured.

If README benchmark copy changes, regenerate the fixture suite first and keep the README snapshot aligned with `docs/benchmarks.md`. Larger real-repo examples may appear as field notes only when they are anonymized and clearly separated from reproducible fixture results.

When fixture numbers change, regenerate both the Markdown table and SVG chart:

```bash
codeprism benchmark-suite examples/benchmarks --out .codeprism/benchmarks/suite.json
python scripts/render_benchmark_chart.py .codeprism/benchmarks/suite.json --out docs/assets/benchmark-snapshot.svg
python scripts/render_benchmark_chart.py .codeprism/benchmarks/suite.json --out docs/assets/benchmark-snapshot.svg --check
```

## Public Mirror Flow

This repo uses two fronts:

- `origin` = private canonical repo for daily development (`kunolabs/cortext-lab`)
- `public` = mirror repo for public release visibility (`kunolabs/codeprism`)

Recommended flow for a public-safe release:

1. Confirm the branch is release-ready and has passed the local release checks.
2. Confirm no private-only files/paths need filtering.
3. Mirror `master` directly:

```bash
git push public master
```

4. Mirror release tags with the code:

```bash
git push public --tags
```

If you later need filtering, publish to a dedicated release branch and apply a scripted filter step before pushing to `public`. Until then, this direct mirror keeps public history intact and keeps `origin` as the private source of truth.

### Public branch canonicalization status

On 2026-05-06, the public repository default branch is set to `master`, and `public/main` was archived to `main-archive-2026-05-06` and removed to keep only the canonical public stream.

If `public/main` is still in use on the public platform, keep it as a compatibility or archived branch and point the public default branch to `master` so CI and release checks run from the canonical stream.

## Public Hygiene

Before publishing, confirm the proof packet hygiene scan passed:

```bash
Get-Content .codeprism/pre-release/hygiene-scan.md
```

The scan checks tracked public-facing files for known private release markers. If it fails, remove the sensitive text first and regenerate the proof packet.

## Publishing

1. Confirm `pytest`, `ruff check .`, and the proof packet passed.
2. Confirm the public repository is the target for the release.
3. Create a tag using the chosen version.
4. Draft the GitHub release using `.github/RELEASE_TEMPLATE.md`.
5. Paste the relevant benchmark summary from `.codeprism/pre-release/benchmark-trends/comparison.md`.
6. Publish only after reviewing the final rendered release body.

## After Release

- Check the public Actions run.
- Download benchmark artifacts when you need a durable baseline for the next release.
- Keep `docs/benchmarks.md` and README benchmark summaries in sync when fixture results intentionally change.
