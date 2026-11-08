# KB Score 3.0 — backfill / feature parity / paired comparisons (2026-11-08)

## Confirmed incident and applied fix
- Run 42465151468 failed pushing `data/research/historical_multistat/observations.sqlite` at 105.39 MB; GitHub rejects files >100 MB.
- Commits f266df3654a6a17dd994a3cbb6a7bfb347188a05 and c2f7b8d5cd4124f48e1c7048c3cdb235efe857f0 add verified compressed SQLite persistence and restoration in historical backfill workflow.
- This is not yet verified end-to-end. Verify compressed size, Git push, next-run restoration, SQLite integrity and unchanged source row count. Compression can fail if archive remains >=95 MB; then use chunking or durable object storage rather than silent loss.

## CatBoost training/forward feature parity — required gate
- The 2026-11-08 Step16-18 gate reports `P1_01_TRAIN_48H_VS_FORWARD_3H_FEATURE_SEMANTICS` for CATBOOST_NO_XG. Do not change training window or forward window independently.
- Before training/activating CatBoost, produce a shared versioned feature contract: feature names, units, source, timezone, cutoff relative to kickoff, missingness, historical availability, calculation and ordering; require exact contract hash in train and forward artifacts.
- Reconstruct train and forward features using the same as-of cutoff semantics, freeze before kickoff, reject leakage, and run deterministic parity tests on matched fixtures. Until tests pass CatBoost stays SHADOW_DIAGNOSTIC_ONLY.

## Same-fixture M0 / Elo-only / CatBoost comparison
- Existing read-only `scripts/step17_offline_three_engine_audit.py` already checks frozen M0 proofs, challenger hashes, pairwise and three-way intersections. Extend its report only on the same exact fixture keys with verified outcome and pre-match probability snapshots.
- Report per engine: unique fixture count, paired Brier multiclass, log loss, reliability/calibration, paired deltas, confidence intervals clustered by ISO week, and per-league coverage. Include abstentions and missing features, never fill missing predictions retrospectively.
- The Step16-18 daily gate still reports insufficient paired matches and independent weeks. No Champion promotion, recalibration or official deployment until gates pass and owner approves.

## Status
- Backfill: code fix committed, validation running.
- CatBoost: feature-parity defect identified; NOT FIXED in model code yet.
- Three-way comparisons: existing strict audit verified in source; extension NOT IMPLEMENTED yet.
