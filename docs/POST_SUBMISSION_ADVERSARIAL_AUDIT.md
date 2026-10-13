# DRED post-submission adversarial EPV audit

Post-submission adversarial audit for Pretalx submission 8TTF3B. These analyses were not pre-specified before the submitted result and must not be represented as such.

## Executive result

- submitted event-local EPV adjusted partial-rank: **0.174** on **603** events
- richer-context adjusted result: **0.157** on **602** events
- recovery-window-aligned net EPV gain: adjusted **0.224**, median match **0.209**, positive **9/10** matches
- aligned net-EPV match-bootstrap 95% interval: **0.068 to 0.330**

The central interpretation changes slightly after the adversarial checks: DRED is best supported as a contemporaneous recovery diagnostic over the recovery window, not as an instantaneous player-action predictor.

## Direction specificity

| metric | n | raw rho | adjusted r |
|---|---:|---:|---:|
| DRED contraction | 603 | 0.126 | 0.174 |
| width expansion placebo | 603 | -0.109 | -0.125 |
| absolute width-tail placebo | 603 | -0.035 | 0.011 |

## Event-locality placebos

| placebo | n | adjusted r |
|---|---:|---:|
| pre-break contraction | 451 | 0.057 |
| previous second-last break by the same defending team | 590 | -0.002 |

## Triggering-action temporal alignment

DRED was recomputed using only reliable tracking frames that occur before the triggering player possession ends. The effect is weak in the first seconds and increases only for longer actions, which is consistent with DRED being a recovery-process metric.

| action cap | n | adjusted r | median match r | positive matches |
|---:|---:|---:|---:|---:|
| 0.5s | 485 | 0.015 | 0.078 | 7/10 |
| 1.0s | 487 | 0.002 | 0.073 | 6/10 |
| 2.0s | 493 | 0.022 | 0.087 | 6/10 |
| 3.0s | 496 | 0.048 | 0.067 | 6/10 |
| 5.0s | 498 | 0.107 | 0.166 | 7/10 |
| 10.0s | 501 | 0.098 | 0.152 | 6/10 |

## EPV aligned to the same recovery window

The alternative outcome uses only player-possession EPV states from the same attacking team, same phase and same DRED recovery window. Completed-possession end values are required for the net endpoint; the strict peak endpoint never uses an event end beyond the recovery-window boundary.

| outcome | n | raw rho | adjusted r | median match r | positive matches | 95% median CI |
|---|---:|---:|---:|---:|---:|---:|
| net EPV gain | 602 | 0.226 | 0.224 | 0.209 | 9/10 | 0.068 to 0.330 |
| strict peak EPV gain | 603 | 0.271 | 0.205 | 0.214 | 8/10 | 0.037 to 0.304 |
| sum of player-possession EPV deltas | 602 | 0.069 | 0.088 | 0.097 | 7/10 | -0.050 to 0.272 |

## Specificity across line-break depth

| furthest line broken | n | adjusted r | median match r | positive matches |
|---|---:|---:|---:|---:|
| first | 351 | -0.011 | 0.057 | 6/10 |
| second_last | 603 | 0.174 | 0.154 | 8/10 |
| last | 170 | 0.173 | 0.120 | 8/10 |

## Stability checks

- leave-one-defending-team-out: all positive **True**, range **0.148 to 0.210**, median **0.174**
- chronological early half: **0.165** (299 events)
- chronological late half: **0.189** (304 events)
- leave-one-match-out cross-match regression: adding DRED lowers held-out MSE in **7/10** matches; weighted MSE reduction **2.47%**

## Exposure shape

- zero DRED: **476** events; positive DRED: **127**
- any-DRED indicator adjusted association: **0.162**
- among positive-DRED events only, continuous intensity adjusted association: **0.153**

Positive-DRED tertiles (adjusted EPV outcome residual, standardised after the submitted controls):

| tertile | n | DRED range | mean adjusted EPV residual (SD) |
|---|---:|---:|---:|
| low | 42 | 0.0002–0.0685 | 0.126 |
| middle | 42 | 0.0713–0.2081 | 0.372 |
| high | 43 | 0.2113–1.0811 | 0.390 |

## What survived and what did not

- SUPPORT: The submitted association reproduces exactly from the stored tracking-derived metric.
- SUPPORT: The signal is direction-specific: contraction is positive while expansion is negative and absolute width abnormality is approximately null.
- SUPPORT: Pre-break contraction and the previous same-defender event are much weaker, supporting event locality.
- SUPPORT: The association survives richer event context, leave-one-defending-team-out checks, and both chronological halves.
- SUPPORT: A recovery-window-aligned EPV endpoint is stronger than the submitted triggering-action EPV endpoint and is positive in most matches.
- LIMIT: The effect is not unique to second-last-line breaks: last-line breaks also show a positive adjusted association, while first-line breaks are approximately null.
- LIMIT: When DRED is restricted strictly to the triggering player action, the association is materially weaker and near zero in the earliest 0.5-2 seconds.
- LIMIT: This reinforces DRED as a recovery diagnostic rather than an instantaneous or pre-break prediction score.
- LIMIT: The recovery-window-aligned EPV analysis is post-submission evidence and is contemporaneous association, not causal proof.

No causal or pre-break prediction claim is supported by this audit.
