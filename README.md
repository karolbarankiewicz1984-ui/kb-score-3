# KB Score 3.0

**Nowy, prywatny i całkowicie niezależny projekt analizy piłkarskiej.** Nie kopiujemy silnika KB Score 2.1. Historyczne KB2.1, API Market i MultiModel pozostają wyłącznie punktami odniesienia.

## Dokumentacja i status projektu

**ŹRÓDŁO PRAWDY:** [Plan główny, bramki odbioru i dziennik na Google Drive](https://docs.google.com/document/d/10wjHL3r3OAuxtezwcIeWztxS8lwjhYon5GM3BLhI0xE/edit).

- [PLAN — mapa wszystkich 29 kroków](docs/PLAN.md)
- [Krok 12 — rzeczywisty indeks 1520 meczów i kopia Google Drive (stan w trakcie prac)](docs/STEP_12_REAL_INDEX_2026-10-26.md)
- [Krok 12 — dokumentacja metody TRAIN/VALIDATION/TEST](docs/STEP_12_PROGRESS.md)
- [Krok 11 — odbiór według pierwotnych wymagań: GATE11 PASS, 11/29 etapów](docs/STEP_11_GATE_ACCEPTANCE_2026-10-26.md)
- [Krok 11 — zaszyfrowane archiwum 760 meczów z niezależnym restore Google Drive](docs/STEP_11_OFFSITE_ARCHIVE.md)
- [Krok 11 — pierwszy rzeczywisty rejestr czasu i treści obserwacji 380 meczów PL 2026/27](docs/STEP_11_PIT_OBSERVATION.md)
- [Krok 11 — drugi odczyt 380 meczów i limitowane xG PitchAPI w kwarantannie](docs/STEP_11_TWO_PIT_XG.md)
- [Krok 11 — 3 mapowania historycznych xG zatwierdzone po przeglądzie pełnego źródła](docs/STEP_11_XG_IDENTITY_REVIEW.md)
- [Krok 11 — realny observed-at PIT zasila wspólne ELO/formę/xG, audyt 125 testów](docs/STEP_11_OBSERVED_FEATURES.md)
- [Krok 11 — dziesięć nowych xG z dziesięciu dat, 5/10 strict, bezpieczny odczyt dwóch niezależnych archiwów](docs/STEP_11_XG10_STRATIFIED.md)
- [Krok 11 — jedno sportowe źródło PitchAPI, 1140 fixture, UEFA/faule i natywny builder shadow](docs/STEP_11_SINGLE_PROVIDER_DECISION.md)
- [Krok 11 — prawdziwe obserwacje PitchAPI 380+5, encrypted Drive oraz niezależne odtworzenie](docs/STEP_11_PITCH_NATIVE_PIT_ARCHIVE.md)
- [Krok 11 — Liga Europy i Liga Konferencji: 12/12 natywne xG, niezależny restore Drive 15/15 i testy zmian źródła](docs/STEP_11_UEFA_NATIVE_XG_COVERAGE.md)
- [Krok 11 — dwie prawdziwe obserwacje natywnego PitchAPI: 0/380 zmian PL i 0/5 xG, dwa odtworzone backupy Drive](docs/STEP_11_NATIVE_SECOND_REAL_CAPTURE.md)
- [Krok 11 — katalog łącznie wszystkich cech z czasem, źródłem i blokadą przyszłych danych (v0.5)](docs/STEP_11_FIELD_PROVENANCE_GATE.md)
- [DANE — projekt bazy i źródeł](docs/DANE.md)
- [MODEL — metodologia i testy](docs/MODEL.md)
- [ZMIANY — rejestr decyzji i PASS/FAIL](docs/ZMIANY.md)
- [Lista kontrolna bezpieczeństwa kroku 03](docs/STEP_03_SECURITY_CHECKLIST.md)
- [Protokół odbioru kroku 04 — PASS](docs/STEP_04_ACCEPTANCE.md)
- [Audyt API-Football i protokół kroku 05 — PASS](docs/STEP_05_ACCEPTANCE.md)
- [Raport pokrycia ligi × sezon](docs/audits/API_FOOTBALL_STEP05_2026-10-25.md)
- [Krok 06 — audyt PitchAPI PASS i wyniki](docs/STEP_06_ACCEPTANCE.md)
- [Krok 07 — parowanie identyfikatorów, GATE PASS i kolejka REVIEW](docs/STEP_07_ACCEPTANCE.md)
- [Krok 08 — SQLite, niezmienne prognozy i odtworzenie backupu z Dysku Google](docs/STEP_08_ACCEPTANCE.md)
- [Krok 09 — pilot importu 380 meczów Premier League, 19/19 testów i zaszyfrowany backup](docs/STEP_09_ACCEPTANCE.md)
- [Krok 10 — audyt jakości 5 lig × 6 sezonów, 10 679 meczów, 54/54 testów PASS](docs/STEP_10_ACCEPTANCE.md)
- [Krok 11 — ELO + ścisła kontrola pochodzenia xG, 246/246 testów, 38 potwierdzonych unikalnych próbek xG, GATE11 PASS](docs/STEP_11_PROGRESS.md)
- [Historia blokady PitchAPI HTTP 401 (rozwiązana)](docs/STEP_06_BLOCKER.md)

**Stan przy aktualizacji tego README (26.10.2026):** kroki 01–12 ZALICZONE (12/29); kroki 11 i 12 ODEBRANE (GATE11 PASS, GATE12 PASS wyłącznie metodologia), kroki 13–29 niezaliczone; training_allowed=false. GATE10 obejmuje audyt źródła i chronologii, z jawnym wyłączeniem 19 baraży i jednego wyniku AWD. Archiwum historii **760 meczów PL 2023/24 i 2024/25** zostało trwale zaszyfrowane na Google Drive z niezależnym odtworzeniem. Dodatkowo zarchiwizowano **dwa osobne realne snapshoty po 380 meczów PL 2026/27** z rzeczywistym czasem odczytu i 3 feedy xG zapisane w kwarantannie, następnie **3/3 mapowania konkretnych meczów** zatwierdzone niezależną warstwą weryfikacji (bez zmiany pierwotnych rekordów); zweryfikowane xG mogą już być użyte jako historyczne cechy w osobnym obserwacyjnym builderze (kontrola faktycznego pobrania i zatwierdzenia crosswalk); preferowany jest już jednosprzedawcowy PitchAPI (na razie tylko pilot, bez przełączenia produkcji) po realnej weryfikacji 1140 meczów trzech sezonów, LE/LK i pól fauli/kartek; nie wykonano produkcyjnego importu kompletnej ligi ani kalibracji modeli, a **ML/trening pozostają zablokowane** do bramek dotyczących cech i chronologii. Nie zmieniono KB2.1 ani innych modeli.

## Co znajduje się w repo?

- `docs/` — plan, decyzje, metodologie i dowody odbioru;
- `src/` — przyszły kod modelu i pobierania danych;
- `tests/` — przyszłe testy;
- `config/` — konfiguracja niesekretna;
- `data/` — manifesty danych (duże archiwa poza repo);
- `models/` — manifesty wytrenowanych modeli;
- `reports/` — szablony i raporty;
- `scripts/` — przyszłe skrypty;
- `.github/workflows/kb3-step03-secrets-smoke.yml` — ręczny, odczytowy test dwóch połączeń API wykonany w kroku 03.

**Zasada bramki:** każdy z 29 kroków ma kryterium odbioru, test PASS i link do dowodu. Kod źródłowy lub sam opis nie zalicza kroku. Brak automatycznego obstawiania i nowych zakupów bez zgody właściciela; sekrety pozostają w GitHub Secrets, nigdy w repo.

**Krok 12 — bezpieczny podział do zatwierdzenia:** [Metodyka oraz protokół decyzji](docs/STEP_12_METHOD_DECISION.md), [zamrożony widok bez wyników](data/splits/STEP12_SAFE_MODEL_VIEW_2026-10-26.json), [niezależny audyt](data/audits/STEP12_INDEPENDENT_METHODOLOGY_2026-10-26.json). 1520 realnych meczów, 760/380/380, 4 foldy 60/126/123/71. GATE12 nadal PENDING (brak akceptacji); trening zablokowany.

**Krok 12 — rozszerzona walidacja:** [EXPANDING kontra przesuwane 24 miesiące](docs/STEP_12_DUAL_WINDOWS.md) — te same cztery kwartalne walidacje 2025/26, 380 spotkań, zero przecieków TEST, brak treningu na niezatwierdzonych danych. [Niezmienny manifest obu metod](data/splits/STEP12_DUAL_WINDOWS_REAL_2026-10-26.json). GATE12 PENDING.

**Aktualny stan (26.10.2026):** Krok 12 ODEBRANY — GATE12 PASS wyłącznie metodologia, 12/29; 0/1520 zatwierdzonych próbek do treningu. [Rekord odbioru](data/audits/STEP12_METHOD_GATE_PASS_2026-10-26.json), [raport ograniczeń PIT](data/audits/STEP12_REAL_PIT_GAP_REPORT_2026-10-26.json). Bez startu kroku13 lub zmiany innych modeli.

**Krok 13 — W REALIZACJI:** [Pierwszy silnik ELO + Poisson i testy matematyczne](docs/STEP_13_PROGRESS.md). [Syntetyczny zamrożony raport M0](data/audits/STEP13_M0_REFERENCE_2026-10-26.json); wzorcowe 1X2 PASS, lecz **brak jeszcze prawdziwego backtestu i metryk historycznych**, GATE13 PENDING, nadal 12/29, training_allowed=false.

**Krok13 v0.2 — symulator walk-forward:** [bezpieczny mechanizm kwartalnego odtwarzania (tylko sztuczne wyniki)](docs/STEP_13_REPLAY_CONTRACT.md) i [realny raport gotowości terminarza](data/audits/STEP13_REAL_FOLD_READINESS_2026-10-26.json) (0/1520 kwalifikowanych danych). CI testuje brak wpływu wyniku walidacji na jego prognozę. Realnego historycznego backtestu nadal nie wykonano, GATE13 PENDING.

**Krok 13 — kontrola opóźnionych wyników:** [Dodatkowy test prequential w obrębie kwartału](docs/STEP_13_PROGRESS.md), [moduł](src/kb3_step13_replay.py) i [raport wyłącznie syntetyczny](data/audits/STEP13_M0_SYNTHETIC_REPLAY_2026-10-26.json). Nie zastępuje głównego modelu ze stałym zamrożeniem na początku folda. Nie testowano prawdziwej historii; GATE13 PENDING.
