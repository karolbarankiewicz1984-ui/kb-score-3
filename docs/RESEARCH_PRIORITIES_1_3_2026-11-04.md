# KB Score 3.0 — trzy priorytety badawcze w czasie zbierania FIT (04.11.2026)

**Dyspozycja właściciela:** skupić się na (1) zgodności TRAIN/forward, (2) jakości historii xG i formy, (3) uczciwym porównaniu M0 / Elo-only / CatBoost. Nie uruchamiać jeszcze pełnego KB3 TEST ani trzech PDF. Ten dokument rozpoczyna **audyt i wykonanie planu badawczego**; nie jest odbiorem żadnej bramki, zakończeniem naprawy ani zgodą na samowolne wdrożenie kodu.

**Zakres i ograniczenia:** brak zmian istniejących parametrów M0, CBM, immutable forecasts, zamrożonego ENG Premier League 2026/27 TEST, baz i artefaktów; brak backfillu po fakcie jako pozornej prognozy przedmeczowej. Żadnego nowego API, płatnego planu ani klucza prywatnego z powodu tego wpisu. GATE16/GATE17=PENDING, formalny harmonogram 15/29. Kalibracja M0: 100 autentycznych FIT jednej wersji, a po pierwszym fit 50 **nowych** HOLDOUT. W badaniach wolno oceniać wyłącznie rozłączne i odpowiednio opisane próby, bez automatycznej promocji Championa.

## Weryfikacja stanu wejściowego — źródła i ustalenia

- **P1-01 faktycznie OTWARTY.** W `src/kb3_features.py` kod zawiera `RESULT_LAG=3h`, `REPLAY_LAG=48h` i `days_since_last_kickoff=(cutoff-last_kickoff)`. W `scripts/step14_m1r_recompute_1140_relaxed_48h.py` historyczny M1-R używa `LAG=48h` i `days_since_last_kickoff=(target kickoff-last_kickoff)`. Ten kontrast może zmieniać dostępne poprzedniki i wartości cech. PR #149 jest MERGED i fail-closed blokuje nieuprawniony awans CatBoost, ale **nie ujednolicił** czasu i definicji. #143 jest nadal DRAFT/NO-GO. P1-02 historycznej kalibracji: starszy 3-league FIT pozostaje bez niezależnego host proof; nie uznawać starych 100 syntetycznych/niepoświadczonych za FIT.
- **Historia, rzeczywisty run 41882339782 (04.11.2026)**: `ACCELERATED_CAPTURE_REPORT.json`: 5 paczek, 229 nowych meczów ze statystykami, 191 dodatkowych zweryfikowanych xG, stan 1525 obserwowanych match-stats / 1363 zweryfikowanych native xG, 162 niezweryfikowane xG. `ROLLING_AFTER_RECHECK.json`: 1525 rozpatrzonych celów; **654 pełne pary core5**, **271 pełnych par xG5**, **39 xG10**, **6 xG15**. W tym raporcie 162 rozbieżności `XG_SHOTS_STATS_DISAGREE`, bez ich dopowiadania lub nadpisywania. To liczby retrospektywne; `retrospective_provider_original_publication_proven=false`, `full_feature_training_approved=false`. UCL jest osobnym scope bez domniemanego mapowania klubów.
- **Porównanie modeli**: #144 DRAFT/RESEARCH: 942 retrospektywne mecze / 19 tygodni na wspólnym zbiorze: M0_FIXED720_REPLAY Brier sum3 0.596539, log loss 1.000187; CatBoost A no-xG 0.589255 / 0.990083; B xG5 0.590495 / 0.991630; C rozszerzony 0.591913 / 0.993788. CI95 delt strat obejmuje zero, xG nie wykazał poprawy. Te predykcje to **historyczny REPLAY, nie autentyczny przedmeczowy freeze**. Drugi realny ablation `STEP17_XG5_ABLATION_41745081578_1.json`: 109 TRAIN / 47 VALIDATION i tylko 5 tygodni; xG5 Brier gorszy od no-xG. Faktyczne prospektywne sparowane rozliczenie M0+Elo-only+CatBoost no-xG na ostatnim receipt: **1 wspólne spotkanie**, za mało do wniosku. M0 ostatni potwierdzony stan 126 zamrożonych / 74 kwalifikujące FIT, 0 HOLDOUT — aktualizować z prawdziwych kolejnych receipts, nie traktować jako ciągle bieżącej liczby.
- **Nie dublować kodu**: istnieją `src/kb3_historical_feature_quality.py` (rzeczywiste ostatnie 5/10/15), `src/kb3_step17_engine_comparison.py` (same fixture, metryki, tygodniowy bootstrap), `src/kb3_step17_forward_challengers.py` (równoległy immutable Elo-only/CatBoost no-xG), a także eksperymenty #144 i selektor #145 (oba draft).

## Tor 1 — P1-01: TRAIN ↔ forward (najwyższy priorytet)

**Stan:** AUDYT KODU WYKONANY / NAPRAWA NIEROZPOCZĘTA / NO-GO AWANSU CATBOOST.

1. Wprowadzić na izolowanej gałęzi **jedną wersjonowaną specyfikację cech**: dokładna chwila `target_kickoff`, rzeczywisty `feature_capture_cutoff`, dostępność wyniku poprzednika, `days_since_last_kickoff`, Elo, forma all/venue 5/10/15 i braki NULL/maski. Rozróżnić oryginalne source observed/published od retrospektywnego heurystycznego lag.
2. Zbudować **read-only delta-audit** na tych samych meczach: lista predecessor IDs i cutoff, liczba rozbieżnych cech, porównanie TRAIN48h vs forward3h; osobno wskazać przypadki niedostępnego źródła/first published. Nigdy nie naprawiać historycznych zapisów podmianą dat.
3. Dopiero po audycie przygotować poprawkę liczenia cech i testy graniczne: `+3h`, `+48h`, przed kickoff, postponement, sezon, ta sama godzina, brak wyniku, brak PIT. Nie zmieniać istniejącego M1-R ani M0 w miejscu — nowy identyfikator wariantu i dokładny SHA.
4. Kryterium odbioru: ta sama semantyka wszystkich dopuszczonych cech przy identycznych wejściach; potwierdzony provenance i brak target leakage; CI regresja na dwóch wersjach Pythona, porównanie SHA nietkniętych danych i oddzielna decyzja o zamknięciu P1-01. Zanim PASS: promocja CatBoost zablokowana.

## Tor 2 — historia xG / rzeczywista forma (równolegle, tylko RESEARCH)

**Stan:** KOLEKTOR DZIAŁA / DANE ZWERYFIKOWANE CZĘŚCIOWO / BRAK ORYGINALNEGO HISTORYCZNEGO PIT.

1. Bazować na istniejącym `kb3_historical_feature_quality.py` i rzeczywistej obserwacji w `data/research/historical_multistat/observations.sqlite`. Liczyć **dokładnie ostatnie** mecze drużyn, 5/10/15 all i home/away, z odcięciem przed target; wymagane pełne dwie strony `shots+stats` i natywne ID. `NULL` nigdy nie zamienia się w 0. Historycznie odtworzone obserwacje pozostają RECONSTRUCTED, nie przekwalifikowywać na stare PIT.
2. W kolejnych badaniach zaplanować brakujące całe okna (nie pojedyncze statystyki) wg przyrostu **pełnych par obu drużyn na rzeczywisty request**, rozłożyć ligi, skontrolować GER/ITA/NED/POL/TUR i chronologię sezonów. Reużyć selektor PR #145 **po** źródłowej naprawie #143 / audycie; jego replay daje szybsze xG5, ale nie dowodzi większego końcowego zbioru xG10/15. Nie scalać automatycznie.
3. Oddzielić 162 konfliktowe xG z ostatniego rechecku; porównać native source ID, okres All, `stats.expected_goals` vs sumę `shots.expected_goals`, `total_shots` i prawdziwe 0 vs brak. Raport per liga/sezon, timestamp, typ konfliktu i liczba kompletnych par po zatwierdzonej poprawce. Nie odblokowywać treningu pełnych historycznych cech bez niezależnego dowodu ich właściwej dostępności.
4. Kryterium odbioru: jawny delta-report 1525→nowe liczby, xG5/xG10/xG15 i core5 liczone bez podwójnego zaliczania; dla każdego kompletu exact predecessors, SHA i brak leakage; rzeczywiste wyniki zamiast nominalnego planu API.

## Tor 3 — uczciwe porównanie M0 / Elo-only / CatBoost (równolegle z Tor 1/2)

**Stan:** SILNIKI I SCORER ISTNIEJĄ / RETROSPEKTYWNY PR #144 WYKONANY / PORÓWNANIE PROSPEKTYWNE PENDING.

1. **Nie trenować ponownie M0** i nie zmieniać jego wersji ani SHA. Gromadzić oryginalne same-fixture, same-cutoff, same-horizon prawdopodobieństwa M0 oraz Elo-only i CatBoost no-xG z osobnymi host proofs, z `src/kb3_step17_forward_challengers.py`. Ujawnić brakujące prognozy per wariant; nie rekonstruować ich po kickoff.
2. Osobno raportować A/B/C z #144 jako RECONSTRUCTED_RESEARCH, nigdy nie łączyć tych 942 z prawdziwym forward ani z 74 FIT. Zachować cały koszt braków xG, ligę i tydzień. CatBoost xG i ensemble dopuszczać do prospektywnego porównania dopiero po walidacji źródeł; brak = `NOT_AVAILABLE`, nie prognoza 0%.
3. Przy każdym nowym **rzeczywiście wspólnym** zakończonym meczu wyliczać 1X2 accuracy, Brier sum3, log loss, ECE; delty na identycznych fixture, bootstrap po tygodniach, wyniki per liga i liczbę braków. W istniejącym `src/kb3_step17_engine_comparison.py` minimalny warunek formalnego porównania to 100 prospektywnych wspólnych spotkań i min. 8 niezależnych tygodni; samo osiągnięcie licznika nie zastępuje audytu jakości. Wcześniejsze raporty tylko diagnostyczne.
4. Kryterium odbioru: kompletna macierz wspólnych ID i autentycznych źródeł, CI95 i pomiary bez przecieków, rekomendacja KEEP M0 / CHALLENGER RESEARCH / NO-GO oparta na danych; formalne GATE17 dopiero po niezależnym odbiorze GATE16 i decyzji właściciela. Żadnego automatycznego wyboru Championa.

## Kolejność i rejestr odbiorów

1. Teraz: zamrozić powyższy baseline i semantykę; zrobić prototyp read-only TRAIN/forward-delta i rozkład niekompletnych źródeł xG; sprawdzić gotowy scorer Step17. Nie dublować #143/#144/#145.
2. Następnie: osobny PR naprawczy P1-01 ze źródłowym kontraktem i testami; obok izolowany offline audyt xG wraz z analizą konfliktów; obok aktualizacja read-only prospectives dla 3 silników, bez dodatkowego API jeśli kolektor już zapisuje odpowiednie prognozy.
3. Po każdym rzeczywistym wykonaniu wpisać commit, URL testu, PASS/PARTIAL/NO-GO, porównanie stare vs nowe, skutki dla cech i kolejną decyzję do `docs/ZMIANY.md`.
4. Gdy danych brak: status `PENDING_EVIDENCE`, nie PASS. Testy syntetyczne nigdy nie zwiększają FIT ani prospektywnych par. Oryginalne GATE16/GATE17 pozostają bez zmian.

**Źródła:** [rejestr](ZMIANY.md), [P1 source guards](STEP03_P1_SOURCE_CALIBRATION_GATES_2026-11-04.md), [audyt PR #143–146](AUDIT_PR_143_146_2026-11-04.md), [historyczny report run 41882339782](../data/pit_sidecar/historical_multistat/2026-11-04/run-41882339782-1-summary/ROLLING_AFTER_RECHECK.json), [raport poboru](../data/pit_sidecar/historical_multistat/2026-11-04/run-41882339782-1-summary/ACCELERATED_CAPTURE_REPORT.json), [PR #144](https://github.com/karolbarankiewicz1984-ui/kb-score-3/pull/144), [PR #145](https://github.com/karolbarankiewicz1984-ui/kb-score-3/pull/145), [provenance 3-silników](../src/kb3_step17_challenger_provenance.py).
