# DRED submission v2 candidate — post-submission research note

**Status:** not part of frozen Pretalx submission `8TTF3B`. The frozen submission remains commit `55b0d82` / tag `submission-8TTF3B`.

## Why a v2 exists

The submitted validation associated 10-second DRED intensity with SkillCorner `possession_epv_delta_for` on the triggering player possession. That result is reproducible (adjusted partial-rank **0.174**, positive in **8/10** matches), but an adversarial temporal audit shows that DRED measured strictly inside the triggering action is much weaker. This is expected for a recovery metric: the structural signal develops over several seconds after penetration.

A cleaner external validation therefore aligns the EPV outcome to the **same recovery window** used by DRED. For each second-last-line-break event, the aligned endpoint uses only player-possession EPV states from the same attacking team and the same phase, bounded by the event's DRED recovery window. End-of-possession EPV is used only when that possession completes before the recovery-window boundary.

## Candidate primary claim

> Defensive Re-Expansion Debt (DRED) measures abnormal lateral contraction after penetration. Across the ten official Dynamic Events matches, higher DRED intensity was associated with greater **net EPV gain over the same recovery window**, after adjusting within match for recovery-window duration, triggering-action duration, starting EPV and static width at the break. The pooled adjusted partial-rank association was **0.224**. The per-match association was positive in **9/10** matches, with median **0.209** and match-bootstrap 95% interval **0.068–0.330**.

This is a **contemporaneous diagnostic association**, not a causal effect and not a pre-break prediction claim.

## Adversarial checks that survived

- Recomputed DRED matches the stored primary metric to floating-point precision (`max |difference| = 3.33e-16`).
- Direction specificity: contraction adjusted `r=0.174`; expansion placebo `r=-0.125`; absolute width-tail placebo `r=0.011`.
- Pre-break contraction is much weaker (`r=0.057`).
- Previous second-last break by the same defending team is approximately null (`r=-0.002`).
- Richer event context (progress, field location, opponents bypassed, pressure, channel, third, OOP phase) leaves adjusted `r=0.157` on 602 events.
- Leave-one-defending-team-out estimates are all positive (`0.148–0.210`).
- Chronological halves remain positive (`0.165` early, `0.189` late).
- Adding DRED to the submitted controls lowers leave-one-match-out held-out MSE in 7/10 folds; weighted MSE falls by about **2.47%**.
- Body Pose remains a separate exploratory mechanism check, not primary inference.

## Limits that must remain visible

- The signal is **not unique to second-last-line breaks**: last-line breaks also show a positive adjusted association (`r=0.173`), whereas first-line breaks are approximately null (`r=-0.011`).
- DRED restricted strictly to the triggering player possession is weak in the first 0.5–2 seconds and reaches only about `r=0.10` over the full action-observable sample. This supports the recovery-process interpretation rather than instantaneous prediction.
- The aligned-window EPV analysis was performed **after** submission and cannot be described as pre-specified evidence.
- Ten matches remain a small external-validation set; Body Pose is available in only two matches.

## Recommendation

If the competition permits edits before the deadline, this v2 framing is scientifically cleaner than the submitted wording because the structural metric and external EPV outcome share the same time window. The one-minute video does not need to be treated as false: it says DRED is associated with greater SkillCorner EPV gain and explicitly calls DRED a diagnostic, not a prediction score. A README update can therefore strengthen the methodology without changing the core idea or overstating causality.

Full reproducible audit: `make adversarial` and `docs/POST_SUBMISSION_ADVERSARIAL_AUDIT.md`.
