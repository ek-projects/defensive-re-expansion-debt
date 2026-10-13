# Research Log

## 2026-10-12 — Starting hypothesis

The project began as **Defensive Recovery Debt**, a multivariate structural-distance score after line breaks. Width, length, area and nearest-neighbour spacing were combined to measure how long a defence remained structurally displaced.

The first full-match prototype looked promising, but the wider public-data pass showed the composite was not better than simple width and max-gap baselines. It was rejected rather than promoted.

## Discovery of DRED

Stratification isolated a clearer phenomenon after **second-last-line breaks**: sustained lateral contraction. This became **Defensive Re-Expansion Debt (DRED)**.

For robust within-match/team/OOP-phase width deviation `z_width(t)`:

`contraction(t) = max(-z_width(t) - 1, 0)`

- DRED = integral of contraction over the recovery window.
- DRED intensity = mean contraction over observed frames.

A historical wider public-data pass helped form the hypothesis and is recorded here for transparency. No result from matches outside the frozen 10-match competition scope is used as submission evidence, and the v2 pipeline no longer exposes a wider-match execution path.

## Official competition scope

Primary labelled analysis was rebuilt from scratch on the 10 Analytics Cup matches with Game Intelligence Dynamic Events:

`1886347, 1899585, 1925299, 1953632, 1996435, 2006229, 2011166, 2013725, 2015213, 2017461`

The v2 code is hard-pinned to those IDs. Dataset fetching, batch validation and focused analysis reject or filter any match outside this set.

## Shot-link result — and why it was demoted

On 632 official second-last-line breaks, DRED integral had ROC AUC 0.624 for `lead_to_shot`. Static width at the break was near chance at 0.501.

A confounding audit changed the interpretation:

- remaining recovery/possession-window duration alone: AUC **0.650**;
- shot-linked events had longer remaining windows on average;
- within the same match and approximately the same 0.1 s recovery-duration strata, DRED conditional AUC fell to **0.540**.

Therefore `lead_to_shot` is not used as primary validation. The full result remains reproducible through `make shot-audit` specifically to document the failed shortcut.

## External validation: event-local EPV

SkillCorner `possession_epv_delta_for` measures the change in attacking possession value during an individual player possession. This provides an event-local external quantity rather than a future shot label.

There are **603** official second-last-line-break player possessions with non-null EPV.

Raw association:

- DRED intensity vs EPV gain: Spearman rho **0.126**.

Both DRED and EPV can be affected by duration/context, so the main comparison ranks variables within match and removes:

1. recovery-window duration;
2. player-possession action duration;
3. EPV at action start;
4. static absolute width deviation at the break.

Results:

- pooled adjusted partial-rank association: **0.174**;
- per-match median partial association: **0.154**;
- positive in **8/10** matches;
- match-bootstrap 95% interval for the median: **0.044 to 0.268**;
- one-sided sign test for 8/10 positive: p=0.0547.

The match-level bootstrap is preferred over treating all 603 events as independent matches.

## Body Pose mechanism check

The Body Pose hypothesis was frozen before inspecting the result:

> Greater abnormal lateral contraction should coincide with lower outward shoulder-orientation readiness.

Both official Body Pose archives were downloaded and verified against SkillCorner's published SHA-256. Shoulder orientations follow the SkillCorner worked-example convention and quality gates: both shoulders present, plausible shoulder width, joint p90 error <=15 cm.

Results:

- match 1925299: 4,195 pose-aligned tracking frames; contracted readiness **-0.202**, normal-width **-0.075**;
- match 1996435: 3,942 frames; contracted **-0.101**, normal-width **-0.020**;
- pooled across 156 pose-covered line-break events, DRED intensity vs outward readiness Spearman rho **-0.175**.

This is mechanistic support, not primary inference: there are only two Body Pose matches and frame observations are serially dependent.

## Current interpretation

DRED is best treated as an interpretable **defensive recovery diagnostic**. The strongest evidence is not that it independently predicts a future shot. Instead:

1. greater DRED intensity is modestly but consistently associated with greater event-local EPV creation after controlling major duration/context variables; and
2. the expected body-orientation mechanism appears in both available Body Pose matches.

The negative and confounded results remain documented to avoid turning the project into post-hoc metric selection.

## 2026-10-13 — Post-submission robustness audit

This analysis was run **after** Pretalx submission `8TTF3B` and is therefore robustness evidence, not pre-specified confirmatory evidence. The frozen submission remains commit `55b0d829ff36918d2980d00266ced74c7a5c5d28`.

The EPV pipeline was extended on the isolated `post-submission-hardening` branch to recompute DRED directly from frame-level `z_width` under five abnormal-contraction thresholds (0.50, 0.75, 1.00, 1.25, 1.50) and four recovery horizons (3, 5, 8, 10 seconds).

Results:

- the recomputed primary 1.0-threshold / 10-second DRED intensity matches the submitted stored metric to numerical precision (maximum absolute difference `3.33e-16`);
- all **20/20** threshold × horizon combinations retain a positive duration/context-adjusted association with event-local EPV gain;
- adjusted partial-rank associations range from **0.064 to 0.201**, median **0.154**;
- leave-one-match-out estimates are positive for all ten omissions, range **0.151 to 0.209**;
- a 10,000-repetition within-match permutation of adjusted DRED residuals gives null mean approximately zero, 95% null interval **-0.088 to 0.083**, with the observed **0.174** outside that range (one-sided empirical p **0.0001**).

These checks reduce concern that the EPV relationship is an artifact of one match, one exact DRED threshold, or the 10-second horizon. They do not turn the observational association into a causal effect.

## 2026-10-13 — Post-submission adversarial temporal audit

A second post-submission audit deliberately tested whether the EPV result was direction-specific, event-local and temporally aligned. This work remains outside the frozen `8TTF3B` evidence set.

Key findings:

- direction specificity is strong: DRED contraction adjusted **r=0.174**, width-expansion placebo **r=-0.125**, absolute-width abnormality placebo **r=0.011**;
- pre-break contraction is much weaker (**r=0.057**) and the previous second-last break by the same defending team is approximately null (**r=-0.002**);
- adding richer context (attacking progress/location, opponents bypassed, pressure, channel, third and OOP phase) leaves adjusted **r=0.157** on 602 events;
- leave-one-defending-team-out estimates are all positive (**0.148–0.210**), and both chronological halves remain positive (**0.165** early, **0.189** late);
- a leave-one-match-out incremental regression gets lower held-out MSE after adding DRED in **7/10** matches, with **2.47%** weighted MSE reduction;
- the effect is not unique to second-last-line breaks: first-line breaks are approximately null (**r=-0.011**), while last-line breaks are also positive (**r=0.173**).

The most important temporal check changed the preferred interpretation. When DRED is computed only from reliable tracking frames that occur before the triggering player possession ends, the association is near zero in the first 0.5–2 seconds and reaches only about **r=0.10** over the full action-observable sample. DRED therefore behaves like a recovery-process metric rather than an instantaneous action predictor.

A recovery-window-aligned EPV endpoint was then constructed using only player-possession EPV states from the same attacking team, same phase and same DRED window. Net EPV gain over that shared window has adjusted **r=0.224**, median per-match **0.209**, is positive in **9/10** matches and has match-bootstrap 95% interval **0.068–0.330**. This is cleaner contemporaneous validation for the recovery construct, but it is explicitly post-submission and non-causal.

Full details are reproduced by `make adversarial` and tracked in `docs/POST_SUBMISSION_ADVERSARIAL_AUDIT.md`.

## 2026-10-13 — v2 candidate: reusable DRED API

The candidate branch extracts the final DRED definition into `src/defensive_recovery/dred.py` with provider-agnostic functions for contextual width standardisation, frame-level contraction excess and DRED summaries. The competition pipeline now calls the same library function rather than carrying a second inline implementation.

Integration validation on official match 1925299 regenerated all 134 line-break episodes. DRED/width-contraction output columns compared against the pre-refactor processed file with maximum absolute difference **0.0**. Core tests expanded from 5 to **9** and pass.

This refactor changes packaging and reuse only; it does not change the metric or frozen submission evidence.

## 2026-10-13 — v2 clean-reproduction verification

The `submission-v2-candidate` branch was cloned into a separate temporary checkout with no derived `data/processed` or `outputs`. Only the already SHA-verified raw official data and SkillCorner vendor checkout were linked in. `make hardening` regenerated the full derived analysis successfully: **9/9 tests passed**, the robustness and adversarial JSON outputs were exactly equal to the source checkout, and `figures/dred_epv_aligned_validation.png` reproduced with the same SHA-256 (`14daee1682991ce13aafc168a77e570a5a5147d333bb62feb9e73483afffae00`).

A separate clean Python virtual environment installed the package from `pyproject.toml`, passed all 9 tests and imported/executed `compute_dred` successfully.

The public YouTube submission was also checked independently: it is public, reports 59 seconds, contains an audio track, and YouTube exposes English automatic captions that transcribe the expected DRED narration. This verifies spoken narration is present; automated checks do not establish speaker identity.
