# 60-second submission video — DRED v2

The Analytics Cup 2.0 rules require the public YouTube pitch to be **at most one minute** and **presented and voiced by the participant or teammate**. `scripts/build_video.py` creates the complete visual cut; the final voice must therefore be Ermir (or a teammate), not synthetic TTS.

## Final narration — 107 words

**0–10 s — Problem**

“A line break is only the start. The real question is whether the defence can reopen and restore lateral coverage.”

**10–22 s — Metric**

“I built Defensive Re-Expansion Debt, or DRED. It measures how long a defence stays abnormally narrow relative to its own normal width.”

**22–38 s — Time-aligned validation**

“Across 602 second-last-line-break events in ten official matches, higher DRED intensity was associated with greater SkillCorner EPV gain measured over the same recovery window. Nine of ten matches were positive.”

**38–46.5 s — Mechanism**

“Body Pose supports the mechanism: contracted defences were less outward-oriented in both available games.”

**46.5–58.5 s — Close**

“DRED is open source, reproducible, and designed as a coaching diagnostic for failed recovery after penetration—not a black-box prediction score.”

## Recording target

- Speak naturally at roughly 110–120 words/minute.
- Aim for 54–58 seconds of voice; leave small pauses between the five sections.
- Record in a quiet room close to the microphone, with no music underneath the raw take.
- Do not claim causality or call DRED a pre-break prediction model.
- Do not try to read every statistic on screen; the voice carries the story, the figure carries the detail.

## Visual hierarchy

1. Problem: recovery after penetration, not static compactness.
2. Metric: abnormal lateral contraction relative to the team's own contextual width.
3. Validation: EPV and DRED use the **same recovery window**; adjusted partial-rank 0.224, 602 events, 9/10 matches positive.
4. Mechanism: Body Pose direction agrees in both available matches.
5. Close: open-source coaching diagnostic.

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
