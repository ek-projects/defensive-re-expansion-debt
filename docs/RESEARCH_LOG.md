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

The wider 20-match public-data pass helped form the hypothesis and is therefore exploratory only.

## Official competition scope

Primary labelled analysis was rebuilt from scratch on the 10 Analytics Cup matches with Game Intelligence Dynamic Events:

`1886347, 1899585, 1925299, 1953632, 1996435, 2006229, 2011166, 2013725, 2015213, 2017461`

The code defaults to those IDs. `--all-public-matches` is explicitly labelled a research extension.

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
