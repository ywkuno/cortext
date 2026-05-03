# Architecture

## Problem

AI coding assistants waste context by repeatedly reading broad file trees. Large repos also hide important relationships: entrypoints, imports, call chains, routes, migrations, generated files, and where things live.

Cortext creates a durable project map that agents can query before reading raw files.

## Pipeline

```text
repo/files -> scanner -> extractors -> normalizer -> graph store -> ranker -> context pack exports -> AI integrations
```

## Components

### Scanner

Discovers files while respecting ignore patterns and size limits.

### Extractors

Deterministic parsers collect symbols and relationships.

Initial extractors:

- Python: stdlib `ast`
- Java: deterministic package/import/type/method fallback
- JavaScript/TypeScript: regex fallback in starter; upgrade to Tree-sitter later
- Markdown: heading map and links
- Generic code fallback: common symbols/imports for C/C++, C#, Go, Rust, Ruby, PHP, Kotlin, Swift, shell, PowerShell, Lua, and similar files
- Unknown text: file metadata only

### Graph store

SQLite tables:

- `nodes`: files, symbols, modules, routes, documents
- `edges`: contains, imports, calls, links, defines
- `runs`: scan metadata

### Context pack

A compact Markdown export with project overview, important files, symbols, edges, docs headings, and agent notes.

## Trust model

The default path is local-only. LLM summarization is optional and must be opt-in. Deterministic facts and generated summaries should be stored separately.

## Token strategy

1. Map first.
2. Query the map.
3. Read only high-relevance files.
4. Export a small context pack.
5. Let the agent request deeper slices when needed.
