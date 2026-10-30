# KB Score 3.0 — dodatkowe prace naprawcze bez minut Actions

**30.10.2026, Europe/Warsaw | pakiet roboczy PENDING CI / BEZ ZMIANY MAIN**

## 1. M0 720-TRAIN: ponowna ocena offline, bez kalibracji

Nowe `scripts/step16_m0_offline_readonly_audit.py` otwiera istniejące `data/forward_m0_720_eight/kb3_forward_eight.sqlite` przez URI `mode=ro&immutable=1`. Nie tworzy schematu ani transakcji INSERT/UPDATE/DELETE. Bierze tylko rekordy z istniejącej funkcji `eligible_settlements`, czyli z realnym rozliczeniem i wcześniejszym serwerowym dowodem GitHub przed kickoff. Ponownie liczy Brier sum3, log loss, trafność 1X2 i top1 ECE 5-bin, osobno dla 8 lig i globalnie; sprawdza zgodność z zapisanym rozliczeniem do tolerancji 1e-9. Raportuje łączną liczbę prognoz, rozliczeń, dowodów hosta, kwalifikowanych wyników oraz liczbę brakującą do 100. Gdy brak kwalifikowanych wyników, miary jakości zwraca jako `null`, a nie sztuczne zero. Nowa ścieżka nie wywołuje `calibrate_if_eligible`, PitchAPI, CatBoost i nie odczytuje oryginalnego chronionego TEST.

Testy: `tests/test_step16_m0_offline_readonly_audit.py`, izolowany PR/manual workflow `.github/workflows/kb3-step16-offline-readonly-audit.yml`. Workflow nie ma harmonogramu, nie jest zależnością działającego kolektora i nie może blokować jego przyszłych przebiegów.

## 2. Usprawnienie zużycia Actions (projekt do sprawdzenia)

Nie wyłączać istniejących dziewięciu wymienionych dziennych uruchomień przed audytem równoważności archiwum. W działającym ośmioligowym workflow testy i pobór instalują CatBoost oraz kryptografię osobno; na gałęzi roboczej wdrożono konfigurację pamięci podręcznej pip w obu jobach oraz rozdzielenie **dokładnie dotychczasowych zależności** na dwa pliki requirements. Nie usuwa to żadnego joba ani harmonogramu. Nie należy zakładać oszczędności minut przed pomiarem; bez scalania do czasu pozytywnego sprawdzenia workflow po odnowieniu minut.

## 3. Porównanie silników i xG

Istniejące `src/kb3_step17_engine_comparison.py` już sprawdza wspólne fixture ID, cutoff, horyzont, sparowane wyniki i CI tygodniowe. `src/kb3_step17_xg_capture.py` i `future_xg_coverage` mają blokadę imputacji braków xG i wymóg pięciu rzeczywiście ostatnich spotkań. Nie należy powielać tych funkcji ani podawać fałszywych metryk. Do czasu rzeczywistych nowych prognoz xG/ensemble oraz wyników 100+50 nie wyznaczać Championa.

**Stan:** kod w odizolowanej gałęzi, wykonanie runnera nieudowodnione przy limitach 3000/3000. Wszystkie 73 wcześniejsze prognozy M0, SHA, 8 lig, kryterium 100+50, GATE15 PASS i GATE16/GATE17 PENDING pozostają bez zmian.

## 4. Kontrola statyczna harmonogramu i zależności

`tests/test_step16_workflow_cache_static.py` porównuje oryginalne dwa harmonogramy live, zależność joba prawdziwego od bramki bezpieczeństwa, brak harmonogramu lub sekretów w odczycie offline oraz dokładne wersje bibliotek. Dopisano go do osobnego PR/manual workflow. Do formalnego PASS konieczne jest rzeczywiste wykonanie CI.
