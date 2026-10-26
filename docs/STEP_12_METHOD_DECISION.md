# KB Score 3.0 — Krok 12: metodyka podziału i protokół akceptacji

**Źródło nadrzędne:** Google Docs „KB Score 3.0 — plan”, sekcja „KROK 12 — Podział TRAIN / VALIDATION / TEST”.  
**Oryginalne kryteria:** chronologia; walk-forward; rozdzielenie tożsamości spotkań/drużyn, czasu informacji i wyniku; brak przecieków; niezmienność podziału dla wersji; akceptacja właściciela **przed treningiem**. Koszt realizacji: **0 zł**.  
**Status:** metodologia zaakceptowana do kontynuacji; **GATE12 PASS tylko dla metodyki**, nie uruchamiać treningu. Liczba zaliczonych kroków: **11/29**.

## 1. Decyzje metodologiczne — wersja `step12-methodology-v1`

| Element | Reguła |
|---|---|
| Jednostka podziału | Natywny PitchAPI `fixture_id`, jeden mecz dokładnie raz |
| Granica czasu | `kickoff_utc` bez względu na etykietę sezonu; UTC, `[start,end)` |
| TRAIN | 2023-07-01 <= kickoff < 2025-07-01 |
| VALIDATION | 2025-07-01 <= kickoff < 2026-07-01 |
| TEST | 2026-07-01 <= kickoff < 2027-07-01 |
| Walk-forward | 4 walidacyjne kwartały lipiec–wrzesień 2025, październik–grudzień 2025, styczeń–marzec 2026, kwiecień–czerwiec 2026; każdy trening (po dopuszczeniu danych) na historii poprzedzającej początek danego okna |
| Embargo informacji | Oprócz `kickoff < fold_start` obowiązuje prawdziwe `result_observed_at < fold_start`; do cech przedmeczowych dozwolone wyłącznie `feature_observed_at <= feature_cutoff < kickoff`. Należy weryfikować w czasie rekonstrukcji danego folda |
| Tożsamości drużyn | Stabilny `team_id` służy do rekonstrukcji ELO historii. Drużyna nie musi być rozłączna między latami, ale rekord meczu musi być unikalny, a przyszłe wyniki/oceny drużyny są wykluczone |
| TEST | Zbiór końcowy; zakaz strojenia i wyboru modeli na TEST. Sam terminarz TEST może służyć do kontroli; etykiety tylko w odrębnym procesie końcowego rozliczenia po zamrożeniu modelu |
| Stan wyników / xG | Nie tworzyć fikcyjnych wartości; źródłowe `RETROSPECTIVE` nie oznacza historycznego prematch-PIT; xG bez źródła = `null`, nie `0` |
| Niezmienność | Wersja eksperymentu ma niezmienny SHA256 i dedykowany manifest; zmiana surowej wersji = **nowy** eksperyment, nie modyfikacja dotychczasowego |

## 2. Ważna korekta wobec pierwszego manifestu

Pierwotny zamrożony plik `data/splits/STEP12_NATIVE_REAL_SPLIT_2026-10-26.json` ma **prawidłowe granice**, ale jest **AUDIT-ONLY**, ponieważ zawiera `source_record_sha256` i `source_records_sha256` obliczone z rekordów obejmujących wyniki. Samo usunięcie klucza `label_90m` nie tworzy bezpiecznego widoku do treningu; hashe powiązane z etykietami również są nieodpowiednie.

Nie zmieniamy zamrożonego audytu ani jego SHA (jego oryginalność jest wartością dowodową). Tworzymy **osobny, bezpieczny widok modelowy** `data/splits/STEP12_SAFE_MODEL_VIEW_2026-10-26.json`: tylko `fixture_id`, `kickoff_utc`, `partition` oraz nazwy i liczebności foldów. **Bez statusu, wyniku, hashy źródła, informacji o dostępności etykiet lub etykiet samych w sobie.** Właściwy audyt dowodowy jest przechowywany osobno `data/audits/STEP12_INDEPENDENT_METHODOLOGY_2026-10-26.json`.

Podział `safe_model_fixtures(..., purpose='tuning', ...)` odrzuca **każde** żądanie strojenia, ponieważ mamy teraz wyłącznie terminarz. `purpose='tuning', role='TEST'` dodatkowo zwraca specjalny błąd TEST_HOLDOUT. Żadna zmiana pola JSON nie upoważnia do treningu.

## 3. Co potwierdza PRAWDZIWY indeks (nie syntetyczny)

1. `1520` rzeczywistych, unikalnych `fixture_id` (PitchAPI), rozdział `760/380/380` według kickoff, zero przekroczeń między grupami.
2. Cztery foldy pokrywają **łącznie dokładnie 380** spotkań walidacyjnych; foldy nie mogą zawierać żadnego meczu TEST ani nakładać się w ramach trenowania i walidacji.
3. Dane z jednej wersji źródła przypięte hashem `da387303645a9bb9476351044944e5465d178ddff689c96b579093c4fb4fce3a`. Oryginalny manifest zachowany bez zmiany. Widok dla algorytmu ma własny, niezależny SHA256.
4. Realna lista terminarza nie świadczy o historycznej dostępności pełnych cech ELO, xG, kartki itd.; **0/1520** obecnie ma akceptację do treningu. Nie porzucamy danych historycznych — mogą być użyte w przyszłym `REPLAY` wyłącznie przy osobno opisanych założeniach, bez fikcyjnego twierdzenia o historii obserwacji.

## 4. Bramka odbioru a warunki treningu — dwa różne pytania

**A. Czy metodologiczny KROK 12 jest poprawny?** Wymaga potwierdzenia chronologii, walk-forward, braku przecieków i freeze. Odbiór wymaga też akceptacji właściciela. Nie wymaga pełnego dostępu do wszystkich historycznych cech ligowych lub nowych zapytań API. Przy spełnionych testach można przedłożyć go do akceptacji.

**B. Czy wolno trenować lub rzetelnie backtestować model na obecnym archiwum?** Jeszcze **NIE**. Źródło ma ograniczenia historycznego PIT. To osobna bramka dostępności danych i określenia polityki `REPLAY (historyczny wynik, jawne założenia opóźnienia)` vs `OBSERVED (rzeczywisty zrzut przed kickoff)`. Krok 13 nie może ukrywać tych różnic i nie startuje bez akceptacji kroku 12.

## 5. Propozycja do decyzji właściciela

**Proponuję zatwierdzić** podział TRAIN 2023/24–2024/25, VALIDATION 2025/26, TEST 2026/27 oraz cztery kwartalne foldy walidacji 2025/26. TEST nigdy nie służy do strojenia, a stare pliki z hashami wyników nie trafiają do kodu modelu. Po akceptacji formalnie zamkniemy krok 12 **jako bramkę metodologiczną**, bez mylnego oznaczania niegotowych do treningu danych jako certyfikowane PIT. Następnie osobno ustalimy reguły dopuszczenia historycznych wyników oraz cech do kroku 13.

**Bez potwierdzonej akceptacji użytkownika: GATE12 PENDING.**

## 6. Kontynuacja po wyborze metody: dwa warianty historii (26.10.2026)

W rozmowie uzgodniono kontynuację kroku 12 z porównaniem dwóch sposobów doboru przeszłych meczów: rozszerzająca historia od 01.07.2023 (EXPANDING) oraz zmieniające się 24 miesiące kalendarzowe (ROLLING). Kluczowe: **ten sam kwartalny VALIDATION** w każdym wariancie. Rzeczywiste liczności TRAIN-kandydatów EXPANDING/ROLLING: 760/760, 820/753, 946/750, 1069/776. Walidacja kwartalna 60/126/123/71 (łącznie 380). Każdy kandydat historyczny ma kickoff co najmniej 3 godziny przed granicą folda, ale bez rzeczywistych receipts label/feature **nadal jest niedopuszczony do treningu**. Nigdy nie wolno dobierać długości historii z użyciem TEST.

Przygotowano [niezmienny protokół obu okien](../data/splits/STEP12_DUAL_WINDOWS_REAL_2026-10-26.json) i [jego niezależny audyt](../data/audits/STEP12_DUAL_WINDOWS_AUDIT_2026-10-26.json), [pełne wyjaśnienie](STEP_12_DUAL_WINDOWS.md), SHA protokołu `25242ed4a626aba2669ea86605b31664cb17bf10a6a74e4e3548470954c81198`, [testy offline PASS](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40353630051). Przed wybraniem zwycięskiej metody, po uzyskaniu osobnego certyfikatu danych, porównać na tych samych meczach wieloklasowy log loss, Brier i kalibrację; żadnych wyników takiego porównania dziś nie ma. Decyzja użytkownika pozwoliła **wdrożyć proponowany wariant**, ale ostateczna formalna akceptacja GATE12 nie jest jeszcze osobno odnotowana. `training_allowed=false`.

## 26.10.2026 — KOŃCOWY ODBIÓR METODYKI KROKU 12

**GATE12 PASS wyłącznie dla metodologii TRAIN/VALIDATION/TEST i porównania EXPANDING vs ROLLING.** [Samodzielny, zamrożony protokół odbioru](../data/audits/STEP12_METHOD_GATE_PASS_2026-10-26.json), rekord SHA `0332edf73cd893f9848ffb23ea7821a09f5c183e6add77fc7cfdd7378959c5be`. [Raport rzeczywistych blokad danych](../data/audits/STEP12_REAL_PIT_GAP_REPORT_2026-10-26.json): `1220` historycznych odczytów RETROSPECTIVE i `300` nadchodzących meczów z niezatwierdzonymi cechami; łącznie **0** dopuszczonych do treningu. Wcześniejsze wzmianki „PENDING” są zapisem stanu sprzed odbioru. Po potwierdzeniu przez użytkownika kontynuacji obu metod porównania i zaliczeniu testów programu protokół metody ma PASS, natomiast **`training_allowed=false`** i osobna bramka PIT pozostają w mocy. Krok 13 nie jest jeszcze rozpoczęty; dopasowywanie modeli, publikowanie prognoz lub fałszywe backtesty są zabronione.
