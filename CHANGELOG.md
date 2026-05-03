# Changelog

## Unreleased

- Repositioned Cortext around context saving and token optimization, with visualization documented as an optional inspection layer.
- Added `contextopt prime <task>` to map a repo, write a focused context slice, and print a savings report in one step.
- Added `contextopt prime <task> --changed` to seed slices from changed, staged, and untracked Git files.
- Improved slice ranking with tokenized/stemmed matching, local import expansion, changed-path seeds, and related test inclusion.
- Added `contextopt install-integrations` for local Codex, Claude, and Copilot helpers.
- Added project-level Claude commands, including `/context-slice`, and Copilot instructions for slice-first workflows.
- Added the Cortext public README, license, contribution guide, and security policy.
- Added mapper, context export, stable graph JSON, static visualization, activity replay, token stats, and targeted context slices.
- Added MVP2.5 visual clarity controls for clean overview, layers, focus mode, hover tooltips, and map fitting.
- Added MVP2.6 multi-column repo-tree layout with cluster-grid fallback.
- Added MVP2.7 semantic node roles, role filter, role legend, role colors, and role badges.
- Added MVP3 replay HUD, per-agent markers, activity trails, and token-aware activity summaries.
- Added `contextopt activity normalize` plus searchable activity event lists in the viewer.
- Added safe tool-event activity adapter plus run/agent filters, jump-to-node, and touched-only replay mode.
- Added slice JSON manifests and viewer context overlays for slice-vs-full context token estimates.
- Added public-readiness cleanup for generated `.contextopt/` files, example config, and CLI smoke coverage in CI.
- Added public demo documentation, README screenshot, and GitHub issue/PR templates.
- Added regression coverage for incremental mapping, visualization export, activity parsing, and token-efficiency helpers.
