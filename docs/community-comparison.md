# Community Comparison

This note tracks what CodePrism should learn from adjacent public agent-context projects without copying their positioning wholesale.

Latest review pass: 2026-05-05 UTC, based on public project documentation and GitHub READMEs. Popularity, release counts, and exact claims can drift quickly; keep future updates dated and source-backed.

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

## Current Landscape Snapshot

| Project | Primary lane | What CodePrism should learn | What CodePrism should avoid copying |
| --- | --- | --- | --- |
| [Graphify](https://github.com/safishamsi/graphify) | AI-assistant graph skill that writes `graph.html`, `GRAPH_REPORT.md`, and `graph.json`; supports many agent platforms, graph querying, hooks, and multimodal inputs. | Strong platform-specific install commands, direct graph query tools, graph-as-team-artifact workflow, and confidence labels for inferred relationships. | Do not blur local-first messaging: Graphify processes code locally, but docs/PDFs/images can go through the active assistant model. CodePrism should keep deterministic local parsing as the default public story. |
| [Serena](https://github.com/oraios/serena) | MCP toolkit that acts like an IDE for agents through symbol-level retrieval, references, editing, and refactoring backed by LSP or JetBrains. | Symbol-aware retrieval and refactoring are the strongest long-term north star for exact context. CodePrism should keep improving references and eventually add richer deterministic symbol relationships. | Do not compete as a full semantic editing/refactoring IDE yet. CodePrism's near-term win is inspectable context artifacts and lightweight preflight slices. |
| [GSD](https://github.com/gsd-build/get-shit-done) | Spec-driven project workflow system for Claude Code and other runtimes, with planning, execution, verification agents, settings, and worktree/commit controls. | Their strongest lesson is workflow persistence: docs, plans, verification state, and commits survive session resets. CodePrism should stay excellent at handoff artifacts that agents actually read. | Do not become a full project-management/metaprompt framework. CodePrism should complement GSD-style systems as the map/slice layer beneath them. |
| [jCodeMunch MCP](https://github.com/jgravelle/jcodemunch-mcp) | Tree-sitter-based structured code retrieval MCP with symbol queries, impact/risk queries, config hygiene, changed-symbol mapping, and git-aware analysis. | Precise symbol retrieval, changed-symbol context, risk/hotspot queries, and agent-config hygiene are directly relevant backlog areas. | Avoid unverified "most efficient" style positioning. CodePrism should keep measured, reproducible fixture claims and clearly labeled field notes. |
| [LeanCTX](https://github.com/yvgude/lean-ctx) | Context runtime with shell hooks, MCP server, read modes, pattern detection, and cached-read token savings. | Hooked reads, cached reads, many read modes, and low-friction binary distribution are useful patterns for agent adoption. | Avoid over-indexing the public pitch around headline savings such as "99%" unless CodePrism has reproducible, checked-in evidence for that exact scenario. |
| [CocoIndex Code](https://github.com/cocoindex-io/cocoindex-code) | AST-based semantic code search with local or cloud embeddings, incremental indexing, skills, and MCP. | The "install and go" story, incremental re-indexing, and semantic search UX are strong. A future CodePrism semantic mode should remain optional and clearly separate from deterministic mode. | Do not introduce embeddings as a default dependency. That would weaken CodePrism's lightweight, local-first, inspectable baseline. |
| [codesight](https://github.com/Houseofmvps/codesight) | One-command AI context generator that writes markdown context/wiki artifacts, agent config files, and MCP tools. | The wiki/index pattern is close to CodePrism's `.brief.md` direction: small session-start artifacts plus targeted topic pages. Its AI config generation also reinforces `setup` and `doctor`. | Do not replace graph-backed exact retrieval with a single static summary file. CodePrism should keep stable node IDs and source retrieval as differentiators. |
| [Caveman](https://github.com/JuliusBrussee/caveman) / prompt-compression skills | Output/input token compression through concise communication modes rather than codebase mapping. | Keep helper prompts short, operational, and behavior-changing. | Treat this as an adjacent layer, not a direct product competitor; terse prose does not solve code discovery or freshness. |

## What The Community Seems To Favor

1. **One obvious install path.**
   GSD, Graphify, CocoIndex Code, and codesight put the install path near the top and make the expected first command obvious. CodePrism should keep `codeprism setup` as the friendly path and leave `install-integrations` as the scriptable lower-level command.

2. **Agent-native adoption.**
   Tools that win do not just generate artifacts. They install skills, commands, MCP servers, hooks, or rules that make agents use the context layer automatically. Graphify and codesight both emphasize making the assistant read the generated artifact before broad file reads. CodePrism now has helper installs and an experimental MCP entrypoint; next it should document client setup and add resources/prompts.

3. **Visible proof of savings.**
   LeanCTX shows live gain and benchmark reports. jCodeMunch and Graphify publish token-reduction examples. CodePrism now has `codeprism gain`, `codeprism benchmark`, `codeprism benchmark-suite`, and `codeprism audit-session`; next it should add larger fixtures before making stronger public claims.

4. **Doctor commands.**
   Diagnostics and setup repair are part of onboarding in this category. CodePrism now has `codeprism doctor` and stale-map reporting in `codeprism gain`; next it should diagnose PATH, CLI version, stale skills, missing maps, and MCP configuration.

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

10. **Machine-readable proof artifacts.**
    Public benchmark claims get safer when release tooling emits manifests rather than only Markdown. CodePrism now writes `.codeprism/pre-release/manifest.json`; the next step is to consume that manifest in release checks and trend docs.

## CodePrism Positioning

CodePrism should not try to be a full spec-workflow system like GSD, a semantic editing IDE like Serena, or an embeddings-first search daemon like CocoIndex Code. Its strongest lane is:

> Local-first context slices for coding agents. Map once, prime the task, read less code.

The visual map is useful, but the public front should keep context saving as the product and visuals as the inspection/replay bonus.

## Competitive Priorities

1. **Make `setup` and `doctor` boringly reliable.**
   External tools win adoption by installing into the places agents already look. CodePrism should make Codex, Claude, Copilot, and MCP setup easy to verify and repair.

2. **Turn exact retrieval into a stronger differentiator.**
   Serena and jCodeMunch show the value of symbol-level context. CodePrism already has stable node IDs, `get`, `references`, and read modes; next it should improve call/reference extraction and staged-diff awareness.

3. **Keep proof honest and reproducible.**
   LeanCTX, jCodeMunch, CocoIndex Code, and codesight all publish strong savings claims. CodePrism should keep checked-in fixture averages separate from dated field notes and route every release through the proof manifest.

4. **Add larger, public, reproducible comparison fixtures before raising claims.**
   Field notes are useful, but public positioning should rest on fixtures or scripted runs that another maintainer can reproduce without private source or network services.

## Shipped And Backlog Pulled From This Review

- `codeprism setup`: friendly install and doctor flow.
- `scripts/pre_release_proof.py`: writes a Markdown proof packet plus `manifest.json` with check status and artifact paths.
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
- External comparison fixtures: add public, reproducible large-repo runs before converting field notes into stronger benchmark copy.
- Hook/read enforcement: evaluate a local hook or command wrapper that warns before broad raw reads when a fresh CodePrism map and slice exist.
- Symbol intelligence: prioritize changed-symbol mapping, call/reference extraction, and risk/hotspot queries over broad semantic summarization.
