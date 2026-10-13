from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from defensive_recovery.competition import (
    ANALYTICS_CUP_TRACKING_MATCH_ID_SET,
    OFFICIAL_DYNAMIC_EVENT_MATCH_ID_SET,
)

MEDIA_BASE = "https://media.githubusercontent.com/media/SkillCorner/opendata/master"
SMALL_SUFFIXES = ("_match.json", "_dynamic_events.csv", "_phases_of_play.csv")


def git_show(repo: Path, rel: str) -> bytes:
    return subprocess.check_output(["git", "-C", str(repo), "show", f"HEAD:{rel}"])


def lfs_pointer(repo: Path, rel: str) -> tuple[str, int]:
    text = git_show(repo, rel).decode("utf-8")
    sha = re.search(r"oid sha256:([0-9a-f]{64})", text)
    size = re.search(r"size (\d+)", text)
    if not sha or not size:
        raise RuntimeError(f"not a Git LFS pointer: {rel}")
    return sha.group(1), int(size.group(1))


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(8 * 1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def materialize_small(repo: Path, out_dir: Path, mid: str) -> None:
    for suffix in SMALL_SUFFIXES:
        name = f"{mid}{suffix}"
        rel = f"data/matches/{mid}/{name}"
        dest = out_dir / name
        blob = git_show(repo, rel)
        if not dest.exists() or dest.read_bytes() != blob:
            dest.write_bytes(blob)


def download_tracking(repo: Path, out_dir: Path, mid: str) -> None:
    name = f"{mid}_tracking_extrapolated.jsonl"
    rel = f"data/matches/{mid}/{name}"
    expected_sha, expected_size = lfs_pointer(repo, rel)
    dest = out_dir / name
    if dest.exists() and dest.stat().st_size == expected_size and sha256(dest) == expected_sha:
        print(f"{mid}: tracking verified (cached)", flush=True)
        return
    part = dest.with_suffix(dest.suffix + ".part")
    url = f"{MEDIA_BASE}/{rel}"
    subprocess.run(
        ["curl", "-fL", "--retry", "5", "--retry-delay", "2", "--connect-timeout", "20", "-C", "-", "-o", str(part), url],
        check=True,
    )
    if part.stat().st_size != expected_size:
        raise RuntimeError(f"{mid}: size mismatch {part.stat().st_size} != {expected_size}")
    actual = sha256(part)
    if actual != expected_sha:
        raise RuntimeError(f"{mid}: sha256 mismatch {actual} != {expected_sha}")
    part.replace(dest)
    print(f"{mid}: tracking downloaded + sha256 verified", flush=True)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--vendor", type=Path, default=Path("vendor/skillcorner-opendata"))
    ap.add_argument("--out", type=Path, default=Path("data/raw"))
    ap.add_argument("--match", action="append", dest="matches", help="optional subset of the frozen 20-match Analytics Cup tracking set")
    ap.add_argument("--all-competition-matches", action="store_true", help="fetch all 20 allowed Analytics Cup tracking matches")
    args = ap.parse_args()
    matches = json.loads((args.vendor / "data/matches.json").read_text())
    available = {str(m["id"]) for m in matches}
    primary = {str(mid) for mid in OFFICIAL_DYNAMIC_EVENT_MATCH_ID_SET}
    allowed = {str(mid) for mid in ANALYTICS_CUP_TRACKING_MATCH_ID_SET}
    required = allowed if args.all_competition_matches else primary
    missing = sorted(required - available)
    if missing:
        raise RuntimeError(f"required Analytics Cup matches missing from vendor dataset: {missing}")
    if args.matches:
        wanted = set(args.matches)
        outside_scope = sorted(wanted - allowed)
        if outside_scope:
            ap.error(f"--match must be one of the frozen Analytics Cup tracking IDs: {outside_scope}")
        ids = sorted(wanted, reverse=True)
    else:
        ids = sorted(required, reverse=True)
    args.out.mkdir(parents=True, exist_ok=True)
    failures = []
    for i, mid in enumerate(ids, 1):
        print(f"[{i}/{len(ids)}] {mid}", flush=True)
        out_dir = args.out / mid
        out_dir.mkdir(parents=True, exist_ok=True)
        try:
            materialize_small(args.vendor, out_dir, mid)
            download_tracking(args.vendor, out_dir, mid)
        except Exception as exc:
            failures.append((mid, str(exc)))
            print(f"ERROR {mid}: {exc}", file=sys.stderr, flush=True)
    if failures:
        for mid, err in failures:
            print(f"FAILED {mid}: {err}", file=sys.stderr)
        raise SystemExit(1)
    print(f"complete: {len(ids)} matches", flush=True)


if __name__ == "__main__":
    main()
