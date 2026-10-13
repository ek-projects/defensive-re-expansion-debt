from __future__ import annotations

import subprocess
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
VIDEO = ROOT / "video"
ASSETS = VIDEO / "assets"
FIGURES = ROOT / "figures"
W, H = 1920, 1080
BG = (10, 18, 31)
PANEL = (248, 250, 252)
TEXT = (244, 247, 250)
MUTED = (170, 184, 199)
ACCENT = (70, 210, 155)
ACCENT2 = (86, 162, 255)
DANGER = (255, 132, 110)

FONT_REG = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

NARRATION = """A line break is only the start. Can the defence reopen and restore lateral coverage? Static compactness misses that.

I built Defensive Re-Expansion Debt, or DRED. It compares live width with each team's normal width for that phase. DRED intensity rises when the defence stays abnormally narrow.

Across 603 line-breaking possessions in ten official matches, higher DRED intensity was associated with greater SkillCorner EPV gain after controlling duration, starting EPV and static width. Eight matches were positive.

Body Pose supports the mechanism: contracted defences were less outward-oriented in both games.

DRED is an open-source coaching diagnostic for failed recovery after penetration—not a black-box prediction score.
"""

SCENES = [
    ("scene_01_hook.png", 8.5),
    ("scene_02_metric.png", 12.5),
    ("scene_03_epv.png", 19.0),
    ("scene_04_pose.png", 10.0),
    ("scene_05_close.png", 8.5),
]


def font(size: int, bold: bool = False):
    return ImageFont.truetype(FONT_BOLD if bold else FONT_REG, size)


def fit_text(draw, text, box, max_size, min_size=24, bold=False, spacing=12):
    x0, y0, x1, y1 = box
    for size in range(max_size, min_size - 1, -2):
        f = font(size, bold)
        words = text.split()
        lines, line = [], ""
        for word in words:
            trial = (line + " " + word).strip()
            if draw.textbbox((0, 0), trial, font=f)[2] <= x1 - x0:
                line = trial
            else:
                if line:
                    lines.append(line)
                line = word
        if line:
            lines.append(line)
        h = sum(draw.textbbox((0, 0), ln, font=f)[3] for ln in lines) + spacing * max(0, len(lines) - 1)
        if h <= y1 - y0:
            return f, lines
    return font(min_size, bold), [text]


def draw_wrapped(draw, text, box, size=50, color=TEXT, bold=False, spacing=12, anchor="la"):
    f, lines = fit_text(draw, text, box, size, bold=bold, spacing=spacing)
    x0, y0, _, _ = box
    y = y0
    for ln in lines:
        draw.text((x0, y), ln, font=f, fill=color, anchor=anchor)
        bb = draw.textbbox((x0, y), ln, font=f, anchor=anchor)
        y += (bb[3] - bb[1]) + spacing
    return y


def title_band(im, kicker, title, subtitle=None):
    d = ImageDraw.Draw(im)
    d.text((100, 70), kicker.upper(), font=font(28, True), fill=ACCENT)
    draw_wrapped(d, title, (100, 118, 1820, 280), size=74, bold=True, spacing=8)
    if subtitle:
        draw_wrapped(d, subtitle, (104, 282, 1810, 365), size=32, color=MUTED, spacing=6)


def place_figure(im, path: Path, box, border=True):
    x0, y0, x1, y1 = box
    src = Image.open(path).convert("RGBA")
    maxw, maxh = x1 - x0, y1 - y0
    scale = min(maxw / src.width, maxh / src.height)
    nw, nh = int(src.width * scale), int(src.height * scale)
    src = src.resize((nw, nh), Image.Resampling.LANCZOS)
    px, py = x0 + (maxw - nw)//2, y0 + (maxh - nh)//2
    if border:
        draw = ImageDraw.Draw(im)
        draw.rounded_rectangle((x0, y0, x1, y1), 26, fill=PANEL)
    im.alpha_composite(src, (px, py))


def scene_hook():
    im = Image.new("RGBA", (W,H), BG + (255,))
    d = ImageDraw.Draw(im)
    title_band(im, "Defensive Re-Expansion Debt", "A line break is only the start.", "Can the defence reopen and restore lateral coverage?")
    # pitch schematic
    pitch = (160, 430, 1760, 900)
    d.rounded_rectangle(pitch, 24, outline=(70,95,120), width=4)
    cx = (pitch[0]+pitch[2])//2
    d.line((cx,pitch[1],cx,pitch[3]), fill=(70,95,120), width=3)
    # normal defence
    ys = [510, 605, 700, 795]
    xs_wide = [390, 720, 1050, 1380]
    xs_narrow = [690, 870, 1050, 1230]
    for x,y in zip(xs_wide,ys): d.ellipse((x-20,y-20,x+20,y+20), fill=ACCENT2)
    for x,y in zip(xs_narrow,ys): d.ellipse((x-18,y-18,x+18,y+18), outline=DANGER, width=5)
    d.line((390,850,1380,850), fill=ACCENT2, width=6)
    d.polygon([(390,850),(420,836),(420,864)], fill=ACCENT2); d.polygon([(1380,850),(1350,836),(1350,864)], fill=ACCENT2)
    d.text((760,870), "normal lateral coverage", font=font(28, True), fill=ACCENT2, anchor="ma")
    d.line((690,770,1230,770), fill=DANGER, width=6)
    d.polygon([(690,770),(720,756),(720,784)], fill=DANGER); d.polygon([(1230,770),(1200,756),(1200,784)], fill=DANGER)
    d.text((960,730), "post-break collapse", font=font(30, True), fill=DANGER, anchor="mm")
    d.text((100,990), "STATIC COMPACTNESS ≠ RECOVERY", font=font(30, True), fill=MUTED)
    return im


def scene_metric():
    im = Image.new("RGBA", (W,H), BG + (255,))
    d = ImageDraw.Draw(im)
    title_band(im, "The metric", "DRED measures abnormal contraction over time.", "Each team is compared with its own normal width for the same defensive phase.")
    place_figure(im, FIGURES / "dred_case_study.png", (930, 400, 1810, 970))
    d.rounded_rectangle((100, 420, 850, 940), 30, fill=(18,31,50))
    d.text((150, 475), "DRED intensity", font=font(50, True), fill=ACCENT)
    draw_wrapped(d, "rises when the defence stays abnormally narrow", (150, 555, 790, 720), size=42, bold=True)
    d.text((150, 770), "✓ context-normalised", font=font(32), fill=TEXT)
    d.text((150, 825), "✓ duration-normalised", font=font(32), fill=TEXT)
    d.text((150, 880), "✓ interpretable in metres / time", font=font(32), fill=TEXT)
    return im


def scene_epv():
    im = Image.new("RGBA", (W,H), BG + (255,))
    d = ImageDraw.Draw(im)
    title_band(im, "Primary validation", "Higher DRED intensity tracks greater EPV gain.", "Adjusted within match for duration, starting EPV and static width.")
    place_figure(im, FIGURES / "dred_epv_validation.png", (80, 385, 1325, 990))
    d.rounded_rectangle((1370, 420, 1830, 920), 28, fill=(18,31,50))
    d.text((1600, 485), "603", font=font(86, True), fill=ACCENT, anchor="ma")
    d.text((1600, 575), "line-breaking possessions", font=font(28, True), fill=TEXT, anchor="ma")
    d.text((1600, 665), "8 / 10", font=font(72, True), fill=ACCENT2, anchor="ma")
    d.text((1600, 745), "matches positive", font=font(28, True), fill=TEXT, anchor="ma")
    d.text((1600, 825), "median r = 0.154", font=font(31, True), fill=TEXT, anchor="ma")
    d.text((1600, 870), "95% CI 0.044–0.268", font=font(27), fill=MUTED, anchor="ma")
    return im


def scene_pose():
    im = Image.new("RGBA", (W,H), BG + (255,))
    d = ImageDraw.Draw(im)
    title_band(im, "Mechanism check", "Body Pose points in the same tactical direction.", "Contracted defensive states show lower outward shoulder-orientation readiness.")
    place_figure(im, FIGURES / "dred_bodypose_validation.png", (120, 390, 1240, 970))
    d.rounded_rectangle((1300, 430, 1810, 900), 28, fill=(18,31,50))
    d.text((1555, 500), "2 / 2", font=font(82, True), fill=ACCENT, anchor="ma")
    d.text((1555, 590), "Body Pose matches", font=font(31, True), fill=TEXT, anchor="ma")
    draw_wrapped(d, "less outward-ready when abnormally contracted", (1370, 680, 1740, 850), size=38, bold=True)
    return im


def scene_close():
    im = Image.new("RGBA", (W,H), BG + (255,))
    d = ImageDraw.Draw(im)
    d.text((100, 120), "DRED", font=font(120, True), fill=ACCENT)
    draw_wrapped(d, "A coaching diagnostic for failed recovery after penetration.", (105, 285, 1300, 500), size=62, bold=True)
    d.rounded_rectangle((105, 585, 1770, 795), 30, fill=(18,31,50))
    d.text((155, 635), "Open source • reproducible • interpretable", font=font(38, True), fill=TEXT)
    d.text((155, 710), "github.com/ek-projects/defensive-re-expansion-debt", font=font(31), fill=ACCENT2)
    d.text((105, 935), "NOT A BLACK-BOX PREDICTION SCORE", font=font(30, True), fill=MUTED)
    return im


def write_srt():
    # Full narration transcript, timed to the visual cut. Timing is intentionally generous for human delivery.
    blocks = [
        (1, "00:00:00,000", "00:00:08,500", "A line break is only the start. Can the defence reopen and restore lateral coverage? Static compactness misses that."),
        (2, "00:00:08,500", "00:00:21,000", "I built Defensive Re-Expansion Debt, or DRED. It compares live width with each team's normal width for that phase. DRED intensity rises when the defence stays abnormally narrow."),
        (3, "00:00:21,000", "00:00:40,000", "Across 603 line-breaking possessions in ten official matches, higher DRED intensity was associated with greater SkillCorner EPV gain after controlling duration, starting EPV and static width. Eight matches were positive."),
        (4, "00:00:40,000", "00:00:50,000", "Body Pose supports the mechanism: contracted defences were less outward-oriented in both games."),
        (5, "00:00:50,000", "00:00:58,500", "DRED is an open-source coaching diagnostic for failed recovery after penetration—not a black-box prediction score."),
    ]
    text = "\n\n".join(f"{i}\n{s} --> {e}\n{t}" for i,s,e,t in blocks) + "\n"
    (VIDEO / "dred_pitch_narration.srt").write_text(text)


def encode():
    # Encode each still independently to respect the VPS process/thread limits,
    # then concatenate identical H.264/AAC segments without re-encoding.
    segments = []
    for idx, (name, duration) in enumerate(SCENES, start=1):
        src = ASSETS / name
        seg = ASSETS / f"segment_{idx:02d}.mp4"
        segments.append(seg)
        cmd = [
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "warning",
            "-threads", "1", "-filter_threads", "1",
            "-loop", "1", "-framerate", "30", "-t", str(duration), "-i", str(src),
            "-f", "lavfi", "-t", str(duration), "-i", "anullsrc=r=48000:cl=stereo",
            "-vf", "format=yuv420p", "-r", "30",
            "-c:v", "libx264", "-threads", "1", "-crf", "18", "-preset", "medium",
            "-c:a", "aac", "-b:a", "128k", "-shortest", "-movflags", "+faststart", str(seg),
        ]
        subprocess.run(cmd, check=True)
    concat = ASSETS / "concat.txt"
    concat.write_text("".join("file '{}'\n".format(seg.name) for seg in segments))
    out = VIDEO / "dred_pitch_visual_cut.mp4"
    subprocess.run([
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "warning",
        "-f", "concat", "-safe", "0", "-i", str(concat),
        "-c", "copy", "-movflags", "+faststart", str(out),
    ], check=True)


def main():
    VIDEO.mkdir(exist_ok=True); ASSETS.mkdir(exist_ok=True)
    makers=[scene_hook,scene_metric,scene_epv,scene_pose,scene_close]
    for (name,_),make in zip(SCENES,makers):
        make().convert("RGB").save(ASSETS / name, quality=95)
    (VIDEO / "NARRATION.txt").write_text(NARRATION)
    write_srt()
    encode()
    print(VIDEO / "dred_pitch_visual_cut.mp4")

if __name__ == "__main__":
    main()
