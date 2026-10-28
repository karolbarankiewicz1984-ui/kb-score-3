# KB Score 3.0 — Step14 owner-only RSA: score-equivalence and Elo input audit (28 Oct 2026)

**Stage:** research, owner-local only; original frozen 760 TRAIN / 380 VALIDATION / TEST partition and M0 remain unchanged. GATE14 PENDING. No CatBoost M1 fitting.

## Just observed: original owner-local encrypted-archive join

After the verified original 1140/1140 native schedule check, owner executed `scripts.step14_multiseason_owner_native_join_local` on their own Windows using the original RSA PEM and original sealed ZIP. The user-supplied PowerShell screenshot displays a success return and aggregates:

| Season / old blob | Native matches matching the source condition |
|---|---:|
| 2023/24 October FPL | 8 |
| 2023/24 December FPL | 8 |
| 2024/25 October OpenFootball | 10 |
| 2025/26 July OpenFootball | 0 |

**26 source-snapshot-to-native-fixture pairs, NOT a guaranteed 26 unique training targets and NOT full PIT evidence.** Both FPL snapshots report `ORIGINAL_RSA_NATIVE_CLOCK_FINGERPRINT_BIJECTION_CHECKED`. The owner-side aggregate JSON is **not** available here and its contents have not been independently read; therefore the project archive only records counts visible in the screenshot. [Unclassified aggregate-only record](../data/audits/STEP14_OWNER_LOCAL_FORM5_NATIVE_JOIN_SCREEN_AGGREGATE_2026-10-28.json). No PEM, native IDs or FT values were transferred.

## Next additional control: compare historical old public scores with sealed original PitchAPI scores

Code: `src/kb3_step14_private_results_equivalence.py`; local Windows runner: `scripts/step14_owner_native_score_elo_local.py`; pure synthetic tests: `tests/test_step14_private_results_equivalence.py`; workflow: `.github/workflows/kb3-step14-owner-ft-elo-unit.yml`.

The new code:
1. Fetches three historical SHA-256 pinned public snapshots before decrypting the ZIP: FPL 05 Oct 2023 (70 prior FT), FPL 04 Dec 2023 (140 prior FT), OpenFootball 02 Oct 2024 (60 prior FT). Exact SHA/content provenance already separately corroborated using historical GH Archive PushEvents.
2. Verifies unchanged original ZIP hash, RSA-AES-GCM receipts and 1140 native fixture identities. Builds an in-memory whitelist of **only those PREDECESSOR native IDs whose FT was present in the authentic old public snapshot**. Reads the original FT scores **only for these whitelisted TRAIN predecessor IDs**; does **not** inspect target match scores, VALIDATION scores or TEST values.
3. Requires strict same fixture/team/UTC mapping and exact 90-minute scores for every earlier public FT. A mismatch blocks promotion; no score or ID is logged or exported.
4. If both 2023 score sets match, replays the original frozen Step11 Elo mathematics in chronological simultaneous-kickoff batches (initial 1500, K20, home 65, scale 400; retention .85 unused *within* initial 2023/24 season). For each candidate requires absence of an unpublished intervening native prior fixture for either club. **No Elo numbers are exported or treated as model-ready features.**
5. The old 2024/25 source can check 60 prior FT but **cannot** prove the full preceding 2023/24 380-match Elo chain without independent historical pre-match evidence; historical xG requires a separate source with matching team semantics and real publication clocks, not later or FPL player-xG values.
6. Writes a new, private aggregate-only JSON *outside the GitHub repo*, without any original match scores, future target labels, private IDs, cryptographic keys, odds or source payloads. Exactly zero paid API requests.

### Windows next step after downloading latest `main`

From the unpacked repository folder:

```powershell
py -3 -m scripts.step14_owner_native_score_elo_local --archive-zip "$HOME\Downloads\KB3_PITCH_PL_2023_2026_NATIVE_20261026.zip" --private-key "$HOME\Desktop\KB3_760_PAKIET_ODZYSKIWANIA_POUFNE\KB3_760_KLUCZ_ODZYSKIWANIA.pem" --output "$HOME\Desktop\KB3_STEP14_PRIOR_FT_ELO_AGGREGATE.json"
```

**Expected structure, never assumed outcome:** each source prints `PREVIOUS_FT`, `EXACT_NATIVE_FT`, `DISAGREEMENTS`, optional `PUBLIC_ELO_FORM5_TARGETS`, `STATUS`. Success or a strict mismatch must be inferred from actual on-PC output only. No result reported as PASS prior to execution.

**Current original PIT eligibility remains 0/760 TRAIN, 0/380 VALIDATION, 13/29, GATE14 PENDING.**
