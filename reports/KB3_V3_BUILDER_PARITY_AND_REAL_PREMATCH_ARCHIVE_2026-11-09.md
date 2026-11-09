# KB3 CatBoost 87 — weryfikacja zgodności buildera i rzeczywistego archiwum (09.11.2026)

## 1. Zgodność oryginalnego buildera

Przeanalizowano oryginalne źródła na branch `research/catboost-contract-v3`: `contracts/kb3_catboost_asof_v3.json` (87 cech), `src/kb3_p1_shared_asof_features_v2.py`, `src/kb3_features.py`, `src/kb3_catboost_research_v3.py`, `src/kb3_step11_field_audit.py`, `tests/test_kb3_p1_shared_asof_features_v2.py`, oraz rzeczywisty lokalny skrypt eksperymentu `train_retro_87.py`.

**Dwa różne twierdzenia:**
1. Oryginalny builder TRAIN/FORWARD jest wspólny: istniejące testy `test_true_same_asof_train_forward_same_features_hash_lineage` sprawdzają równość canonical feature SHA, wektorów, braków, lineage i zegarów na syntetycznych danych. Widziano sukces workflow `KB3 P1 shared as-of TRAIN FORWARD v2 - isolated offline CI` z 09.11 06:27 UTC (run `42573117892`). To potwierdza **wewnętrzną** parytetowość buildera na testach.
2. Osobny retrospektywny `train_retro_87.py` nie wywołuje `build_shared_features` ani `verified_view`, nie posiada niezależnie zaświadczonych `target_receipt` i `result_receipt`, nie buduje per-feature availability/lineage. **Nie wykazano** pełnej zgodności wektorów tego modelu z oryginalnym builderem. Samo 87 nazw i identyczny podział TRAIN/VAL nie dowodzi zgodności wartości. Status `RETRO_87_TO_V3_PARITY=UNPROVEN`, `OFFICIAL_V3_MODEL=NOT_TRAINED`.

Nie wolno podpinać retrospektywnego `CATBOOST_RETRO_87_FEATURES_NOT_PIT.cbm` do oficjalnego buildera ani uruchamiać go jako certyfikowany Shadow.

## 2. Rzeczywisty niezależny hostowany materiał dla przyszłych meczów

Pobrano rzeczywisty GitHub Actions artifact **13619490089**, run **42484728241**, utworzony **2026-11-08T13:23:56Z**, `KB3_3_LEAGUE_DAILY_REAL_PIT_ENCRYPTED_OBSERVATION`. Wewnątrz SQLite `forward_m0/kb3_forward_m0.sqlite`, `m0_forward_feature_records` ma **8** wpisów z `snapshot_day_utc=2026-11-08`: **ESP 4, ITA 2, GER 2**. W każdym `captured_before_kickoff_utc=2026-11-08T13:23:54.767235Z`, host artifact utworzony przed kickoff. Najwcześniejszy kickoff 2026-11-08T15:15:00Z (ponad 111 minut po host-created); pozostałe późniejsze. Tym samym **8/8** rekordów zarchiwizowano na serwerze przed kickoff i co najmniej 90 min przed kickoff. Są to **rzeczywiste przedmeczowe rekordy innego, istniejącego kolektora M0**, nie zweryfikowane wektory 87 cech.

Archiwum zawiera zaszyfrowane `THREE_LEAGUE_DAILY_SOURCE.enc` i receipt; ostatni receipt deklaruje 43 wywołania API, 18 nowo zaobserwowanych par statystyk, 8 frozen feature snapshots. Pierwszy czas publikacji dostawcy nieznany. Brak odszyfrowania natywnego payloadu, sprawdzenia każdego native source member SHA względem pre-cutoff i transformacji do wejścia `verified_view`. **Formalnie dopuszczone do v3: 0**.

Zastany workflow `.github/workflows/kb3-pitchapi-three-league-daily.yml` ma schedule `17 6 * * *`, a `kb3-step14-c-native-asof-daily.yml` `42 4 * * *`, `workflow_dispatch`, i zapisują szyfrowane dowody do GitHub Actions; nie trzeba mnożyć kosztownych wywołań API. W dniu 09.11 w sprawdzonych najnowszych runach nie znaleziono jeszcze nowego udanego uruchomienia tych konkretnych kolektorów; nie wolno nazywać archiwum z 08.11 nową prognozą na 09.11.

## 3. Decyzja

- `ORIGINAL_BUILDER_TRAIN_FORWARD_TEST_PARITY=PASS_SYNTHETIC_CI`.
- `RETRO_87_TO_ORIGINAL_BUILDER_VECTOR_PARITY=UNPROVEN`.
- `REAL_INDEPENDENT_PREMATCH_ARCHIVE=YES_8_M0_RECORDS_NOV08`.
- `V3_VERIFIED_NATIVE_INPUT=NO`, `V3_NEW_FROZEN_SHADOW=0`, `V3_OFFICIAL_TRAINING=NOT_TRAINED`.
- `M0/CHAMPION/TEST=UNCHANGED`.

**Do ukończenia:** kontrolowane fixture-by-fixture parity wartości 87 cech na oryginalnym `build_shared_features` vs niezależnej implementacji przy dokładnie tych samych receiptach; zweryfikowane native response bytes i ich rzeczywiste czasy hostowania, następnie nowy przedmeczowy Shadow po czasie treningu. Nie wolno sztucznie dopisywać provider publication timestamp.
