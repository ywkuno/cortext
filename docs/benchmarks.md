# CodePrism Benchmarks

CodePrism benchmark reports are local, reproducible estimates. They are useful for comparing source, context-pack, graph, and focused-slice sizes, but they are not billing-grade token measurements and should not be read as guarantees for every repository.

The public benchmark story has two parts:

- **Fixture suite:** checked-in, reproducible, suitable for CI and release comparisons.
- **Field notes:** local alpha runs on larger real repositories, useful for product intuition but not treated as release guarantees.

Run the checked-in suite:

```bash
codeprism benchmark-suite examples/benchmarks --out .codeprism/benchmarks/suite.json
python scripts/render_benchmark_chart.py .codeprism/benchmarks/suite.json --out docs/assets/benchmark-snapshot.svg
```

The benchmark command writes per-fixture JSON reports, a combined `suite.json`, and a Markdown summary at `.codeprism/benchmarks/suite.md`. The chart renderer turns the suite JSON into `docs/assets/benchmark-snapshot.svg` for README and docs display.

To verify the checked-in chart is current without rewriting it:

```bash
python scripts/render_benchmark_chart.py .codeprism/benchmarks/suite.json --out docs/assets/benchmark-snapshot.svg --check
```

Compare two suite runs:

```bash
codeprism benchmark-compare previous-suite.json .codeprism/benchmarks/suite.json --out .codeprism/benchmarks/comparison.md
```

Add `--fail-on-regression --regression-threshold 5` when you want CI or a release script to fail if any matched fixture loses more than five percentage points of estimated source-to-slice savings.

For release review, use the maintainer helper:

```bash
python scripts/benchmark_trend.py --baseline-suite previous-suite.json
```

That local mode never calls GitHub. It runs the current suite, compares it to the supplied baseline, and writes `.codeprism/benchmark-trends/comparison.md`.

To compare against the latest successful public workflow artifact, install and authenticate the GitHub CLI, then omit `--baseline-suite`:

```bash
python scripts/benchmark_trend.py --repo kunolabs/codeprism --python-version 3.12
```

The artifact mode downloads `codeprism-benchmarks-py3.12`, finds its `suite.json`, runs the current local suite, and writes a Markdown trend report. This is an explicit maintainer workflow; normal CodePrism commands do not make network calls.

To collect a fuller local pre-release proof packet:

```bash
python scripts/pre_release_proof.py --baseline-suite previous-suite.json
```

This writes `.codeprism/pre-release/README.md`, a machine-readable `.codeprism/pre-release/manifest.json`, benchmark trend output, sample session audit output, test and lint logs, and a public hygiene scan. If no baseline suite is supplied, the benchmark trend compares the current suite against itself so the command remains fully offline by default.

## Current Fixture Suite

The current suite covers 8 fixtures across Python, TypeScript, Java, and Kotlin. Across all fixtures it maps 40 files, compares 15,291 estimated source tokens against 4,801 estimated focused-slice tokens, and reports a 68.75% average per-fixture source-to-slice reduction.

![CodePrism benchmark chart](assets/benchmark-snapshot.svg)

| Fixture | Files | Source tokens | Slice tokens | Source -> slice | Source -> context pack |
| --- | ---: | ---: | ---: | ---: | ---: |
| Basic Java | 5 | 1,126 | 524 | 53.46% | 0.00% |
| Basic Kotlin | 4 | 1,139 | 442 | 61.19% | 13.26% |
| Basic Python | 5 | 1,263 | 172 | 86.38% | 70.39% |
| Basic TypeScript | 5 | 1,073 | 264 | 75.40% | 21.06% |
| Medium Java Server | 6 | 2,538 | 956 | 62.33% | 14.81% |
| Medium Kotlin Android | 5 | 2,804 | 1,171 | 58.24% | 48.25% |
| Medium Python Service | 5 | 2,897 | 783 | 72.97% | 59.54% |
| Medium TypeScript App | 5 | 2,451 | 489 | 80.05% | 64.18% |

Summary:

- Fixtures: 8
- Average source-to-slice saving: 68.75%
- Minimum source-to-slice saving: 53.46%
- Maximum source-to-slice saving: 86.38%

## How To Read These Numbers

The checked-in fixtures are intentionally small so they can run quickly in CI. On tiny projects, graph metadata and slice headers can be a meaningful part of the output, so a context pack or slice can show little or no reduction even when the workflow is behaving correctly.

The real product loop is larger than this table: run `codeprism prime "<task>"`, read the compact brief, then use `query`, `get`, `references`, and `read --mode signatures/diff` before opening raw files. Large repositories and narrow tasks usually show stronger reductions because CodePrism can avoid generated files, repeated shell output, dependency folders, and unrelated source.

When README or release notes mention larger real-world reductions, keep those examples clearly labeled as field notes. Do not mix them into the reproducible fixture average unless the repository, fixture data, and commands are checked in.

## Fixture Groups

The `basic-*` fixtures are tiny language smoke tests. They keep Python, TypeScript, Java, and Kotlin extraction behavior visible.

The `medium-*` fixtures add a small amount of generated or noisy code around a focused task. They are still CI-sized, but they are closer to the cases CodePrism is meant to handle: identify the relevant slice and avoid dragging every nearby file into the agent prompt.

## CI Artifacts

The GitHub Actions smoke job uploads benchmark JSON and Markdown reports for each Python version as `codeprism-benchmarks-py<version>`. Download two artifacts and run `codeprism benchmark-compare`, or use `scripts/benchmark_trend.py`, when reviewing a performance-sensitive change or preparing release notes.
