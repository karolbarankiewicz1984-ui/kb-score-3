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

## Implementation update — 2026-11-08

### Steps 1–4
1. **Backfill oversized SQLite**: workflow changes f266df3, c2f7b8d. Gzip+SHA-256 persistence and restore; pending full end-to-end verification. Watch for compressed blob size and next-run reconstruction; do not mark CLOSED until verified.
2. **CatBoost feature parity**: 44c978c adds `require_paired_catboost_85_contract` on existing `src/kb3_p1_shared_asof_features_v2.py`. Enforces same as-of, 85 feature names/order/values/hash in research only. Old frozen 48h M1-R weights remain NOT approved for 3h forward semantics. New fitted model requires later training; no Champion change.
3. **Exact same-game model comparison**: 30a2cf4 extends `src/kb3_step17_engine_comparison.py` with `exact_three_engine_comparison`, per-league same-triplet metrics, Brier/log loss/accuracy and ISO-week paired uncertainty. Existing strict host-attested comparison remains intact; missing triplets must not be invented.
4. **Historical quality**: f6bd626 adds `scripts/kb3_history_readonly_quality_gate.py` (scope coverage, missing stats, publication proof counts, DB SHA/integrity); 72845b2 adds it to offline workflow. Historical data remain research-only, not retrospective certified PIT.

**Validation:** new GitHub Actions runs triggered; pending confirmation of successful job conclusion and artifact contents. Do not claim steps production-verified before that.

### Steps 5–8 — registered backlog, NOT executed
5. **Research CatBoost retraining:** fit a NEW version on shared as-of v2 features only after strict independent source/feature parity review. Freeze train/validation splits and keep historical protected TEST sealed; record feature contract SHA, calibration, Brier and log loss against M0.
6. **Parallel SHADOW:** freeze M0, Elo-only, new CatBoost predictions on identical future fixture keys with real GitHub host evidence at least 90 minutes before kickoff. Append-only storage; no retroactive forecasts.
7. **M0 calibration:** continue prospective real settled sample collection toward 100 FIT and separate 50 HOLDOUT; no automatic activation before gates. Last verified actual M0 postmatch total 37 on 2026-11-08.
8. **Champion selection:** after sufficient independent matches/weeks and paired improvement with uncertainty intervals, audit feature leakage and request owner approval. Until then M0 unchanged; no automatic Champion promotion.
