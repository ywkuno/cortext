from __future__ import annotations
from pathlib import Path

from contextopt.integrations import install_integrations


def main() -> int:
    result = install_integrations(root=Path.cwd(), target="project", force=True)
    print(
        f"installed {result['planned']} project integration files "
        f"({result['copied']} copied, {result['skipped']} skipped)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
