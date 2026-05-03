from pathlib import Path
from contextopt.extractors.python import extract_python


def test_extract_python_symbols(tmp_path: Path):
    f = tmp_path / "sample.py"
    f.write_text(
        """import os

class Cat:
    def meow(self):
        pass

def run():
    pass
""",
        encoding="utf-8",
    )
    result = extract_python(f, "sample.py")
    names = {n.name for n in result.nodes}
    assert "Cat" in names
    assert "run" in names
    assert any(e.kind == "imports" and "os" in e.target for e in result.edges)
