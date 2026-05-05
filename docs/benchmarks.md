# CodePrism Benchmarks

CodePrism benchmark reports are local, reproducible estimates. They are useful for comparing source, context-pack, and focused-slice sizes, but they are not billing-grade token measurements and should not be read as guarantees for every repository.

Run the checked-in suite:

```bash
codeprism benchmark-suite examples/benchmarks --out .codeprism/benchmarks/suite.json
```

The command writes per-fixture JSON reports, a combined `suite.json`, and a Markdown summary at `.codeprism/benchmarks/suite.md`.

## Current Fixture Suite

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

## Fixture Groups

The `basic-*` fixtures are tiny language smoke tests. They keep Python, TypeScript, Java, and Kotlin extraction behavior visible.

The `medium-*` fixtures add a small amount of generated or noisy code around a focused task. They are still CI-sized, but they are closer to the cases CodePrism is meant to handle: identify the relevant slice and avoid dragging every nearby file into the agent prompt.
