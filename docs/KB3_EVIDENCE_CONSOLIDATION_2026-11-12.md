# KB3 — evidence consolidation and V3 readiness, 2026-11-12 (RESEARCH ONLY)

## 1. Original 23 M0 / Shadow Six pairs — ALREADY SETTLED
Source: [run 42547104765](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/42547104765), successful jobs. Prior register docs/KB3_2026-11-08_BACKFILL_CATBOOST_PAIRED_REPAIR.md explicitly records 23/23 same-fixture host-attested settled pairs on 2026-11-09.
M0: top1 14/23; Brier sum3 0.5621912012; log loss 0.9516386707; ECE 0.1755385582.
Six-feature Shadow: top1 15/23; Brier sum3 0.5599529955; log loss 0.9449020152; ECE 0.1976834490.
Differences (Shadow minus M0): Brier -0.0022382057; log loss -0.0067366555; ECE +0.0221448908. Descriptive only; n=23, no valid Champion selection. DO NOT repeat settlement or confuse with 85/87-feature models.

## 2. Prior experiments — no retraining authorized
- Retrospective research CatBoost: [run 41915259711](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/41915259711), 1007 TRAIN / 376 VALIDATION, historical reconstruction, NOT original PIT. 14-feature no-xG: Brier 0.6410348466, log loss 1.0629033841, accuracy 0.4414893617, ECE 0.0227643078. 18-feature xG: Brier 0.6445418321, log loss 1.0686233758, accuracy 0.4228723404, ECE 0.0517653486. No direct numerical comparison to the forward 23 because cohorts and feature contracts differ.
- Historical M0-720 vs other engines: previously studied on 374 historical validation matches, with separate contracts; not pooled into the 23 prospective Shadow Six pairs.
- Existing offline exact-three-engine comparator: scripts/step17_offline_three_engine_audit.py, reads source SQLite immutable, uses temporary copy, requires host proofs and exact fixture intersections. Latest exact-triplet count/metrics NOT independently recalculated in this review. Step18 [run 42553835471](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/42553835471) job SUCCESS is not gate PASS.
- Legacy 85-feature CatBoost has TRAIN +48h vs FORWARD +3h feature-semantic mismatch. Research gate exists; old weights are NOT approved. 87-feature V3 native builder has zero real forward verified targets as of [run 43037646607](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/43037646607).

## 3. V3 readiness without PitchAPI
- [run 43037646607](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/43037646607): source_count=6, target_count=0, 7 provider calls in the EXISTING run, 0 provider failures; zero builder-verified forward 87-vectors. 96h horizon during international break is a plausible explanation, NOT proof that selector is correct.
- Introduce a separate research-only offline readiness diagnostic with explicit NO_FIXTURES_IN_WINDOW versus SELECTOR_MISMATCH and proof-required statuses. No changes to daily source capture.
- Exact per-fixture cutoff must use kickoff minus 90 minutes and independently hosted source timestamp strictly before cutoff; absent timestamp/fixture yields BLOCKED, never PIT TRAIN.
- No API, no workflow dispatch, no new FIT, no changes to M0/Champion/TEST.

## 4. Remaining checks and decisions
1. Run research-only offline tests in CI on this branch; until CI is observed, TESTS_NOT_CI_VERIFIED.
2. Obtain current immutable read-only Step17 same-fixture exact-triplet report and compare per model, per week, per league. Do not fabricate counts.
3. At next genuine league fixture entering 96h horizon, inspect existing scheduled capture and native original-builder host attestation. Never force paid PitchAPI calls.
4. Retain GATE16/GATE17=PENDING; formal PIT TRAIN=0 until independently certified; no model promotion.

This report consolidates existing evidence and explicitly does not claim new training, new settled matches or successful CI of new tests.
