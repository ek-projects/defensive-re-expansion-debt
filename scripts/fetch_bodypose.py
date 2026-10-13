from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import urllib.request

FILES = {
    1925299: (623_408_231, "0415665098d594fb5681815000f7a6312037788a3237910a9f41bb8de5c336a0"),
    1996435: (644_327_811, "64bcab2be9776172d062521d9a97e0e6f391fc9cacb331f9e42a6fe88cf8434b"),
}
BASE = "https://huggingface.co/datasets/SkillCorner/opendata-bodypose/resolve/main/raw"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def fetch(match_id: int, dest: Path) -> None:
    size, expected = FILES[match_id]
    dest.mkdir(parents=True, exist_ok=True)
    path = dest / f"{match_id}.jsonl.zip"
    if path.exists() and path.stat().st_size == size and sha256(path) == expected:
        print(f"{match_id}: verified (cached)")
        return
    tmp = path.with_suffix(path.suffix + ".part")
    url = f"{BASE}/{match_id}.jsonl.zip"
    print(f"{match_id}: downloading {size / 1024**2:.1f} MiB")
    with urllib.request.urlopen(url) as response, tmp.open("wb") as out:
        while True:
            block = response.read(1024 * 1024)
            if not block:
                break
            out.write(block)
    if tmp.stat().st_size != size:
        tmp.unlink(missing_ok=True)
        raise RuntimeError(f"{match_id}: size mismatch")
    got = sha256(tmp)
    if got != expected:
        tmp.unlink(missing_ok=True)
        raise RuntimeError(f"{match_id}: sha256 mismatch")
    tmp.replace(path)
    print(f"{match_id}: sha256 verified")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dest", type=Path, default=Path("data/bodypose"))
    ap.add_argument("--match", type=int, choices=sorted(FILES), action="append")
    args = ap.parse_args()
    for match_id in (args.match or sorted(FILES)):
        fetch(match_id, args.dest)


if __name__ == "__main__":
    main()
