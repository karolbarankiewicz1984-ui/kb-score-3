# KB Score 3.0

**Nowy, prywatny i całkowicie niezależny projekt analizy piłkarskiej.** Nie kopiujemy silnika KB Score 2.1. Historyczne KB2.1, API Market i MultiModel pozostają wyłącznie punktami odniesienia.

## Dokumentacja i status projektu

**ŹRÓDŁO PRAWDY:** [Plan główny, bramki odbioru i dziennik na Google Drive](https://docs.google.com/document/d/10wjHL3r3OAuxtezwcIeWztxS8lwjhYon5GM3BLhI0xE/edit).

- [PLAN — mapa wszystkich 29 kroków](docs/PLAN.md)
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
- [Krok 11 — ELO + ścisła kontrola pochodzenia xG, 217/217 testów, 12/12 xG w próbce (8/12 zgodnych ID), GATE11 PENDING](docs/STEP_11_PROGRESS.md)
- [Historia blokady PitchAPI HTTP 401 (rozwiązana)](docs/STEP_06_BLOCKER.md)

**Stan przy aktualizacji tego README (26.10.2026):** kroki 01–10 ZALICZONE (10/29); krok 11 W REALIZACJI (GATE11 PENDING), kroki 12–29 niezaliczone. GATE10 obejmuje audyt źródła i chronologii, z jawnym wyłączeniem 19 baraży i jednego wyniku AWD. Archiwum historii **760 meczów PL 2023/24 i 2024/25** zostało trwale zaszyfrowane na Google Drive z niezależnym odtworzeniem. Dodatkowo zarchiwizowano **dwa osobne realne snapshoty po 380 meczów PL 2026/27** z rzeczywistym czasem odczytu i 3 feedy xG zapisane w kwarantannie, następnie **3/3 mapowania konkretnych meczów** zatwierdzone niezależną warstwą weryfikacji (bez zmiany pierwotnych rekordów); zweryfikowane xG mogą już być użyte jako historyczne cechy w osobnym obserwacyjnym builderze (kontrola faktycznego pobrania i zatwierdzenia crosswalk); preferowany jest już jednosprzedawcowy PitchAPI (na razie tylko pilot, bez przełączenia produkcji) po realnej weryfikacji 1140 meczów trzech sezonów, LE/LK i pól fauli/kartek; nie wykonano produkcyjnego importu kompletnej ligi ani kalibracji modeli, a **ML/trening pozostają zablokowane** do bramek dotyczących cech i chronologii. Nie zmieniono KB2.1 ani innych modeli.

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
