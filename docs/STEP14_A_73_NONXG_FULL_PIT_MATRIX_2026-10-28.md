# Step14 A — full original 1140×73 non-xG PIT audit, 2026-10-28

**CI verified:** [real workflow #40738870670](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40738870670) **SUCCESS**, 6/6 tests, full gzipped source matrix uploaded as artifact `KB3_STEP14_A_REAL_1140_NOXG_FIELD_PIT_MATRIX`.

The exact frozen original Step12 safe manifest SHA `3b8da84b334d897e327c883b769944bf36016cb44daf1da041bfb7d16a7b11e7` provides **760 original TRAIN + 380 original VALIDATION** match IDs and kickoffs; TEST entries skipped. The frozen Step11 field contract has 121 numeric fields +38 missing flags, of which **73 numeric fields +14 missing flags do not depend on xG/xGA**. Actual **1140×87 = 99,180** per-field/flag availability cells were independently recorded and exported to the Actions artifact; no target results, odds, secret, xG numeric values or TEST labels used.

Each cell is **`NO_NATIVE_PER_FIELD_HISTORIC_PUBLISHED_AND_CAPTURED_RECEIPT`**, with `original_cutoff=null`. Known authentic public snapshot timestamps (October/December 2023, May 2024, October 2024, July 2025) were indexed as **possible external prior sources** only, never silently approved as original PitchAPI native team data. Observed counts of rows with 0/1/2/3/4/5 older public snapshot candidates: **70/70/240/60/320/380**. They establish only temporal source existence and never prove matching original native fixture/team IDs, exact previous form/goal values or historical publication/capture for each feature.

**A implemented and run successfully as an audit, not as real CatBoost training.** 0/760 officially eligible original TRAIN, 0/380 VALIDATION. **M1_BEZ_XG not fitted.** Retroactively inventing cutoff times or approving data from a 2026 capture is expressly prohibited. Further work requires old valid per-team/fixture receipts and fit-admission gate; exploratory research CatBoost without PIT exists separately from original M1.

**Status formal:** 13/29, GATE14 PENDING. No changes to original M0, 20 frozen predictions, TEST or frozen split.
