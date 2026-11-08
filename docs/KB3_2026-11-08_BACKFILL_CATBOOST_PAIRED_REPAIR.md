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

### CI correction
- Commit 34b1134 fixes malformed literal newline escapes in the workflow audit step introduced in 72845b2. The preceding runs 42479993279 and 42480010827 failed workflow parsing (no jobs). New run 42480029331 is queued; end-to-end backfill remains UNVERIFIED.

## Owner direction — continue immediately without waiting for 150 samples (2026-11-08)

- Owner authorizes immediate research development, prospective data collection and same-fixture shadow comparisons; **not** relaxation of FIT/HOLDOUT independence, 90-minute freeze, leakage controls, protected TEST or Champion promotion gates.
- Existing `scripts/kb3_p1_prospective_six_train.py` already trains separate six-feature CatBoost on 1007 retrospective reconstructed TRAIN and 376 VALIDATION rows. This model is **not** formally trained on independently attested as-of v2 sources. It must not be represented as a newly verified 85-feature retrain.
- Existing `config/kb3_shadow_six_forward_activation.json` already has `enabled=true`, research-only, no retroactive forecasts, no Champion promotion; `.github/workflows/kb3-step16-m0-720-eight-forward.yml` has six daily scheduled slots for M0 and optional CatBoost Shadow Six, with Step17 Elo-only and original 85-feature CatBoost challengers separately. Avoid duplicate pipelines and unnecessary API usage.
- Continue using existing scheduled forecasts immediately; collect genuine host-attested future freezes and independently verified postmatch outcomes. Report separate exact triplet cohorts: (M0, Elo-only, original 85-feature CatBoost) vs (M0, Elo-only, six-feature research CatBoost) and never mix feature contracts/model versions.
- Formal Champion selection (step 8) is explicitly **DEFERRED** until enough paired independent future fixtures and weeks, proper uncertainty analysis and owner approval. A readiness report may be prepared immediately, but must state NO_PROMOTION.
- Backfill validation run 42480029331 was still in progress at last check; unresolved failures must be fixed before declaring step 1 complete.
- This entry is an operational decision and inventory of existing functionality, not proof of successful new prospective Shadow forecasts or retraining in this turn.

## Manifest bug fix and failure triage — 2026-11-08

- Commit `ccf6f8b8bb98b1e06b32325c0a30135e634d637f` fixes compressed snapshot manifest filename: `target.with_name(target.name+'.manifest.json')`, exactly matching restore and `git add` path `observations.sqlite.gz.manifest.json`.
- Run 42512371550 confirmed gzip compression of 110,510,080 raw bytes to 7,857,635 compressed bytes, then failed because the expected manifest path did not exist. This fix targets that demonstrated failure. **Re-run after this commit still required to verify persistence.**
- Run 42501013612 previously failed in the same commit step with `TypeError: 'int' object is not callable`; its prior revision is superseded, not evidence of a successful new run.
- Latest checked M0 settle run 42493640304: 3 new M0 settlements, 115 total; 23 Shadow Six rows, zero host-attested settled M0/Shadow Six pairs. Do not misreport M0 settlements as CatBoost paired evaluation.
- Next audit: inspect next history workflow conclusion and first genuine host-attested Shadow Six settled pairs; no promotion, no backdated forecasts.
