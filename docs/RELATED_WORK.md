# Related work and originality boundary

**Search date:** 2026-10-13. This note is deliberately conservative: DRED is not claimed to be the first dynamic defensive-organisation metric.

## Closest established work

### Defensive compactness from tracking data

Forcher et al. studied defensive compactness and organisation in 153 Bundesliga matches using whole-team and subgroup surface area/spread plus distances between formation lines. Their result is an important warning against assuming that global compactness is inherently successful: whole-team compactness differed little between successful and unsuccessful defensive plays, while the five defenders closest to the ball showed small local compactness differences.

Reference: Forcher L, Forcher L, Altmann S, Jekauc D, Kempe M. *Is a compact organization important for defensive success in elite soccer? – Analysis based on player tracking data.* International Journal of Sports Science & Coaching. DOI: https://doi.org/10.1177/17479541231172695

### Prediction of defensive success

Related work has used tracking-derived defensive pressure, distance to ball, inter-line distances, numerical superiority, surface area and spread as inputs to machine-learning models of ball-winning success. This establishes that spatial defensive features can carry outcome information, but it is a different goal from an interpretable post-penetration recovery diagnostic.

Reference: *Prediction of defensive success in elite soccer using machine learning – Tactical analysis of defensive play using tracking data and explainable AI.* DOI: https://doi.org/10.1080/24733938.2023.2239766

### Dynamic defensive reorganisation after a transition

Serra et al. (2026) is the closest conceptual neighbour found in this scan. It measures goal-referenced angular concentration of players' movement directions after negative transitions and relates it to controlled ball recovery within 10 seconds. It is explicitly a process indicator of defensive reorganisation.

Reference: Serra E, Carrilho D, Xiao L, et al. *Team Synergies in Professional Football: A Goal-Referenced Performance Indicator for Rapid Ball Recovery in Negative Transitions.* Sports. 2026;14(9):374. DOI: https://doi.org/10.3390/sports14090374

### Defensive pressure indices

Li et al. (2026) developed and initially validated a tracking-data defensive pressure index in the Chinese Super League, combining tactical defensive information rather than measuring the specific post-penetration lateral recovery process used by DRED.

Reference: Li J, Wu F, Li A, Martínez-Santos R. *Development and initial validation of a defensive pressure index using tracking data in the Chinese super league.* Frontiers in Sports and Active Living. DOI: https://doi.org/10.3389/fspor.2026.1833549

## What is distinctive about DRED

The defensible originality claim is the **combination**, not ownership of the general idea of dynamic defensive organisation:

1. the trigger is an observed defensive-line penetration rather than generic defensive play or loss of possession;
2. the state variable is specifically **lateral re-expansion**, measured as abnormal width contraction relative to that team's contextual out-of-possession reference;
3. DRED separates accumulated debt from duration-normalised intensity;
4. external validation can be aligned to the same recovery window using SkillCorner EPV;
5. Body Pose is used as an independent exploratory mechanism check for outward orientation readiness;
6. failed shortcuts and confounding checks remain in the public research trail rather than being discarded.

## Claims to avoid

- Do not say DRED is the first metric of defensive reorganisation or compactness.
- Do not say compactness itself is always beneficial or harmful.
- Do not claim that the second-last line is uniquely privileged; the post-submission audit also finds a positive association after last-line breaks.
- Do not describe the recovery-window EPV analysis as pre-specified; it was developed after Pretalx submission `8TTF3B`.
- Do not make causal or pre-break prediction claims.

A careful one-line positioning is: **DRED is an interpretable, line-break-triggered measure of whether a defence restores lateral coverage after penetration.**
