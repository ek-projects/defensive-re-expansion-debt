from __future__ import annotations

import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
README = ROOT / "README.md"
LICENSE = ROOT / "LICENSE.md"
MAX_README_WORDS = 1000
MAX_FIGURES_OR_TABLES = 2
FORBIDDEN_SUFFIXES = {".csv", ".jsonl", ".parquet", ".zip", ".mp4", ".mov", ".m4a", ".wav"}


def tracked_files() -> list[Path]:
    proc = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=ROOT,
        check=True,
        capture_output=True,
    )
    return [Path(p.decode()) for p in proc.stdout.split(b"\0") if p]


def readme_counts(text: str) -> tuple[int, int, int]:
    words = len(re.findall(r"\b[\w’'-]+\b", text))
    images = len(re.findall(r"!\[[^\]]*\]\([^)]*\)", text))
    tables = sum(1 for line in text.splitlines() if re.match(r"^\s*\|?\s*:?-{3,}", line))
    return words, images, tables


def main() -> None:
    errors: list[str] = []
    notes: list[str] = []

    if not LICENSE.exists():
        errors.append("LICENSE.md is missing")
    elif "MIT License" not in LICENSE.read_text(encoding="utf-8"):
        errors.append("LICENSE.md is not recognisably MIT licensed")

    if not README.exists():
        errors.append("README.md is missing")
    else:
        text = README.read_text(encoding="utf-8")
        words, images, tables = readme_counts(text)
        notes.append(f"README words={words}, images={images}, tables={tables}")
        if words > MAX_README_WORDS:
            errors.append(f"README has {words} words; limit is {MAX_README_WORDS}")
        if images + tables > MAX_FIGURES_OR_TABLES:
            errors.append(
                f"README has {images + tables} figures/tables; limit is {MAX_FIGURES_OR_TABLES}"
            )
        for required in ("make all", "make hardening", "diagnostic coaching metric"):
            if required not in text:
                errors.append(f"README is missing required guidance: {required!r}")

    tracked = tracked_files()
    forbidden = [p for p in tracked if p.suffix.lower() in FORBIDDEN_SUFFIXES]
    if forbidden:
        errors.append("forbidden data/media files are tracked: " + ", ".join(map(str, forbidden)))

    tracked_data = [p for p in tracked if p.parts and p.parts[0] == "data" and p.name != ".gitkeep"]
    if tracked_data:
        errors.append("competition data is tracked: " + ", ".join(map(str, tracked_data)))

    executable_scope_files = [ROOT / "Makefile", ROOT / "scripts/fetch_dataset.py", ROOT / "scripts/batch_validate.py", ROOT / "scripts/focused_analysis.py"]
    for scope_file in executable_scope_files:
        scope_text = scope_file.read_text(encoding="utf-8")
        if "all-public-matches" in scope_text or "public-all" in scope_text:
            errors.append(f"wider public-match execution path remains in {scope_file.relative_to(ROOT)}")

    required_paths = [
        "pyproject.toml",
        "src/defensive_recovery/dred.py",
        "tests/test_dred.py",
        "docs/API.md",
        "docs/RELATED_WORK.md",
        ".github/workflows/ci.yml",
        ".github/workflows/full-reproduction.yml",
    ]
    for rel in required_paths:
        if not (ROOT / rel).exists():
            errors.append(f"required project file missing: {rel}")

    print("DRED release audit")
    for note in notes:
        print(f"  OK  {note}")
    print(f"  OK  tracked files={len(tracked)}")
    print(f"  OK  tracked competition-data files={len(tracked_data)}")
    print(f"  OK  forbidden tracked data/media files={len(forbidden)}")

    if errors:
        for error in errors:
            print(f"  ERR {error}")
        raise SystemExit(1)
    print("PASS")


if __name__ == "__main__":
    main()
