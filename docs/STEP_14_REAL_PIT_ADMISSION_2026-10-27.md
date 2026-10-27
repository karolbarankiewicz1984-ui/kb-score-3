# KB Score 3.0 — Krok 14: rzeczywisty audyt dopuszczenia TRAIN (27.10.2026)

## Wynik i kwalifikacja

**WYNIK AUDYTU: PASS dla integralności i blokady przecieków / DENIED dla rzeczywistego treningu M1.** To nie jest trening ani walidacja sportowa. **GATE14 nadal PENDING** i licznik ukończonych etapów to **13/29**.

Źródło: niezmieniony [manifest Step12](../data/splits/STEP12_NATIVE_REAL_SPLIT_2026-10-26.json) SHA256 `da387303645a9bb9476351044944e5465d178ddff689c96b579093c4fb4fce3a` oraz [SAFE model view](../data/splits/STEP12_SAFE_MODEL_VIEW_2026-10-26.json) SHA256 `3b8da84b334d897e327c883b769944bf36016cb44daf1da041bfb7d16a7b11e7`. **Odczyt danych 26.10.2026** nie jest niezależnym dowodem publikacji/obserwacji ich cech przed każdym historycznym meczem 2023–2026. Script `src/kb3_step14_real_pit_gate.py` odczytuje wyłącznie metadane TRAIN i VALIDATION. Nie przekazuje do CatBoost ani raportu z hashami zależnymi od etykiet, ani wyników meczu, ani kursów, ani jakiegokolwiek fragmentu TEST.

| Metryka | Wykonany rezultat |
| --- | ---: |
| Zamrożony TRAIN (2023/24–2024/25) | 760 |
| Historia TRAIN `RETROSPECTIVE / QUARANTINE` | 760 |
| W TRAIN brak potwierdzonego `feature_cutoff_utc` | 760 |
| TRAIN z udowodnioną historyczną dostępnością cech | **0** |
| Zamrożona VALIDATION (2025/26) | 380 |
| VALIDATION bez potwierdzonego `feature_cutoff_utc` | 380 |
| VALIDATION dopuszczona do realnej oceny M1 | **0** |
| TEST 2026/27 | 380 wg *agregatów* z poprzedniego bezpiecznego planu; **0 odczytów wierszy TEST i 0 etykiet** w tym audycie |
| Reprodukowany model CatBoost M1 na historycznym TRAIN | **NIE URUCHOMIONO — fail closed** |
| Rzeczywisty log loss / Brier / kalibracja M1 | **NIE DOSTĘPNE — brak legalnego treningu i walidacji** |

**Niezależny [GitHub Actions #40481190607](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40481190607): 9/9 testów PASS.** Testy symulują podmianę cutoff, zmiany flag dopuszczenia, próbę ponownego podpisania zmodyfikowanego raportu, wstrzyknięcie kursów/etykiet i naruszenie tożsamości terminarza. Każda taka manipulacja jest odrzucana. `check_real_fit_admission` odmawia jeszcze **przed wywołaniem CatBoost**. `no_lookahead_source_index_check=PASS_SCHEDULE_IDENTITY_ONLY` to nie to samo co pełny backtest `no_lookahead_actual_model_assessment=NOT_PERFORMED`.

## Potwierdzenie istniejących źródeł

W archiwum kopii zapasowych Google Drive KB Score 3.0 sprawdzonym 27.10.2026 znajduje się 19 plików; najpóźniejszy zapis źródłowy przechowywanego tam pakietu z audytu 12 pochodzi z **26.10.2026 15:07 UTC**. Starsze ZIP-y obejmują autentyczne obserwacje dnia 26.10, ale nie dowodzą historycznej publikacji sprzed kickoff dla TRAIN 2023–2025. Nie ma w tej kopii certyfikowanego zbioru cech treningowych z historycznymi snapshotami sprzed każdego spotkania. Sam ZIP zawiera materiał szyfrowany i nie został w tym kroku odszyfrowany.

## Dokładne wymagania, aby uruchomić realne M1 (bez zmiany 29-etapowego planu)

1. **Źródło prawdziwego as-of:** każdy historyczny rekord cechy musi mieć identyfikator spotkania, niezmienne `feature_cutoff_utc < kickoff_utc`, autentyczne źródłowe receipt/snapshot obserwowane **przed jego cutoff**, hash payloadu i kontrolę rozliczenia dostępności poprzednich wyników. Nie wolno tworzyć w 2026 r. fikcyjnych receiptów dla lat 2023–2025, ani traktować `kickoff+48h` jako rzeczywistego czasu publikacji. Jeżeli archiwalne receipt nie istnieją, budować zbiór prospektywny od dat rzeczywistego zbierania, z nowszą osobno zamrożoną wersją eksperymentu i bez naruszania obecnego TEST.
2. **Formalne dopuszczenie:** nowy niezależnie zbadany, podpisany manifest kwalifikacji, krzyżowy audyt IDs/UTC/hash-chain, pełna dokumentacja braków xG (w tym częściowego pokrycia), dokładne separacje TRAIN/VALIDATION/TEST i potwierdzenie braku kursów i wyniku meczu docelowego w feature matrix. Dotychczasowych źródeł z `training_allowed=false` nie przerabiać przez zmianę flagi.
3. **Właściwy CatBoost M1 i ewaluacja:** deterministyczny fit i hash .cbm *tylko* na zatwierdzonym TRAIN, seedy/konfiguracja przed odczytem VALIDATION, zamrożone P 1/X/2 przed odczytem prawdziwych etykiet i porównanie multiclass log loss, Brier oraz stabilności/calibration w czterech uzgodnionych foldach. TEST chroniony do odrębnego odbioru, bez hiperparametrów dobieranych na TEST. Nie wybierać produkcyjnego czempiona ani zakładów bez dodatkowej decyzji użytkownika.

## Granica uczciwości

Możliwe jest policzenie retrospektywnych cech z prawdziwych wyników i hipotetycznego opóźnienia, lecz **nie** spełnia to rygorystycznie zamrożonej polityki potwierdzenia PIT i **nie** będzie dziś przedstawiane jako rzeczywisty model bez przecieków. Odrębny eksperyment badawczy wymagałby oznaczenia `RETROSPECTIVE_RESEARCH_NOT_PIT`; nie może znieść istniejącej blokady `GATE14`.

**Decyzja automatycznej bramki:** `real_catboost_train_allowed=false`; `real_catboost_model_fitted=false`; `real_validation_metrics_available=false`; `gate14_pass=false`. Projekt pozostaje w kroku 14.
