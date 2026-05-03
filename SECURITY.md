# Security Policy

CodePrism is local-first and does not make network calls by default.

## Reporting Issues

Please do not include secrets, private source code, or sensitive logs in a public issue. If GitHub private vulnerability reporting is enabled for this repository, use that first. Otherwise, open a minimal public issue describing the affected area and ask for a private contact path.

## Supported Versions

The project is currently pre-1.0. Security fixes are made on the main development line.

## Handling Generated Data

CodePrism outputs may contain source paths, symbols, documentation headings, and other project metadata. Treat generated `.contextopt/` artifacts as project-sensitive unless you intentionally created them from a public repository.
