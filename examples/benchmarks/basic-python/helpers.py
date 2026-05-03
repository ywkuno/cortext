def build_report(name: str) -> str:
    notes = [
        "map first",
        "slice next",
        "read exact source only when needed",
    ] * 120
    return f"{name}: {len(notes)} context notes"
