# Benchmark Fixtures

These fixtures keep CodePrism's public token-saving claims reproducible.

Run the full suite:

```bash
codeprism benchmark-suite examples/benchmarks --out .codeprism/benchmarks/suite.json
```

The suite writes per-fixture JSON reports, a combined `suite.json`, and a Markdown table at `suite.md`.

Token counts are local estimates for comparison, not billing-grade measurements.
