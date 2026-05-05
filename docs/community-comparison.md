# Community Comparison

This note tracks what CodePrism should learn from adjacent public agent-context projects without copying their positioning wholesale.

## Repos Reviewed

- [gsd-build/get-shit-done](https://github.com/gsd-build/get-shit-done)
- [jgravelle/jcodemunch-mcp](https://github.com/jgravelle/jcodemunch-mcp)
- [yvgude/lean-ctx](https://github.com/yvgude/lean-ctx)
- [cocoindex-io/cocoindex-code](https://github.com/cocoindex-io/cocoindex-code)
- [Graphify](https://github.com/safishamsi/graphify)
- [oraios/serena](https://github.com/oraios/serena)
- [JuliusBrussee/caveman](https://github.com/JuliusBrussee/caveman)
- [Houseofmvps/codesight](https://github.com/Houseofmvps/codesight)
- [OpenWolf](https://openwolf.com/)
- [mattpocock/skills grill-me](https://github.com/mattpocock/skills)

## What The Community Seems To Favor

1. **One obvious install path.**
   GSD and CocoIndex Code put the install path near the top and make the expected first command obvious. CodePrism should keep `codeprism setup` as the friendly path and leave `install-integrations` as the scriptable lower-level command.

2. **Agent-native adoption.**
   Tools that win do not just generate artifacts. They install skills, commands, MCP servers, hooks, or rules that make agents use the context layer automatically. CodePrism now has helper installs and an experimental MCP entrypoint; next it should document client setup and add resources/prompts.

3. **Visible proof of savings.**
   LeanCTX shows live gain and benchmark reports. jCodeMunch and Graphify publish token-reduction examples. CodePrism now has `codeprism gain`, `codeprism benchmark`, `codeprism benchmark-suite`, and `codeprism audit-session`; next it should add larger fixtures before making stronger public claims.

4. **Doctor commands.**
   LeanCTX and CocoIndex Code both make diagnostics part of onboarding. CodePrism now has `codeprism doctor` and stale-map reporting in `codeprism gain`; next it should diagnose PATH, CLI version, stale skills, and missing maps.

5. **Exact retrieval, not only search.**
   jCodeMunch is compelling because an agent can fetch a symbol, outline, or compact bundle instead of opening whole files. CodePrism now has `codeprism get` and `codeprism read --mode`.

6. **Fresh indexes.**
   CocoIndex Code and Graphify emphasize incremental re-indexing. CodePrism already caches unchanged file extraction and reports stale maps; next it needs watch/hook options.

7. **Public polish.**
   Successful repos have a sharp first screen, badges, screenshots/GIFs, clear support links, and update/uninstall docs.

8. **Small resume artifacts.**
   LeanCTX's rule installs are idempotent, OpenWolf uses a persistent anatomy file before reads, and public subagent-overflow guidance favors file-based result passing instead of pulling long transcripts back into context. CodePrism should treat full slices as inspectable artifacts and provide a tiny slice brief for resumes, compacted conversations, and first reads.

9. **Less always-loaded prose.**
   Caveman and Grill Me are popular partly because they are simple skills with clear behavioral constraints. CodePrism helper text should be short, operational, and explicit about when not to run `prime`.

## CodePrism Positioning

CodePrism should not try to be a full spec-workflow system like GSD or a heavyweight semantic search daemon first. Its strongest lane is:

> Local-first context slices for coding agents. Map once, prime the task, read less code.

The visual map is useful, but the public front should keep context saving as the product and visuals as the inspection/replay bonus.

## Shipped And Backlog Pulled From This Review

- `codeprism setup`: friendly install and doctor flow.
- `codeprism doctor --json`: shareable diagnostics for agents and bug reports.
- `codeprism get NODE_ID`: exact source retrieval for a graph node.
- `codeprism read PATH --mode map|signatures|diff|full`: token-aware file read modes.
- `codeprism gain`: report estimated saved tokens from slices and map freshness.
- `codeprism uninstall-integrations`: safe cleanup.
- `codeprism mcp`: add resources/prompts and client setup docs.
- `codeprism benchmark-suite`: run reproducible cross-language fixtures and write a public Markdown summary table.
- `codeprism audit-session`: local Codex JSONL audit for adoption timing, raw reads, compaction risk, large outputs, and observed savings.
- `codeprism watch`: optional local refresh loop for active repos.
- Compaction-safe `.brief.md` beside each slice: small recovery artifact before the full Markdown slice.
- Public landing assets: short GIF, before/after token example, and cleaner viewer screenshot.
