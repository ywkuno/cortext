# Benchmark Fixtures

These fixtures keep CodePrism's public token-saving claims reproducible.

The `basic-*` fixtures are tiny parser and slicing smoke tests. The `medium-*` fixtures add generated or noisy files around a focused task so the suite can exercise more realistic source-to-slice behavior while still staying fast enough for CI.

Run the full suite:

```bash
codeprism benchmark-suite examples/benchmarks --out .codeprism/benchmarks/suite.json
```

The suite writes per-fixture JSON reports, a combined `suite.json`, and a Markdown table at `suite.md`. See [docs/benchmarks.md](../../docs/benchmarks.md) for the current public table and caveats.

Token counts are local estimates for comparison, not billing-grade measurements.
