# 60-second submission video — DRED

The Analytics Cup rules require the one-minute YouTube pitch to be **presented and voiced by the participant or teammate**. `scripts/build_video.py` creates the complete visual cut; the final voice must therefore be Ermir (or a teammate), not synthetic TTS.

## Final narration — 106 words

**0–8.5 s — Problem**

“A line break is only the start. Can the defence reopen and restore lateral coverage? Static compactness misses that.”

**8.5–21 s — Metric**

“I built Defensive Re-Expansion Debt, or DRED. It compares live width with each team's normal width for that phase. DRED intensity rises when the defence stays abnormally narrow.”

**21–40 s — Primary validation**

“Across 603 line-breaking possessions in ten official matches, higher DRED intensity was associated with greater SkillCorner EPV gain after controlling duration, starting EPV and static width. Eight matches were positive.”

**40–50 s — Mechanism**

“Body Pose supports the mechanism: contracted defences were less outward-oriented in both games.”

**50–58.5 s — Close**

“DRED is an open-source coaching diagnostic for failed recovery after penetration—not a black-box prediction score.”

## Recording target

- Speak naturally at roughly 110–120 words/minute.
- Aim for 54–58 seconds of voice; never rush the statistics.
- Record in a quiet room close to the microphone, with no music underneath the raw take.
- Do not claim causality or call DRED a pre-break prediction model.
- The detailed confidence interval stays on screen instead of burdening the narration.

## Build the visual cut

```bash
python3 scripts/build_video.py
```

Generated locally (ignored by Git):
- `video/dred_pitch_visual_cut.mp4` — 58.5-second 1080p/30fps visual cut.
- `video/NARRATION.txt` — teleprompter text.
- `video/dred_pitch_narration.srt` — timed transcript for YouTube captions.

## Add the participant voice

```bash
python3 scripts/mux_voice.py path/to/ermir_voice.m4a
```

This creates `video/dred_pitch_final.mp4`, normalises speech loudness and refuses any result that would exceed the one-minute limit.
