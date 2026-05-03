# Activity Stream Schema

This schema is the MVP2 foundation for visual overlays and the MVP3 pixel-agent replay loop.
The source log format is newline-delimited JSON (`.jsonl`). `codeprism visualize --activity <file>` normalizes valid rows into `.contextopt/visual/activity-stream.json` and records warnings for malformed rows.

You can also normalize an activity stream without generating a viewer:

```bash
codeprism activity normalize examples/activity-stream.sample.jsonl --out .contextopt/activity-stream.json
```

For simple tool-event logs, CodePrism includes a conservative adapter example:

```bash
codeprism activity adapt-tool-log examples/tool-events.sample.jsonl --out .contextopt/activity-events.jsonl
```

The adapter accepts safe fields such as `agent`, `type`, `file`, `tokens`, and `duration_ms`, then emits CodePrism activity JSONL. It does not read private session logs or infer hidden context.

## Base fields

Recommended event fields:

- `ts` — ISO8601 timestamp
- `run_id` — unique run identifier
- `agent_id` — actor name or agent ID
- `event` — event type string
- `node_id` — optional stable node ID
- `from_node_id` — optional stable node ID where a replay movement starts
- `to_node_id` — optional stable node ID where a replay movement ends
- `path` — optional repo path
- `duration_ms` — optional event duration or animation hint
- `estimated_tokens` — optional local token estimate for the event
- `actual_tokens` — optional measured token count when an integration can provide it
- `status` — optional status such as `ok`, `passed`, `failed`, or `blocked`
- `severity` — optional severity such as `info`, `warn`, or `error`
- `meta` — freeform object

Only `event` is effectively required by the parser. Missing optional fields are normalized to empty strings or nulls so replay does not crash. Token fields are optional because CodePrism should never need access to private session logs; integrations can pass normalized counts when they already have safe data.

## Stable node ID examples

- Folder: `folder::src/contextopt`
- File: `file::src/contextopt/cli.py`
- Markdown doc: `doc::docs/visualization-plan.md`
- Function: `function::src/contextopt/cli.py::main`
- Method: `method::src/contextopt/graph.py::commit`
- Class: `class::src/contextopt/graph.py::GraphStore`
- Heading: `heading::README.md::Quick start`
- Route: `route::/users/:id`
- External module: `module::pathlib`

## Example event types

### `file_read`
```json
{"ts":"2026-05-03T02:00:00Z","run_id":"demo-1","agent_id":"codex","event":"file_read","node_id":"file::src/app.py","to_node_id":"file::src/app.py","path":"src/app.py","duration_ms":650,"estimated_tokens":420,"status":"ok","severity":"info","meta":{"reason":"task relevant"}}
```

### `file_write`
```json
{"ts":"2026-05-03T02:01:00Z","run_id":"demo-1","agent_id":"codex","event":"file_write","from_node_id":"file::src/app.py","to_node_id":"function::src/app.py::main","node_id":"function::src/app.py::main","path":"src/app.py","duration_ms":800,"estimated_tokens":180,"status":"ok","severity":"info","meta":{"diff_lines":12}}
```

### `context_pack_generated`
```json
{"ts":"2026-05-03T02:02:00Z","run_id":"demo-1","agent_id":"CodePrism","event":"context_pack_generated","estimated_tokens":1400,"actual_tokens":1280,"meta":{"node_count":22,"edge_count":37}}
```

### `test_run`
```json
{"ts":"2026-05-03T02:03:00Z","run_id":"demo-1","agent_id":"codex","event":"test_run","path":"tests/test_app.py","meta":{"status":"passed"}}
```

## Generated payload

The visualizer writes a normalized JSON payload:

- `events` — valid normalized rows
- `warnings` — malformed or non-object rows skipped during parsing
- `summary` — aggregate counts for the viewer HUD:
  - `event_count`
  - `agent_count`
  - `agents`
  - `estimated_tokens`
  - `actual_tokens`
  - `duration_ms`

The standalone `codeprism activity normalize` command writes the same payload shape, which keeps adapters simple and avoids reading private agent session logs directly.

Activity replay can be combined with context overlays by running `codeprism visualize --activity <activity.jsonl> --context <slice.json>`. Activity events show what was touched; context overlays show what was packed.

## Future fields

Potential additions:
- `target_path`
- `context_pack_id`
- `tool_name`
- `context_slice_id`

## Malformed rows

Malformed JSONL rows are skipped and reported in the generated `activity-stream.json` `warnings` array. Non-object JSON rows are also skipped. The viewer can still load and replay the valid events.
