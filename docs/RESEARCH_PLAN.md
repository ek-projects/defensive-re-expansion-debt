# Research Plan — frozen submission direction

## Core construct

**Defensive Re-Expansion Debt (DRED)** measures abnormal lateral contraction after a second-last defensive line break.

Primary reporting distinguishes:

- accumulated DRED (integral);
- DRED intensity (mean abnormal contraction), used for cross-event validation where duration would otherwise confound the comparison.

## Primary external validation

Official 10 Dynamic Events matches only.

External quantity: SkillCorner `possession_epv_delta_for` on the line-break player possession.

Main adjusted comparison controls, within match, for:

- recovery-window duration;
- player-possession duration;
- starting EPV;
- static width deviation at the break.

Uncertainty emphasis: per-match partial associations and match-level bootstrap, not event-count p-values.

## Mechanism validation

The two official Body Pose matches test a hypothesis frozen before inspection: contracted recovery states should show lower outward shoulder-orientation readiness.

This remains exploratory because only two matches include pose.

## Secondary audit

`lead_to_shot` is not a primary target. Duration alone outperformed DRED in the shot-link AUC analysis; `make shot-audit` preserves this result as a reproducible confounding demonstration.

## Submission communication

One-minute narrative:

1. static compactness misses recovery dynamics;
2. define DRED and duration-normalized intensity;
3. show adjusted EPV relationship across the 10 official matches;
4. show Body Pose mechanism in both available pose games;
5. close with coaching use and open-source reproducibility.

No causality claim. No pre-break prediction claim.
