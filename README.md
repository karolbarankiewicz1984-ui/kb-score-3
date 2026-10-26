# KB Score 3.0

**Nowy, prywatny i całkowicie niezależny projekt analizy piłkarskiej.** Nie kopiujemy silnika KB Score 2.1. Historyczne KB2.1, API Market i MultiModel pozostają wyłącznie punktami odniesienia.

## Dokumentacja i status projektu

**ŹRÓDŁO PRAWDY:** [Plan główny, bramki odbioru i dziennik na Google Drive](https://docs.google.com/document/d/10wjHL3r3OAuxtezwcIeWztxS8lwjhYon5GM3BLhI0xE/edit).

- [PLAN — mapa wszystkich 29 kroków](docs/PLAN.md)
- [Krok 11 — zaszyfrowane archiwum 760 meczów z niezależnym restore Google Drive](docs/STEP_11_OFFSITE_ARCHIVE.md)
- [Krok 11 — pierwszy rzeczywisty rejestr czasu i treści obserwacji 380 meczów PL 2026/27](docs/STEP_11_PIT_OBSERVATION.md)
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
- [Krok 11 — ELO + ścisła kontrola pochodzenia xG, 82/82 testów, 12/12 xG w próbce (8/12 zgodnych ID), GATE11 PENDING](docs/STEP_11_PROGRESS.md)
- [Historia blokady PitchAPI HTTP 401 (rozwiązana)](docs/STEP_06_BLOCKER.md)

**Stan przy aktualizacji tego README (26.10.2026):** kroki 01–10 ZALICZONE (10/29); krok 11 W REALIZACJI (GATE11 PENDING), kroki 12–29 niezaliczone. GATE10 obejmuje audyt źródła i chronologii, z jawnym wyłączeniem 19 baraży i jednego wyniku AWD. Archiwum historii **760 meczów PL 2023/24 i 2024/25** zostało trwale zaszyfrowane na Google Drive z niezależnym odtworzeniem. Dodatkowo zarchiwizowano osobny realny snapshot **380 meczów PL 2026/27** z rzeczywistym czasem odczytu; statystyki, xG i kursy nie są jeszcze zaimportowane do trwałej bazy (12 testowych odczytów PitchAPI wyłącznie w tymczasowym audycie), a **ML/trening pozostają zablokowane** do bramek dotyczących cech i chronologii. Nie zmieniono KB2.1 ani innych modeli.

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
