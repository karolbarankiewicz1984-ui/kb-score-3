# Original strict historical PIT — independent read-only recheck, 2026-11-03 18:17 UTC

Scope: original 121 numeric features + 38 flags, frozen 760 TRAIN / 380 VALIDATION, native provider first-publication evidence. No TEST or original M1 training.

## Evidence actually re-read
- Original contract: `docs/STEP14_COMPREHENSIVE_HISTORIC_PREMATCH_RECONSTRUCTION_2026-10-28.md`; independent 2026-11-01 recheck: `docs/STEP14_ORIGINAL_STRICT_PIT_INDEPENDENT_RECHECK_2026-11-01.md`.
- Historical fixture identity was reported as 1140/1140 verified in original run 40745602928; this does not certify 159 fields per fixture.
- Original strict PIT independently documented as **0/760 TRAIN and 0/380 VALIDATION**. No subsequently inspected evidence certifies provider-native first publication of `match_id + team_id + period=All + expected_goals` prior to historical kickoff.
- Fresh GitHub Actions API GET `/repos/karolbarankiewicz1984-ui/kb-score-3/actions/runs?per_page=30` at 2026-11-03 18:17 UTC: research-only xG5 ablation run 41691844430 completed success; eight-league M0 research 41672457360 success; historical multi-stat backfill 41665018210 success; M0 postmatch settlement 41664332685 success; Step14 native observed-at xG archive 41635067083 success. These are **not** original native historical first-published-at certificates. Workflow success is not GATE14 PASS.
- Most recent commits at this check include 04388240 (research xG5 pilot), 5a7ee0a (480 source matches, 87 card recoveries, persistent native xG discrepancies), b32b41d (observed multi-stat source batch). Their titles and observed-at backfill cannot retroactively establish provider publication times in 2023–2025.

## Decision
`GATE14_ORIGINAL_STRICT_NATIVE_PIT=PENDING`. Certified original full 159-field rows: TRAIN 0/760, VALIDATION 0/380 **as last independently documented**, not a fresh recomputation of the full matrix. Do not fit original M1; do not access TEST; do not conflate separate relaxed/research gates. No new native first-publication evidence found in this read-only check. Additional original native receipts are still required; do not invent publication timestamps.

This file records an independent inspection of repository documents, recent commits and actual Actions run conclusions; it does not claim to independently validate all raw archived artifacts.
