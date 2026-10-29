# KB Score 3.0 — bieżące automatyczne rozliczanie M0, log loss, Brier oraz przyszła kalibracja

**ADR aneks: 29.10.2026 — status w chwili napisania: implementacja + testy; pierwszy realny wynik GitHub Actions i trwały zapis trzeba zweryfikować po merge.**

Powiązanie: [ADR 29.10.2026](ADR_2026-10-29_FORWARD_M0_PIT_CALIBRATION_STORAGE.md), [oryginalny plan 29 kroków](PLAN.md), [pierwsze prawdziwe zamrożone M0 1/X/2](STEP14_M0_REAL_PREMATCH_1X2_SHADOW_2026-10-29.md).

## Źródło wyniku i bezpieczeństwo

- Włączona w ramach GitHub Actions **cykliczna kontrola realnych wyników wyłącznie ESP LaLiga, ITA Serie A, GER Bundesliga** sezonu **2026/27**: 2 razy dziennie (07:47 i 22:47 UTC), maks. 4 rzeczywiste odpytywania istniejącym kluczem PitchAPI (`leagues.list` + 3 `leagues.matches`).
- Zanim jakikolwiek wynik zostanie przetworzony, `scripts/step14_m0_postmatch_real.py` sprawdza **już zapisane w GitHub** raporty `data/forecasts/m0_shadow_1x2/YYYY-MM-DD/FROZEN_M0_SHADOW_1X2.json`: hasz całego raportu, hasz każdej prognozy, nienadpisywalne wartości (1/X/2), identyfikatory i czasy oraz dokładną zgodność z tabelą SQLite `m0_shadow_1x2_forecasts`. Sam zapis hasza nie stanowi niezależnego poświadczenia pierwszej publikacji; nie wolno tego twierdzić.
- Pobieramy **tylko prawdziwe odpowiedzi NETWORK_OBSERVED**. Spotkania mogą być rozliczane dopiero gdy `status=finished`, `score_home` i `score_away` są całkowitymi nieujemnymi wynikami 90 minut, a od **oryginalnego kickoff minęły minimum 3 godziny**. Weryfikujemy **niezmienione** natywne `fixture_id`, `home_team_id`, `away_team_id`, **kickoff UTC** względem opublikowanej prognozy. Zmiany terminarza/tożsamości są **oznaczane do przeglądu, nie dopasowywane automatycznie**; POSTPONED/ABANDONED/AWARDED nie są oceniane jako zwykły wynik.
- Wynik zostaje utrwalony tylko **raz** w [migracji 004](../migrations/004_m0_shadow_settlements_and_calibration.sql) — `m0_shadow_1x2_settlements` z blokadą `UPDATE/DELETE`. Oryginalne M0 pre-match p(1), p(X), p(2) w tabeli `m0_shadow_1x2_forecasts` i wcześniejsze 121+38 cech NIE są zmieniane. Premier League 2026/27 oryginalnego TEST **nie jest ani odpytywana, ani trenowana**; nie zmieniono kryterium `GATE14`.
- Prawdziwe odpowiedzi źródłowe są archiwizowane RSA/AES-GCM w `data/pit_sidecar/m0_postmatch/YYYY-MM-DD/run-HHMMSSffffff/` (`ORIGINAL_PITCHAPI_RESULTS.enc` + SHA manifest), a jawny raport tylko w **prywatnym** repo (`M0_POSTMATCH_AND_CALIBRATION_REVIEW.json`). Katalog per-run pozwala wykonać oba kontrole tego samego dnia bez nadpisania żadnej wersji. SQLite `data/forward_m0/kb3_forward_m0.sqlite` jest kopiowana na plik staging; tylko cały poprawny przebieg zostaje zatwierdzony.

## Matematyka — bez własnej, innej definicji błędu

Korzystamy z oryginalnej funkcji `src/kb3_step14_m1_math_calibration.py::score_one`:
- Klasy w ścisłej kolejności **1 / X / 2**.
- **Log loss:** `-log(p_rzeczywistego_wyniku)` (logarytm naturalny; niższy lepszy).
- **Brier sum3:** `(p1-y1)^2+(pX-yX)^2+(p2-y2)^2` (zakres [0,2], **bez dzielenia przez 3**).
- Po każdym przebiegu pełna próba rozliczonych unikatowych prognoz `M0_ELO_POISSON_UNFITTED_SHADOW_FEATURES_V1`/`EARLY` otrzymuje średnie log loss, Brier sum3, skuteczność najczęściej typowanej klasy, `ECE` oraz tabelę reliability. W razie `0` zakończonych meczów — raport jawnie pokazuje `null` dla agregatu, nie wymyśla wyników ani kalibracji.

## Przyszły kalibrator: odróżnienie treningu i niezależnego TEST

To **kalibracja samych prawdopodobieństw** `temperature_probabilities`, NIE trening nowych wag Elo, Poissona czy CatBoost M1:
1. **20–30** prawdziwych rozliczeń — diagnostyka, bez zmiany modelu.
2. **Minimum 100** różnych, wcześniej zamrożonych i rozliczonych meczów jednej `model_version` i fazy `EARLY` — jednorazowe, append-only dopasowanie temperatury na **pierwszych 100** rzeczywistych próbkach. Źródło `m0_shadow_calibration_candidates` ma unikalny wiersz na wersję/fazę/zakres lig i zamrożony znacznik `fitted_at_utc`; startowy kalibrator **nie jest aktywowany automatycznie**.
3. Dopiero **minimum 50 kolejnych meczów z kickoff po `fitted_at_utc`** i wynikach rzeczywiście znanych później — porównanie raw vs temperatura na identycznym, nietkniętym holdout. Źródło `m0_shadow_calibration_holdout_reviews`, metryki log loss/Brier/ECE, raport oceny i `approved_for_production=0` na sztywno. Pierwsze 50 jest ustalane chronologicznie. Dotknięcie ich wyników podczas dopasowania temperatury zabronione. Uwaga: 100 i 50 to minimalne progi operacyjne, a nie gwarancja reprezentatywności.
4. Pooling lig **ESP/ITA/GER** to osobny badawczy strumień `ESP_ITA_GER_POOLED_RESEARCH`; żadnych transferów kalibracji do Premier League 2026/27 TEST ani automatycznego zatwierdzania. W przyszłości stabilność po ligach i okresach wymaga dodatkowego audytu. Gdy T=1 (neutralny), brak istotnej poprawy lub niespójność metryk, zostawiamy surowe prognozy.

**Implementacja:** `src/kb3_m0_live_settlement_calibration.py`, `scripts/step14_m0_postmatch_real.py`, `migrations/004_m0_shadow_settlements_and_calibration.sql`, [GitHub Actions](../.github/workflows/kb3-m0-real-postmatch-calibration.yml).

## Status względem 29 kroków

To **przyspieszony PILOTAŻ** elementów 16,21,22,24,26–27, nie formalne ich zaliczenie i nie zmiana planu. **Krok 14 i oryginalny M1 nadal GATE14 PENDING, 13/29**. Nie wykonano jeszcze niezależnego Google Drive backupu produkcyjnej SQLite. Pierwsze 12 rzeczywistych prognoz M0 były utworzone 29.10.2026 przed meczami; dopóki żaden z nich się nie zakończył, **0 prawdziwych rozliczeń jest całkowicie prawidłowym wynikiem** i brak oceny skuteczności. Przy każdym kolejnym uruchomieniu warunki i prawdziwe liczności są zapisywane w nowym raporcie.


## Potwierdzenie rzeczywistego uruchomienia — 29.10.2026

**POTWIERDZONE na `main`**, nie tylko założenie lub test syntetyczny. [GitHub Actions #40842252221](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40842252221) **SUCCESS**: 8/8 testów osłon rozliczeń i przyszłej kalibracji + 6/6 testów matematyki i przedmeczowego freeze; 4 prawdziwe zapytania PitchAPI przez wcześniej skonfigurowany klucz.

O 29.10.2026 08:27:44 UTC rzeczywisty przebieg dał **0 nowych / 0 łącznie rozliczeń**, ponieważ 12 świeżo zamrożonych prognoz dotyczy jeszcze nierozpoczętych lub niezakończonych spotkań. Log loss/Brier/ECE dla rzeczywistej próby pozostają **`null` / niedostępne**, a kalibrator 100+50 **nie został dopasowany**. Jest to zamierzone zachowanie chroniące przed dopisywaniem wyników z przyszłości.

Sprawdzono po wykonaniu fizyczną obecność na `main`:
- [raport na dziś](../data/pit_sidecar/m0_postmatch/2026-10-29/run-082743157159/M0_POSTMATCH_AND_CALIBRATION_REVIEW.json), zawiera `network_call_count=4`, 0/0 settlement, `candidate=null`, `aggregate_score=null`, `original_Premier_League_TEST_accessed=false`;
- `ORIGINAL_PITCHAPI_RESULTS.enc` (28 787 B) oraz `ORIGINAL_PITCHAPI_RESULTS.manifest.json` z oryginalnymi źródłami RSA/AES-GCM, SHA i rzeczywistym UTC;
- `data/forward_m0/kb3_forward_m0.sqlite` (2 985 984 B), z utworzonymi tabelami 004, bez modyfikacji 12 uprzednio zamrożonych prognoz. Test SQLite `integrity_check=ok`, `foreign_key_check=[]`, oryginalna tabela `predictions=0`, żadna kalibracja nie została aktywowana.

Harmonogram jest zapisany na `main` jako cron **07:47 UTC i 22:47 UTC codziennie**; kolejne wykonania potrzebują własnego wyniku/raportu, a nie deklaracji sukcesu z wyprzedzeniem. 29-etapowy plan: formalnie nadal 13/29; `GATE14=PENDING`.


### Aktualizacja metodologiczna 29.10.2026 — poprawiona ochrona przyszłej kalibracji

[PR #87](https://github.com/karolbarankiewicz1984-ui/kb-score-3/pull/87) zaakceptowany do main, [10 testów log loss/settlement/kalibracji + 6 testów prognozy M0](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40842920872) **PASS**. W przyszłości nie wolno mieszać zamrożonych prognoz o odmiennym `parameter_sha256` w jednej kalibracji tylko dlatego, że mają identyczny `model_version`; w takim przypadku przerywamy fit i wymagamy odrębnej wersji modelu. Niezależny HOLDOUT 50 obejmuje wyłącznie mecze z **prognozą faktycznie wygenerowaną PO cutoff zamrożonego kandydata** oraz kickoff po tym cutoff i etykietą poznaną przed review. Sam późniejszy kickoff bez późniejszej daty generowania prognozy nie wystarcza. Autoaktywacja wciąż 0. Żadnego przeliczenia starych prognoz lub wyników, tylko zabezpieczenie przyszłego fitu.
