# KB Score 3.0

**Nowy, prywatny i całkowicie niezależny projekt analizy piłkarskiej.** Nie kopiujemy silnika KB Score 2.1. Historyczne KB2.1, API Market i MultiModel pozostają wyłącznie punktami odniesienia.

## Dokumentacja i status projektu

**ŹRÓDŁO PRAWDY:** [Plan główny, bramki odbioru i dziennik na Google Drive](https://docs.google.com/document/d/10wjHL3r3OAuxtezwcIeWztxS8lwjhYon5GM3BLhI0xE/edit).

- [PLAN — mapa wszystkich 29 kroków](docs/PLAN.md)
- [DANE — projekt bazy i źródeł](docs/DANE.md)
- [MODEL — metodologia i testy](docs/MODEL.md)
- [ZMIANY — rejestr decyzji i PASS/FAIL](docs/ZMIANY.md)
- [Lista kontrolna bezpieczeństwa kroku 03](docs/STEP_03_SECURITY_CHECKLIST.md)
- [Protokół odbioru kroku 04 — PASS](docs/STEP_04_ACCEPTANCE.md)
- [Audyt API-Football i protokół kroku 05 — PASS](docs/STEP_05_ACCEPTANCE.md)
- [Raport pokrycia ligi × sezon](docs/audits/API_FOOTBALL_STEP05_2026-10-25.md)
- [Krok 06 — diagnostyka PitchAPI, BLOKADA](docs/STEP_06_BLOCKER.md)

**Stan przy aktualizacji tego README (25.10.2026):** kroki 01–05 ZALICZONE, krok 06 ZABLOKOWANY (PitchAPI HTTP 401 / SDK AuthError), kroki 07–29 jeszcze niezaliczone. Dokładny stan na dany dzień należy zawsze sprawdzić w planie Google Docs. Żaden nowy model ani uczenie ML nie zostały uruchomione.

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
