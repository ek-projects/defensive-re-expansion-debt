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

Fresh-clone derived-data reproduction is now verified: 10/10 tests pass, post-submission JSON outputs match exactly and the generated aligned-EPV figure has the same SHA-256. A clean temporary virtualenv install also succeeds. The v2 candidate is published on its own GitHub branch with a repository-scoped deploy key. CI covers Python 3.11–3.14, wheel build/install smoke testing and a submission-constraint audit; a manual workflow reproduces the full primary 10-match pipeline. Primary evidence is pinned to the 10 new Dynamic Events matches, while explicit research targets are limited to the frozen 20-match Analytics Cup tracking set across current/prior editions.


## 2026-10-13 competition-grade gate

- README: 872 words, 2 figures, 0 tables.
- Licence: MIT; package metadata uses SPDX `MIT`.
- Base package dependency: NumPy only; analysis stack is optional/development metadata.
- Automated release audit rejects tracked competition data/media and wider-match execution paths.
- Public CI definition: Python 3.11–3.14 tests + release audit + wheel build/isolated-install smoke test.
- Manual full-reproduction workflow: official 10-match rebuild + robustness/adversarial audit, with Body Pose optional.
- The historical 20-match tracking exploration is reproducible through explicitly named research targets and remains separate from the 10-match primary evidence. The 20-match whitelist corresponds to Analytics Cup current/prior tracking data; arbitrary external matches are rejected.
