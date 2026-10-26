# KB Score 3.0 — Krok 13: bezpieczny test na historii (konstrukcja v0.2)

**26.10.2026 — PR wdrożeniowy.** Zbudowany jest **mechanizm chronologicznego odtwarzania walidacji**, nie rzeczywisty historyczny backtest. M0 Elo + Poisson w kroku 13 ma nadal bramkę **GATE13 PENDING**, a dane `training_allowed=false`.

## 1. Co wykonuje test i dlaczego

Na początku każdego kwartalnego folda, osobno dla dwóch sposobów historii z kroku 12:
1. **EXPANDING:** wszystkie wcześniej rozgrywane mecze od 1 lipca 2023. **ROLLING:** ostatnie 24 miesiące kalendarzowe.
2. Z wcześniejszych zakończonych meczów aktualizuje ratingi Elo. Do historii w demonstracji syntetycznej dopuszcza wynik tylko, gdy kickoff + 48 godzin oraz udokumentowany moment otrzymania wyniku są wcześniejsze od **początku folda**. Sztuczne dane mają celowo prawidłowe godziny odbioru.
3. **Zamraża ocenę zespołów na początku okresu walidacji.** Dla każdego meczu VALIDATION tworzy prognozę M0 bez używania wyników jakiegokolwiek spotkania z tego kwartału. Nie dopasowuje parametrów w obrębie tego folda. Kolejny fold może włączyć wcześniejszą walidację do TRAIN tylko na podstawie nowego cutoff i dowodu dostępności.
4. **Dopiero po zapisaniu wszystkich prognoz** oddzielnie czyta ledger wyników do oceny; etykieta analizowanego meczu nie jest cechą. Miar nie obliczamy przy brakującym choćby jednym wyniku z wybranej walidacji. Syntetyczne Brier/log loss/ECE nie są miarą trafności.
5. Zakaz wejść bukmacherskich, dodatkowych pól z etykietą, przyszłych meczów, nieprawidłowych dat, duplikatów oraz **TEST**. Przy niezatwierdzonym źródle fail closed.

## 2. Reguły dowodowe: nie mylić `event_time` z `observed_at`

- Data kickoff meczów historycznych jest znana z terminarza, lecz **nie dowodzi**, kiedy pobrano lub opublikowano ich 90-minutowe wyniki i cechy.
- Hipotetyczny replay z `kickoff+48h` może być **eksperymentem retrospektywnym**, a NIE historycznym dowodem publikacji/obserwacji `observed_at`. Nie wolno podmieniać rzeczywistej daty pobrania na domyślne 48 godzin.
- Osobna klasa `OBSERVED_ASOF` będzie wymagać zweryfikowanych capture receipts i źródłowego czasu dostępności dla każdej cechy przed cutoff. Kwarantanna nie może zostać zniesiona zwykłym flagowaniem JSON.
- Dzisiejszy kod `replay_synthetic_fold(...)` działa **tylko dla jawnych syntetycznych rekordów** (brak dostępu do zewnętrznych wyników); niezależnie od wyniku ustawia `historical_pit_certified=false`, `historical_metrics_available=false`, `gate13_pass=false`.
- **Niezmienność**: `real_schedule_probe()` sprawdza opublikowany, przypięty hash widoku z kroku 12 i identyczność rekonstrukcji obu wariantów. Czyta tylko identyfikatory meczu i datę kickoff; nie czyta wyników, nie próbuje trenować ELO na realnej historii.

## 3. Weryfikacja na 1520 prawdziwych ID (bez etykiet)

| Fold 2025/26 | EXPANDING — terminarz | ROLLING — terminarz | Wspólne VALIDATION | Certyfikowany TRAIN |
|---|---:|---:|---:|---:|
| VII–IX 2025 | 760 | 760 | 60 | 0 |
| X–XII 2025 | 820 | 753 | 126 | 0 |
| I–III 2026 | 946 | 750 | 123 | 0 |
| IV–VI 2026 | 1069 | 776 | 71 | 0 |

**Raport wyjściowy:** [STEP13_REAL_FOLD_READINESS_2026-10-26.json](../data/audits/STEP13_REAL_FOLD_READINESS_2026-10-26.json), SHA256 `814b58950a387ec206673203c51a494b1b82a3a199ab1f9b28f77dac4e84e29b`. Pola `real_backtest_performed`, `historical_predictions_made`, `real_metrics_available`, `training_allowed` i `gate13_pass` są jawnie **false**. Łącznie **0 historycznych próbek z certyfikatem PIT**.

## 4. Implementacja i testy bezpieczeństwa

- [Silnik symulacji foldów](../src/kb3_step13_fold_replay.py): utrzymuje dwie metody historii, 48-godzinny embargo, zamrożenie prognoz, odrębny ledger etykiet, detekcję braku wyników.
- [Testy niezmienności wyniku prognozy przy manipulacji etykietą VALIDATION](../tests/test_step13_fold_replay.py), m.in. zmiana 2:0 na 0:7 zmienia **wyłącznie ocenę skuteczności**, nie prognozowane P; wprowadzenie TEST, kursu, błędnego czasu, zduplikowanego ID lub fikcyjnego dowodu powoduje odmowę.
- [GitHub Actions PASS](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40377868431): regresje Kroku13 i Step12 + generacja niezmiennego realnego raportu *tylko terminarza*. Nie ma nowego kosztu API ani zależności od kluczy.

## 5. Co blokuje formalny odbiór kroku 13

Nie istnieje jeszcze certyfikowany historyczny wsad zawierający zarazem:
- natywne ID meczów i drużyn,
- wynik 90-minutowy z dowodem autentycznego momentu dostępności,
- historycznie dostępne przed meczem cechy lub osobno zatwierdzony badawczy sposób rekonstrukcji,
- pełną i spójną próbę TRAIN i VALIDATION z dokładnymi identyfikatorami,
- odrębny manifest jakości, akceptujący eksperyment, ale **nie** nazywający hipotetycznego backtestu historycznym PIT.

Dopiero po odrębnym audycie tego źródła można rzetelnie dobrać parametry baseline i porównać EXPANDING z ROLLING za pomocą Brier, log loss i kalibracji. **Nie dobieramy parametrów z użyciem TEST.**

**GATE13 PENDING, ukończone kroki 12/29, trening rzeczywisty zablokowany.**
