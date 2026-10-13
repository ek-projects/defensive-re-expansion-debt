# Analytics Cup judging readiness — internal

This is an internal readiness review for the five equally weighted Analytics Cup 2.0 criteria. It is not evidence and should not be presented as a judge score.

## Relevance

**State: strong.** DRED addresses the Football / Defensive Positioning theme directly and produces an episode-level diagnostic a coach or analyst can retrieve and compare after penetration.

Remaining emphasis: demonstrate the coaching workflow, not only the statistic — identify a high-DRED episode, compare it with a matched control and explain the recoverable behaviour.

## Methodology

**State: strong with explicit limits.** The frozen submission has 10 official Dynamic Events matches, within-match adjustment, match-level uncertainty, a Body Pose mechanism check and a documented failed shot-prediction shortcut. Post-submission hardening adds threshold/horizon sensitivity, leave-one-match/team-out checks, permutation controls, direction/placebo tests, richer context and recovery-window-aligned EPV.

Remaining limit: the dataset is still only 10 labelled matches and the aligned-window validation is post-submission. Keep causal language out.

## Originality

**State: defensible, not absolute.** Dynamic compactness and defensive reorganisation already exist in the literature. DRED's novelty is the specific line-break trigger + contextual lateral re-expansion debt + duration-normalised intensity + aligned EPV + Body Pose mechanism combination.

Use `docs/RELATED_WORK.md` and avoid “first ever” wording.

## Communication

**State: strong.** The submitted YouTube video is public, 59 seconds, and YouTube automatic captions confirm spoken English narration matching the intended script. The core story is simple: snapshot compactness misses whether the defence reopens after penetration. The current submitted video remains directionally correct, but the candidate README now explains the cleaner recovery-window validation.

Remaining opportunity: if a revised submission is published before the deadline, ensure the video and README tell the same validation story. Do not overload the one-minute pitch with robustness statistics.

## Open-source potential

**State: materially improved in v2 candidate.** The core DRED formula now lives in a provider-agnostic tested API (`compute_dred`, `contraction_excess`, `standardize_width`), not only in analysis scripts. The Makefile has explicit dependencies for rebuilding derived data and the adversarial analysis is reproducible.

Fresh-clone derived-data reproduction is now verified: 9/9 tests pass, post-submission JSON outputs match exactly and the generated aligned-EPV figure has the same SHA-256. A clean temporary virtualenv install also succeeds. The remaining publication gate is the public GitHub push, currently blocked by the connected GitHub integration's ref-write permission rather than by the repository itself.
