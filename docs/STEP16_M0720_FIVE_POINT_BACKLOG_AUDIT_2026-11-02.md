# KB Score 3.0 — 2026-11-02: plan 1–5 / audyt braku przyrostu M0-720

Status: **częściowo wykonane, bez wdrożenia zmian live**. Zmiany w odseparowanej gałęzi audytowej. Bez nowych płatnych wywołań PitchAPI, bez modyfikacji forecastów, bazy, modeli i chronionego TEST.

## Ustalenia z realnych źródeł
- M0 trzy ligi: autentyczny receipt z 2026-11-02 01:51 UTC: 6 nowych, 18 łącznie, 3 pending / TOO_EARLY.
- M0-720 8 lig: receipt z 2026-11-02 16:15 UTC: 17 wywołań, 0 nowych prognoz, 75 łącznie; ostatni potwierdzony settle: 60/75 rozliczonych. Nie zakładać, że 15 z 15 mają już końcowy wynik.
- Workflow ma forecast 06:21, 09:21, 12:21 UTC, ale `scripts/step16_m0_mode_guard.py` pomija kolejne przebiegi, gdy istnieje dzienny frozen JSON. `scripts/step16_m0_720_eight_run.py` też wraca wcześniej. `run()` wymaga jednego katalogu prognoz na dzień. Dopisanie kolejnego crona bez modyfikacji archiwizacji nie zwiększy pokrycia.
- `make_forecasts`: 96h okno, 90m lead, limit 10/ligę po sprawdzeniu historii, historyczne `home_all_5_n` i `away_all_5_n` co najmniej 5. Odmowy nie mają pełnego trwałego licznika szczegółowych przyczyn.

## Realizacja punktów 1–5
1. **Audyt odmów: przygotowana podstawa, pełne liczniki PENDING.** Potrzebny patch w `make_forecasts` na liczby per liga i per powód: poza horyzontem; za późno; status; brak pięciu poprzedników u gospodarzy/gości; quota; już istniejący w SQLite (to rozpoznać dopiero po porównaniu z zapisanymi ID). Zmianę rozliczać w nowym rzeczywistym przebiegu, nie z danych nieutrwalonych.
2. **Backlog: dodano niezależne narzędzie `scripts/audit_m0720_backlog.py`.** Otwiera SQLite wyłącznie do odczytu, sprawdza integrity/foreign keys, podaje wszystkie nierozliczone forecast IDs i ligi oraz rozdziela przyszły kickoff od wyniku wymagającego sprawdzenia w PitchAPI. NIE twierdzi, że sam upływ czasu oznacza finalny wynik. Uruchomienie na rzeczywistej bazie przez GitHub CI/runner nadal PENDING; brak możliwości odczytu binarnej bazy przez tekstowy konektor.
3. **Harmonogram: AUDITED, zmian LIVE NIE AKTYWOWANO.** Przed zwiększeniem częstotliwości wymagane są wielokrotne niezmienne snapshota per dzień, brak ponownego rozliczenia tych samych ID, koszty 17 requestów na nowy pełny forecast i odporność na opóźnienia Actions. Nie uruchamiać dodatkowych płatnych przebiegów w ciemno.
4. **Więcej lig: bez rozszerzenia w tej zmianie.** Pozostać przy 8; audyt 309 NED i 313 BEL historycznych native IDs z nieznaną fazą, brak zgody na trening lub domniemane regular/playoff. Dopiero wiarygodne porównanie braków i uprawnień dostawcy uzasadnia zwiększenie.
5. **Integralność: zachowana.** Parametry `55310f0e1dd3842e6d876069ef21b1380901b3a6cc6884cf6ec6ea351a5812d1`; 100 FIT + 50 późniejszych HOLDOUT, zakaz ex-post, chroniony Premier League TEST, M0/M1 produkcyjne i stary 3-league shadow bez zmian.

## Warunki dalszego odbioru
- PASS testu skryptu read-only na fixture SQLite i rzeczywistej bazie; sprawdzenie backlogu wszystkich 15 pozycji.
- Pełna diagnostyka selekcji bez zmiany decyzji modelu, frozen receipt z nowymi licznikami.
- Osobny PR dla multi-run/day, testy kolizji i SHA, a dopiero po nim ewentualne dodatkowe godziny; koszt zatwierdzony w istniejących limitach.
- GATE16/GATE17 nadal PENDING; nie ma dowodu na 100 FIT.
