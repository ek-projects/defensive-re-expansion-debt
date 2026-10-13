from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path

from build_video import CAPTIONS, NARRATION, ROOT, SCENES

VIDEO = ROOT / "video"
DEFAULT_VISUAL = VIDEO / "dred_pitch_visual_cut.mp4"
DEFAULT_FINAL = VIDEO / "dred_pitch_final.mp4"


def probe(path: Path) -> dict:
    raw = subprocess.check_output([
        "ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)
    ])
    return json.loads(raw)


def srt_end_seconds(value: str) -> float:
    h, m, rest = value.split(":")
    s, ms = rest.split(",")
    return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000


def normalise(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip())


def audit_visual(path: Path) -> None:
    if not path.exists():
        raise SystemExit(f"missing visual cut: {path}")
    info = probe(path)
    duration = float(info["format"]["duration"])
    video_streams = [s for s in info["streams"] if s.get("codec_type") == "video"]
    audio_streams = [s for s in info["streams"] if s.get("codec_type") == "audio"]
    assert 58.0 <= duration < 60.0, duration
    assert len(video_streams) == 1, len(video_streams)
    assert not audio_streams, "visual cut must not contain placeholder audio"
    v = video_streams[0]
    assert (int(v["width"]), int(v["height"])) == (1920, 1080)
    assert v.get("r_frame_rate") == "30/1", v.get("r_frame_rate")

    scene_total = sum(float(d) for _, d in SCENES)
    assert abs(scene_total - 58.5) < 1e-9, scene_total
    assert abs(duration - scene_total) < 0.05, (duration, scene_total)

    narration_file = VIDEO / "NARRATION.txt"
    assert narration_file.exists()
    assert normalise(narration_file.read_text()) == normalise(NARRATION)
    words = re.findall(r"\b[\w'-]+\b", NARRATION)
    assert 95 <= len(words) <= 115, len(words)

    srt = VIDEO / "dred_pitch_narration.srt"
    assert srt.exists()
    text = srt.read_text()
    timings = re.findall(r"(\d\d:\d\d:\d\d,\d{3}) --> (\d\d:\d\d:\d\d,\d{3})", text)
    assert len(timings) == len(CAPTIONS), len(timings)
    ends = [srt_end_seconds(end) for _, end in timings]
    assert abs(ends[-1] - 58.5) < 1e-9, ends[-1]
    subtitle_lines = []
    for block in re.split(r"\n\s*\n", text.strip()):
        lines = block.splitlines()
        subtitle_lines.extend(lines[2:])
    assert normalise(" ".join(subtitle_lines)) == normalise(NARRATION)
    print(f"visual PASS: {duration:.3f}s, 1920x1080, 30fps, video-only, narration={len(words)} words")


def audit_final(path: Path) -> None:
    if not path.exists():
        print(f"final SKIP: {path} does not exist yet")
        return
    info = probe(path)
    duration = float(info["format"]["duration"])
    types = [s.get("codec_type") for s in info["streams"]]
    assert duration < 60.0, duration
    assert "video" in types and "audio" in types, types
    print(f"final PASS: {duration:.3f}s with video+audio")


def main() -> None:
    ap = argparse.ArgumentParser(description="Audit the DRED one-minute pitch artifacts.")
    ap.add_argument("--visual", type=Path, default=DEFAULT_VISUAL)
    ap.add_argument("--final", type=Path, default=DEFAULT_FINAL)
    args = ap.parse_args()
    audit_visual(args.visual)
    audit_final(args.final)


if __name__ == "__main__":
    main()
