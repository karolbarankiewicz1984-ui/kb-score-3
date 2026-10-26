# KB Score 3.0 — Krok 12: podział TRAIN / VALIDATION / TEST

**Rozpoczęto:** 26.10.2026 • **Stan:** ZALICZONY — GATE12 PASS wyłącznie dla metodologii • **Koszt nowych usług:** 0 zł.

**Zakres:** techniczna konstrukcja odtwarzalnego, chronologicznego i niemutowalnego podziału. **Nie uruchamiamy treningu, nie generujemy typów bukmacherskich, nie twierdzimy, że historyczne dane są prawdziwym PIT.** Krok 11 odebrany według pierwotnej bramki; jego `training_allowed=false` pozostaje w mocy.

## Zamrożona propozycja okien v0.1 (UTC, lewy kraniec włączony, prawy wyłączony)

| Rola | Zakres wydarzeń | Dozwolone użycie po dodatkowej certyfikacji |
|---|---|---|
| TRAIN | 01.07.2023–30.06.2025 | Estymacja ELO/Poissona i innych parametrów |
| VALIDATION | 01.07.2025–30.06.2026 | Strojenie i kalibracja, bez korzystania z TEST |
| TEST | 01.07.2026–30.06.2027 | Zamknięty holdout; bez strojenia na jego wynikach |

Podział działa po rzeczywistym `kickoff_utc`, a **nie** tylko po nazwie sezonu. Tożsamość `fixture_id` nie może wystąpić więcej niż raz. Ciągłość tożsamości drużyn między latami nie jest przeciekiem: tożsamość jest znana przed meczem, natomiast ich **późniejsze oceny, wyniki oraz cechy już są przeciekiem**.

## Walk-forward v0.1

Kolejne walidacyjne okna: 07–09.2025, 10–12.2025, 01–03.2026 i 04–06.2026. W każdym oknie treningowe obserwacje muszą spełnić obie granice: `kickoff < fold_start` **oraz** `label_observed_at < fold_start`. Wcześniejsze obserwacje VALIDATION mogą wejść do następnego, poszerzonego TRAIN dopiero po udostępnieniu ich prawdziwych wyników. **Nigdy** nie wolno włączyć TEST do strojenia.

## Kwarantanna informacji retrospektywnych

Odczyty meczów PL 2023/24–2025/26 pobrane 26.10.2026 są prawdziwą historią sportową, ale nie stanowią dowodu historycznej dostępności wszystkich cech przed kickoff. Zapisujemy je jako `RETROSPECTIVE` i **nie** przydzielamy ich do dopuszczonego treningu ani uczciwego historycznego backtestu. Obserwacje `PROSPECTIVE_OBSERVED_AT` muszą mieć źródłowe znaczniki każdej cechy <= `feature_cutoff_utc < kickoff_utc`, a także zgodę z audytu Step11. Brak xG nie staje się zerem; osobny mechanizm cech z kroku 11 nadal odpowiada za flagi braków.

Kontrola 90 minut: wynik H/D/A musi być obserwowany nie wcześniej niż kickoff i najpóźniej do czasu eksportu. Wynik TRAIN obserwowany po początku VALIDATION nie nadaje się do treningu tej walidacji, analogicznie VALIDATION po początku TEST nie nadaje się do decyzji poprzedzającej TEST. Wyniki trzymamy poza jawnie publikowanymi w manifestach listami, by nie przypadkowo wykorzystać holdoutu.

## Kod, dowód i odbiór

- `src/kb3_split.py`: walidacja UTC, wersja danych, kody powodów kwarantanny, chronologiczny przydział, walk-forward, SHA-256 i zapis manifestu **bez możliwości nadpisania różną zawartością**.
- `tests/test_step12_split.py`: negatywne i pozytywne testy syntetyczne. Test nie jest dowodem na istnienie prawdziwych poprawnych historycznych PIT.
- `.github/workflows/kb3-step12-split.yml`: testy offline, bez sekretów, wywołań API, automatycznego treningu i płatnych zadań.
- Wywołanie na gotowym rzeczywistym *zunifikowanym indeksie metadanych*, nie na surowym pliku z tokenami: `python -m src.kb3_split --input input_metadata.json --output private/STEP12_SPLIT_v1.json`. Wymagane pola wejścia: `dataset_version`, `exported_at_utc`, `records[]`; rekord: `fixture_id`, `kickoff_utc`, `label_90m` (lub null), `label_observed_at_utc` (lub null), `evidence_class`. Dla dopuszczalnego PIT także `feature_cutoff_utc` i `feature_availability` z czasem i zgodą dla każdej cechy.

**Do odbioru GATE12:** (1) wskazać rzeczywisty, zamrożony, pełny indeks fixture ID wraz z fingerprintami źródeł; (2) zapisać manifest z liczebnościami i SHA oraz sprawdzić jego niezależne odtworzenie; (3) pokazać zielone testy CI oraz oddzielne potwierdzenie braku przecieku; (4) uzyskać akceptację metodologii przed treningiem. Jeśli brak rzeczywistego PIT, wynik to uczciwe `GATE12 PENDING`, a nie fikcyjne zaliczenie.

**Własne starsze modele KB2.1, API Market i MultiModel:** nietknięte. **Nowe koszty:** 0 zł.

## 26.10.2026 — rzeczywisty indeks 1520 i kopia niezależna

Pierwszy rzeczywisty, kompletny indeks czterech sezonów PitchAPI został utworzony, 1520/1520 native match IDs, TRAIN 760 / VALIDATION 380 / TEST 380. Wszystkie 1520 rekordów pozostają poza ML z powodu historycznej klasyfikacji RETROSPECTIVE albo braku zatwierdzenia pełnych prospektywnych cech; nie fałszujemy prematch-PIT. [Rzeczywiste CI PASS](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40345911294), [manifest](../data/splits/STEP12_NATIVE_REAL_SPLIT_2026-10-26.json), [raport](STEP_12_REAL_INDEX_2026-10-26.md), [kopia na Google Drive](https://drive.google.com/file/d/1j56rqRA8SnVYi1g65dbfwPaXHH96GzhB/view). Po pobraniu kopii z Drive niezależnie zweryfikowano hashe źródłowego ciphertext i splitu, bez prywatnego klucza i bez RSA decrypt. Wciąż GATE12 PENDING i training_allowed=false.

## 26.10.2026 — interpretacja BRAMKI bez dodawania nowych wymagań

Ponownie przeczytano oryginalny KROK 12: jest to **metodyka TRAIN / VALIDATION / TEST, walk-forward, oddzielenie dat informacji od wyników, freeze i akceptacja właściciela**. Nie jest warunkiem tego kroku certyfikacja kompletnego xG każdego historycznego meczu. To osobny problem jakości danych przed rzeczywistym treningiem, a nie podstawa do nieskończonego odsuwania metodologicznej bramki. Oryginalny manifest zawiera hashe zależne od wyników, przez co nie powinien być podawany algorytmowi; zachowano go wyłącznie do audytu. Przygotowano [safe model view](../data/splits/STEP12_SAFE_MODEL_VIEW_2026-10-26.json) oraz [odrębny niezależny raport](../data/audits/STEP12_INDEPENDENT_METHODOLOGY_2026-10-26.json), 4 foldy walidacji: 60 / 126 / 123 / 71, suma 380; żadne 380 z TEST nie trafia do foldów. Konkretny [protokół do akceptacji](STEP_12_METHOD_DECISION.md). **Brak akceptacji = GATE12 PENDING; brak PIT i zgody = zakaz treningu.**

## 26.10.2026 — wariant EXPANDING vs ROLLING 24 miesięcy

Po omówieniu dostępnych podziałów wdrożono porównanie dwóch metod historii na dokładnie tych samych kwartalnych walidacjach. Realne kandydatury TRAIN (tylko terminarz, nie certyfikowane próbki): **760/760**, **820/753**, **946/750**, **1069/776** odpowiednio dla EXPANDING/ROLLING. Validation 60/126/123/71 = 380. Trening wymaga jeszcze prawdziwych czasów dostępności wyniku i cech przed foldem. Żaden rekord TEST nie może wpływać na wybór strategii. Zasady i audyt: [Krok12 dual windows](STEP_12_DUAL_WINDOWS.md), [nowy niezmienny manifest](../data/splits/STEP12_DUAL_WINDOWS_REAL_2026-10-26.json), [raport](../data/audits/STEP12_DUAL_WINDOWS_AUDIT_2026-10-26.json); offline testy PASS https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40353630051 . Bez kolejnych wywołań PitchAPI, bez dopasowywania jakiegokolwiek modelu. Formalnie nadal GATE12 PENDING.

## 26.10.2026 — KOŃCOWY ODBIÓR METODYKI KROKU 12

**GATE12 PASS wyłącznie dla metodologii TRAIN/VALIDATION/TEST i porównania EXPANDING vs ROLLING.** [Samodzielny, zamrożony protokół odbioru](../data/audits/STEP12_METHOD_GATE_PASS_2026-10-26.json), rekord SHA `0332edf73cd893f9848ffb23ea7821a09f5c183e6add77fc7cfdd7378959c5be`. [Raport rzeczywistych blokad danych](../data/audits/STEP12_REAL_PIT_GAP_REPORT_2026-10-26.json): `1220` historycznych odczytów RETROSPECTIVE i `300` nadchodzących meczów z niezatwierdzonymi cechami; łącznie **0** dopuszczonych do treningu. Wcześniejsze wzmianki „PENDING” są zapisem stanu sprzed odbioru. Po potwierdzeniu przez użytkownika kontynuacji obu metod porównania i zaliczeniu testów programu protokół metody ma PASS, natomiast **`training_allowed=false`** i osobna bramka PIT pozostają w mocy. Krok 13 nie jest jeszcze rozpoczęty; dopasowywanie modeli, publikowanie prognoz lub fałszywe backtesty są zabronione.
