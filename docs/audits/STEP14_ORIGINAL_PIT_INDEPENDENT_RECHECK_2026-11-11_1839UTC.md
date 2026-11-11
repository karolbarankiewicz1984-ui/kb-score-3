# KB Score 3.0 — original Step14 PIT independent read-only recheck — 2026-11-11 18:39 UTC

Scope: original frozen 760 TRAIN / 380 VALIDATION, 121 numeric features + 38 missing flags, 2023/24–2025/26. This record adds independently fetched repository evidence only. It is **not** an attestation of historical provider publication times.

## Source and identity evidence

- Re-read `docs/STEP14_COMPREHENSIVE_HISTORIC_PREMATCH_RECONSTRUCTION_2026-10-28.md`: the original native fixture identity / kickoff / home-away / split crosswalk was reported 1140/1140, but it does not certify per-field historical PIT. Its 106/1140 historical public-source predecessor candidates are distinct from original PitchAPI fields.
- Re-read `docs/STEP14_ORIGINAL_STRICT_PIT_INDEPENDENT_RECHECK_2026-11-01.md`, `docs/audits/STEP14_INDEPENDENT_GATE_RECHECK_2026-11-07_1838UTC.md`, and `docs/STEP_14_PITCHAPI_FIRST_PUBLISHED_XG_AND_SAME_MATCH_SEMANTIC_AUDIT_2026-10-28.md`. Public historical FPL/Opta player-xG is not equivalent to PitchAPI native team-xG. No independently verifiable `first_available_at_utc` for original `match_id + team_id + period=All + expected_goals` was established.
- Existing historical public-source SHA and GHArchive lineage provides narrower evidence of published predecessor files; it does not prove historical availability of all original 159 PitchAPI-derived fields.

## Newly fetched observed run and persisted report (2026-11-11)

- [Historical PitchAPI multi-stat backfill run #43072486127](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/43072486127): GitHub Actions reports `success`, started 17:53:29 UTC.
- Read the committed `data/pit_sidecar/historical_multistat/2026-11-11/run-43072486127-1-b5/HISTORICAL_BACKFILL_REPORT.json`, whose source capture ended at 17:59:42 UTC. Its declared cumulative totals: 6080 historical match-stat observations, 5375 verified native xG observations, 8714 indexed finished fixtures, 1575 research targets with both teams' last-5 xG, 441 last-10 and 123 last-15. These counts cover multiple leagues and seasons and **are not** original 760/380 certified rows.
- The same persisted report explicitly declares `historical_pit_certified=false`, `original_2023_2025_provider_published_at_proven=false`, `official_training_allowed=false`, `protected_premier_league_test_accessed=false`, `research_training_performed=false`, `feature_report_is_reconstructed_not_provider_pit=true`. It records encrypted source payloads and SHA256 digests, but these prove current captured bytes, not their first historical publication.
- Other 2026-11-11 Actions success statuses (including #43021986260 native vector gate and #43055122984 hosted preflight) are execution results, **not** independent proof that the original historical 1140x159 PIT gate passed. No contrary original strict gate certificate was found in the examined records.

## Strict original decision

`GATE14_ORIGINAL_STRICT_NATIVE_PIT=PENDING`. Independently certified original full PIT rows remain **0/760 TRAIN and 0/380 VALIDATION**. Missing original historical per-field provider first-publication evidence and full independently audited frozen 1140x159 matrix. A successful research backfill cannot be relabeled as original PIT, and PASS of guard tests is not PASS of the historical reconstruction. Do not close original Step14; do not fit original M1; do not use protected TEST. No model, split, gate, source eligibility, credentials or provider configuration changed by this audit.
