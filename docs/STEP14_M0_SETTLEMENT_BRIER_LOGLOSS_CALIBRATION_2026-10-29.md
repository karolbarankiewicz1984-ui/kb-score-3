# KB Score 3.0 — automatyczne rozliczanie M0, log loss, Brier i kalibracja (29.10.2026)

**ADR [bieżące ustalenia](ADR_2026-10-29_FORWARD_M0_PIT_CALIBRATION_STORAGE.md), formalnie 13/29; GATE14 nadal PENDING.**

## Zakres działania

1. W prywatnej [bazie SQLite](../data/forward_m0/kb3_forward_m0.sqlite) są pierwotnie zamrożone prognozy SHADOW M0 1/X/2 dla LaLiga, Serie A i Bundesligi. **Nigdy ich nie nadpisujemy**, nawet gdy dostawca zmienia statystyki.
2. Nowy [kod](../src/kb3_m0_shadow_settlement.py) czyta tylko **nierozliczone** prognozy, których kickoff był **co najmniej 3 godziny wcześniej**; pobiera **bieżące, rzeczywiste** wyniki z `PitchAPI.leagues.matches` tylko dla potrzebnych spośród tych trzech lig, przy użyciu istniejącego klucza. Rozlicza jedynie status `finished`, wynik 90 minut i dokładne ID meczu, gospodarzy, gości oraz pierwotny kickoff. Odmowy/braki pozostają nierozliczone, a nie stają się porażką ani remisem 0:0.
3. `migrations/004_m0_shadow_settlement_calibration.sql` dodaje odrębną append-only tabelę `m0_shadow_settlements` z wynikiem, prawdziwymi czasami odczytu i rozliczenia, źródłowym SHA, log loss i **Brier sum3 bez dzielenia przez trzy**. Triggery blokują `UPDATE/DELETE`, powtórny wynik tego samego `forecast_id` i rozliczenie przed zakończeniem spotkania. Źródłowa prognoza i jej prawdopodobieństwa pozostają nietknięte.
4. Matematyka z oryginalnego `src/kb3_step14_m1_math_calibration.py`: `score_one` dla każdego meczu; następnie `score_predictions` dla całego zbioru, log loss, Brier, trafność top1 i ECE. Każda wersja `model_version_id + parameter_sha256` jest analizowana osobno; faza `EARLY`, porządek klas `1, X, 2`.
5. **20–30** zamrożonych i rozliczonych meczów to diagnostyka, bez korekt. Przy **100** chronologicznie zakończonych prognozach stałej wersji przygotowujemy **kandydata temperatury** z zamrożonej siatki `0.7,0.85,1.0,1.15,1.4,1.8,2.2`. Przy **50 kolejnych rozliczonych** badamy surowe vs kalibrowane `log loss/Brier/ECE` bez fit na tej późniejszej próbie. Werdykt pozostaje **`production_approved:false`**, nawet przy poprawie metryk; wymaga audytu i osobnej decyzji. Nie uczymy CatBoost M1 na tych samych wynikach ani nie wykorzystujemy oryginalnego TEST Premier League 2026/27.
6. [Workflow](../.github/workflows/kb3-m0-shadow-daily-settlement.yml) jest zaplanowany codziennie **08:41 UTC (09:41 zimą, 10:41 latem, Europe/Warsaw)**, niezależnie od codziennego zrzutu cech o 06:17 UTC. Na każdy dzień tworzy **osobny raport JSON** i zapisuje powiększoną bazę SQLite na prywatnej głównej gałęzi GitHub. Jeżeli żaden z prognozowanych meczów jeszcze się nie zakończył, zapisuje stan `0` rozliczeń i `COLLECTING` zamiast wymyślać wyniki.
7. Obecne prognozy są **M0_SHADOW, z parametrami Poissona ilustracyjnymi i niefitowanymi**. Ten proces obiektywnie oceni ich skuteczność, ale nie oznacza dziś gotowego bukmacherskiego Championa, oryginalnego M1 czy zaliczonego GATE14.

## Kontrola i bieżące ograniczenia

**Nie wolno** używać najnowszej retrospektywnej odpowiedzi jako dowodu oryginalnej daty opublikowania xG w sezonie 2023–25. Pobierane po meczu wyniki nie dotykają archiwalnych cech, Elo ani zamrożonych prawdopodobieństw. W razie przesunięcia meczu kontrola kickoff blokuje automatyczne rozliczenie; trzeba odrębnie ustalić poprawny przypadek bez modyfikacji oryginalnego forecast.

**Nie uruchomiono jeszcze niezależnego offsite backup SQLite Google Drive**, dlatego prywatny `main` i 30-dniowy artefakt GitHub Actions nie zastępują planowanego systemu kopii zapasowych. Brak jest też jeszcze rzeczywistych rozliczonych meczów z pierwszej próby, jeśli w czasie uruchomienia żaden z nich nie osiągnął stanu finished+3h.

**Następne czynności:** po pierwszych zakończonych spotkaniach zweryfikować ich faktyczny wynik, znaczniki czasu, `log loss/Brier`, ciągłość kopii SQLite; później monitorować n100/150 i osobną chronologiczną walidację. Bez samowolnej zmiany metodologii.

### 29.10.2026 — decyzja o wyłączeniu dubla

Ten dokument opisuje **historyczny, zdublowany wariant**, a nie obowiązującą automatyzację. `.github/workflows/kb3-m0-shadow-daily-settlement.yml` odtąd wykonuje **wyłącznie testy regresyjne CI**, bez `schedule`, `workflow_dispatch`, klucza PitchAPI i uprawnienia zapisu. Zachowano kod oraz dotychczasowe rekordy do śledzenia pochodzenia, bez kolejnych live wpisów. Jedynym aktywnym robotem rozliczającym jest [KB3 M0 real postmatch](STEP14_M0_REAL_POSTMATCH_LOGLOSS_BRIER_CALIBRATION_2026-10-29.md) z tabelą `m0_shadow_1x2_settlements`, działający **07:47 i 22:47 UTC**, z trwałym SHA/RSA źródła. Nie wolno zsumować wyników z obu tabel jako niezależnych meczów. Progi badawcze i ochrona TEST 2026/27 nie ulegają zmianie.
