# Contributing to DRED

DRED is intended to remain a small, interpretable football-tracking metric rather than grow into a hidden modelling pipeline.

## Development setup

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
make install
make test
make release-audit
```

## Project boundaries

- The reusable metric lives under `src/defensive_recovery/`; competition-specific analysis belongs in `scripts/`.
- Primary submission workflows are pinned to the 10 new Dynamic Events match IDs. Explicit research workflows may use only the frozen 20-match Analytics Cup tracking set (current + prior edition) in `defensive_recovery.competition`; arbitrary external match IDs are not allowed.
- Never commit competition datasets, downloaded tracking, Body Pose archives, generated video, or derived `outputs/`.
- Changes to the DRED formula must include unit tests and an explicit note about numerical compatibility with the frozen competition definition.
- Statistical extensions should preserve negative/confounded findings and avoid causal or pre-break prediction claims unsupported by the design.

## Before opening a change

Run `make test` and `make release-audit`. For analysis changes, also run `make hardening` from a fully prepared competition-data environment. GitHub CI checks the package and tests on supported Python versions; the manual full-reproduction workflow rebuilds the official 10-match analysis.
