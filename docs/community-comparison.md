# Community Comparison

This note tracks what CodePrism should learn from adjacent public agent-context projects without copying their positioning wholesale.

## Repos Reviewed

- [gsd-build/get-shit-done](https://github.com/gsd-build/get-shit-done)
- [jgravelle/jcodemunch-mcp](https://github.com/jgravelle/jcodemunch-mcp)
- [yvgude/lean-ctx](https://github.com/yvgude/lean-ctx)
- [cocoindex-io/cocoindex-code](https://github.com/cocoindex-io/cocoindex-code)
- [Graphify](https://github.com/safishamsi/graphify)

## What The Community Seems To Favor

1. **One obvious install path.**
   GSD and CocoIndex Code put the install path near the top and make the expected first command obvious. CodePrism should keep `codeprism setup` as the friendly path and leave `install-integrations` as the scriptable lower-level command.

2. **Agent-native adoption.**
   Tools that win do not just generate artifacts. They install skills, commands, MCP servers, hooks, or rules that make agents use the context layer automatically. CodePrism should keep improving Codex/Claude/Copilot helpers and add MCP next.

3. **Visible proof of savings.**
   LeanCTX shows live gain and benchmark reports. jCodeMunch and Graphify publish token-reduction examples. CodePrism should add reproducible benchmark fixtures before making stronger public claims.

4. **Doctor commands.**
   LeanCTX and CocoIndex Code both make diagnostics part of onboarding. CodePrism now has `codeprism doctor`; next it should diagnose PATH, CLI version, stale skills, missing maps, and stale maps.

5. **Exact retrieval, not only search.**
   jCodeMunch is compelling because an agent can fetch a symbol, outline, or compact bundle instead of opening whole files. CodePrism should add `codeprism get` and `codeprism read --mode`.

6. **Fresh indexes.**
   CocoIndex Code and Graphify emphasize incremental re-indexing. CodePrism already caches unchanged file extraction; next it needs clearer stale-map checks and watch/hook options.

7. **Public polish.**
   Successful repos have a sharp first screen, badges, screenshots/GIFs, a clear support channel, update/uninstall docs, and sponsor plumbing.

## CodePrism Positioning

CodePrism should not try to be a full spec-workflow system like GSD or a heavyweight semantic search daemon first. Its strongest lane is:

> Local-first context slices for coding agents. Map once, prime the task, read less code.

The visual map is useful, but the public front should keep context saving as the product and visuals as the inspection/replay bonus.

## Backlog Pulled From This Review

- `codeprism setup`: friendly install and doctor flow.
- `codeprism doctor --json`: shareable diagnostics for agents and bug reports.
- `codeprism uninstall-integrations`: safe cleanup.
- `codeprism get NODE_ID`: exact source retrieval for a graph node.
- `codeprism read PATH --mode map|signatures|diff|full`: token-aware file read modes.
- `codeprism mcp`: expose prime/query/slice/get/read/stats as MCP tools.
- `codeprism gain`: report estimated saved tokens from slices and cache reuse.
- `codeprism benchmark fixtures/`: reproducible token-saving examples.
- `codeprism watch`: optional local refresh loop for active repos.
- Public landing assets: short GIF, before/after token example, and cleaner viewer screenshot.
