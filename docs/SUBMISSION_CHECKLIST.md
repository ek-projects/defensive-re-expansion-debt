# Submission Checklist

## Verified submission status — 2026-10-13

- Pretalx receipt confirmed by official email.
- Proposal code: `8TTF3B`.
- Submitted project title: **Defensive Re-Expansion Debt (DRED)**.
- Submitted GitHub URL: `https://github.com/ek-projects/defensive-re-expansion-debt`.
- Submitted YouTube URL: `https://youtu.be/qDVTA8S03HE`.
- Submission snapshot commit: `55b0d829ff36918d2980d00266ced74c7a5c5d28`.
- Local annotated freeze tag: `submission-8TTF3B`.
- Post-submission Body Pose end-to-end revalidation completed successfully on 2026-10-13; numerical results reproduced.
- Post-submission EPV robustness audit completed on 2026-10-13 on isolated branch; 20/20 threshold × horizon combinations positive and all 10 leave-one-match-out estimates positive.
- Post-submission adversarial/temporal audit completed on 2026-10-13; aligned-window net EPV adjusted r=0.224, median match r=0.209, positive in 9/10 matches. This is post-submission evidence only.
- Submission-v2 candidate exposes DRED as a provider-agnostic tested Python API; one-match integration regeneration shows zero numeric drift in DRED outputs.
- Fresh-clone derived-data smoke test completed: 9/9 tests, robustness/adversarial JSON identical, aligned-validation figure SHA-256 identical.
- Clean temporary virtualenv install completed successfully; package import and API smoke test passed.
- GitHub deploy-key publication path verified; `submission-v2-candidate` is public while `main` remains frozen.
- Competition-grade CI added for Python 3.11–3.14 plus wheel build/clean-install smoke test.
- Manual full-reproduction GitHub workflow added for the official 10-match pipeline.
- Release audit added: README limits, MIT licence, no tracked competition data/media, and no wider-match execution path.
- V2 executable data scope hard-pinned to the 10 official match IDs.
- Current documented status: **received / awaiting review**; receipt is not acceptance or finalist selection.

## Repository

- [x] Primary metric frozen: Defensive Re-Expansion Debt (DRED).
- [x] Duration-normalized DRED intensity implemented.
- [x] Primary scope frozen: 10 official Dynamic Events matches.
- [x] Official match IDs encoded in one shared module.
- [x] Raw competition data excluded from Git.
- [x] Tracking downloads verified against Git-LFS hashes.
- [x] Optional Body Pose downloads verified against published SHA-256.
- [x] Core tests passing.
- [x] Original failed multivariate metric documented.
- [x] Shot-link duration confound documented and demoted.
- [x] EPV validation implemented.
- [x] Body Pose mechanism check implemented.
- [x] Public GitHub remote created: https://github.com/ek-projects/defensive-re-expansion-debt
- [x] Fresh public clone reproduction test (5/5 tests passed).

## Evidence

- [x] EPV sample: 603 second-last-line-break player possessions, 10 matches.
- [x] Adjusted pooled partial-rank association: 0.174.
- [x] Median per-match partial association: 0.154.
- [x] Match-bootstrap 95% interval: 0.044–0.268.
- [x] Positive direction in 8/10 matches.
- [x] Body Pose direction consistent in both available matches.
- [x] Shot audit retained as secondary negative/confounding result.

## README / video

- [x] V2 README competition check: 872 words, 2 figures, 0 tables.
- [x] Video script rewritten around EPV + Body Pose.
- [x] 58.5-second 1080p visual cut generated reproducibly.
- [x] Participant-voice mux/normalisation pipeline implemented and tested.
- [x] Matched case-study visual available for video.
- [x] Submitted public video contains spoken English narration matching the script (verified through YouTube automatic captions). Speaker identity is not machine-verifiable; competition rules require participant/teammate voice.
- [x] Submitted YouTube video is public and 59 seconds.
- [ ] Check readability on mobile.

## Submission

- [ ] Confirm Europe / Football in Pretalx.
- [x] Paste public repository URL.
- [x] Add public video URL.
- [ ] Re-check rendered README from GitHub.
- [x] Submit before 18 December 2026 — received by Pretalx on 13 October 2026 (`8TTF3B`).
