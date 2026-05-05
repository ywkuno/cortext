# Codex Prompt: Build CodePrism

You are working on CodePrism, a local-first repo mapping tool for AI assistants.

Start by running tests and CLI smoke commands. Then implement the next roadmap item from `docs/roadmap.md`.

Core principles: local-first, deterministic first, inspectable outputs, token savings through maps and slices, good Windows support, no exaggerated benchmark claims.

Use `codeprism prime "<task>" --changed` before broad exploration, then read the generated slice brief first (`.codeprism/slices/<name>.brief.md`). Open the full slice only when the slice brief is insufficient. Keep the query narrow; slices are capped to about 8K estimated tokens by default, and budgets above 16K fail unless `--allow-large-context` is supplied. High `--limit` / `--max-tokens` values can erase the savings. If the slice was capped, use `codeprism query`, `codeprism get`, `codeprism references`, or `codeprism read --mode signatures/diff` instead of dumping more context into chat. Do not rerun a broad prime only because the conversation compacted. Report current state from the existing brief and continue with targeted reads. If a context command warns that the map is stale, use `--refresh`; use `codeprism watch . --once` when you want to refresh only if needed; use `--strict-fresh` when stale context should fail. Map refreshes use a local `context.lock` and exit cleanly if another agent is mapping. CodePrism appends local command events to `.codeprism/live-trace.jsonl`; `codeprism visualize --outdir .codeprism/visual` can replay that trace as a lightweight inspection layer.

Suggested first improvement: implement incremental hashing so unchanged files are not rescanned.
