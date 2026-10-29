# KB Score 3.0 — rzeczywiste rozliczenia 1/X/2, log loss, Brier i kalibracja M0

**29 października 2026 · status: automatyzacja badawcza · GATE14=PENDING, 13/29.** Dokument obowiązuje razem z [ADR decyzji](ADR_2026-10-29_FORWARD_M0_PIT_CALIBRATION_STORAGE.md) i [planem 29 kroków](PLAN.md).

## Operacja dzienna

[Workflow GitHub](../.github/workflows/kb3-m0-shadow-daily-settlement.yml) wykonuje o **07:03 UTC codziennie** kontrolę trzech lig (Hiszpania LaLiga, Włochy Serie A, Niemcy Bundesliga; sezon 2026/27) przez istniejący sekret `PITCHAPI_API_KEY`. Cztery rzeczywiste wywołania (katalog i 3 terminarze), SHA i czas serwera; surowe odpowiedzi zaszyfrowane za pomocą znanego publicznego klucza RSA/AES-GCM. Raporty `data/settlements/m0_shadow_daily/YYYY-MM-DD/M0_DAILY_SETTLEMENT_AUDIT.json` oraz zaszyfrowany `.enc` i manifest dopisywane do prywatnego `main`; stan wynikowy w istniejącej `data/forward_m0/kb3_forward_m0.sqlite`, migracja [004](../migrations/004_m0_shadow_settlement_and_future_calibration.sql).

**Warunki dopuszczenia wyniku:** niezmienny oryginalny forecast M0 wygenerowany >=90 minut przed kickoff, prawidłowe unikalne ID meczów i obu drużyn, ta sama godzina kickoff, `status=finished`, dwie całkowite bramki 90-minutowe, rzeczywisty odczyt >=3 godziny po kickoff. Mecz przełożony, zmiana ID, inna godzina lub późniejsza zmiana wcześniej rozliczonego wyniku => brak automatycznej podmiany, przypadek do kontroli. Jeden forecast to dokładnie jedno rozliczenie. Wszystkie wpisy są append-only, UPDATE/DELETE zablokowane.

## Matematyka i wskaźniki

- `log_loss = -ln(p_rzeczywistej_klasy)` — oryginalna matematyka `src/kb3_step14_m1_math_calibration.py::score_one`.
- `Brier sum3 = (p_1-I_1)^2 + (p_X-I_X)^2 + (p_2-I_2)^2` — **nie dzielimy przez 3**, zakres 0–2. Niższy wynik lepszy.
- Dla modelu i każdej ligi oraz agregatu 3 lig raport zawiera średni log loss, średni Brier sum3, top-1 accuracy, ECE w 10 koszykach, liczność. Nie liczyć trafności ze spotkań nierozliczonych.
- Wszystkie wcześniej zamrożone 1/X/2 pozostają nienaruszone; późniejszy wynik jest osobnym zapisem z dowodem źródłowym.

## Kalibracja tylko dla przyszłych prognoz

- **20–30 rzeczywiście zakończonych prognoz:** wyłącznie diagnostyka.
- **>=100 prawdziwych, zamrożonych i rozliczonych prognoz tego samego `model_version+parameter_sha256+EARLY`**: dopasowanie pierwszego kandydata temperatury na zamkniętym zbiorze, siatka `0.7, 0.85, 1.0, 1.15, 1.4, 1.8, 2.2`, minimalizowanie log loss. Wynik i jego czas odcięcia oraz SHA próbek zapisane w **niezmiennym** `m0_shadow_calibration_candidates`.
- **>=50 innych rozliczonych spotkań, dla których prognozy zostały wygenerowane dopiero po tamtym odcięciu**: niezależna ewaluacja wcześniej zamrożonej temperatury w `m0_shadow_calibration_evaluations`, porównanie log loss, Brier i ECE z surowym M0. Ocena nie zasila wcześniejszego dopasowania.
- **Autoaktywacja zawsze wyłączona**, także po pozytywnym wyniku. Wymagana późniejsza decyzja oraz kontrola statystyczna.

**Ochrona:** nigdy nie pobieramy wyników oryginalnego TEST Premier League 2026/27 na potrzeby kalibracji; odrębne historyczne zbiory i `GATE14` nie są zmieniane. M0 nadal wykorzystuje **wstępne, niefitowane** parametry Poissona. Nie traktować tych prognoz jako zweryfikowanych typów bukmacherskich.

**Aktualny status liczb:** dopiero po pierwszym rzeczywistym wykonaniu workflow sprawdzić, ile spotkań spośród 12 oryginalnie zamrożonych 29.10.2026 już się zakończyło. Gdy nie ma prawdziwego zakończonego meczu, wynik 0 jest poprawny; nie wolno go uzupełniać danymi syntetycznymi. Niezależny backup SQLite na Google Drive pozostaje zadaniem otwartym.
