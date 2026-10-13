from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_VIDEO = ROOT / "video" / "dred_pitch_visual_cut.mp4"
DEFAULT_OUTPUT = ROOT / "video" / "dred_pitch_final.mp4"
MAX_VOICE = 58.0


def duration(path: Path) -> float:
    raw = subprocess.check_output([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "json", str(path),
    ])
    return float(json.loads(raw)["format"]["duration"])


def main() -> None:
    ap = argparse.ArgumentParser(description="Mux the participant's real voice into the DRED visual cut.")
    ap.add_argument("voice", type=Path, help="Participant voice recording (wav/m4a/mp3/etc.)")
    ap.add_argument("--video", type=Path, default=DEFAULT_VIDEO)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = ap.parse_args()

    if not args.voice.exists():
        raise SystemExit(f"voice file not found: {args.voice}")
    if not args.video.exists():
        raise SystemExit(f"visual cut not found: {args.video}; run scripts/build_video.py first")

    voice_s = duration(args.voice)
    visual_s = duration(args.video)
    if voice_s > MAX_VOICE:
        raise SystemExit(
            f"voice is too long ({voice_s:.2f}s); record a take <= {MAX_VOICE:.1f}s "
            "so the finished pitch remains safely below one minute"
        )
    if visual_s >= 60.0:
        raise SystemExit(f"visual cut is already too long: {visual_s:.3f}s")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    # Human voice only. Keep video bit-identical, clean speech conservatively,
    # normalise to spoken-word loudness, then pad silence to the visual endpoint.
    af = "highpass=f=70,lowpass=f=14000,loudnorm=I=-16:TP=-1.5:LRA=11,apad"
    cmd = [
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "warning", "-threads", "1",
        "-i", str(args.video), "-i", str(args.voice),
        "-map", "0:v:0", "-map", "1:a:0", "-af", af,
        "-t", f"{visual_s:.3f}", "-c:v", "copy", "-c:a", "aac", "-b:a", "160k",
        "-movflags", "+faststart", str(args.output),
    ]
    subprocess.run(cmd, check=True)
    final_s = duration(args.output)
    if final_s >= 60.0:
        args.output.unlink(missing_ok=True)
        raise SystemExit(f"safety failure: encoded video is {final_s:.3f}s")
    print(f"voice={voice_s:.3f}s visual={visual_s:.3f}s final={final_s:.3f}s")
    print(args.output)


if __name__ == "__main__":
    main()
