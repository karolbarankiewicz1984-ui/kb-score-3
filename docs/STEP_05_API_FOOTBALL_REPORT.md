# KB Score 3.0 — Krok 05: audyt API-Football

**Data:** 25.10.2026, uruchomienie 17:47:54–17:49:37 UTC (18:47–18:49 Europe/Warsaw). **Źródło:** [GitHub Actions run #40218180472](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40218180472) zakończony **success**. **Wynik:** audyt wykonany (bez uruchamiania modelu); kryteria odbioru podane na końcu.

**Dane maszynowe:** [25 rekordów audytowych JSON](../data/api_football_coverage_2026-10-25.json). **Kod audytu:** [scripts/step05_api_football_audit.py](../scripts/step05_api_football_audit.py). **Testy:** [test_step05_api_audit.py](../tests/test_step05_api_audit.py). **Plan:** [Google Docs — źródło prawdy](https://docs.google.com/document/d/10wjHL3r3OAuxtezwcIeWztxS8lwjhYon5GM3BLhI0xE/edit).

## 1. Co faktycznie sprawdzono

- Pięć lig: Premier League (ID 39), La Liga (140), Bundesliga (78), Serie A (135), Ligue 1 (61).
- Pięć sezonów startowych: 2022, 2023, 2024, 2025 i **2026 (bieżący, w trakcie)**. RAZEM: **25 kombinacji liga × sezon**.
- Dla każdej: `/leagues?id&season` z deklaracją pokrycia oraz pełne `/fixtures?league&season` z liczebnością i statusami; **dwa deterministycznie wybrane zakończone mecze** z `/fixtures/statistics`; jeden zakończony mecz dla `/fixtures/lineups`.
- Dodatkowo po jednej stronie wyników `/odds?league&season=2026&page=1` na ligę; nie jest to pełne archiwum historycznych kursów.
- Łącznie **131 odczytów API**, **0 błędów odpowiedzi** i **0 komórek ze zgłoszonym błędem podczas odczytu**. Testy offline kontraktów przeszły w Actions.

## 2. Podsumowanie ilościowe

| Miara | Odczyt |
|---|---:|
| Wszystkie rekordy wydarzeń 2022–2026 | 8849 |
| Wszystkie ze statusem zakończonym FT/AET/PEN | 7477 |
| Sezony 2022–2025: rekordy spotkań | 7097 |
| Sezony 2022–2025: zakończone FT/AET/PEN | 7096 |
| Deklaracja `statistics_fixtures=true` | 25/25 |
| Próbki statystyk: obie drużyny z danymi niepustymi | 50/50 |
| Próbki fauli: dane obu drużyn | 50/50 |
| Próbki rożnych: dane obu drużyn | 50/50 |
| Próbki żółtych kartek: dane obu drużyn | 49/50 |
| Próbki czerwonych kartek: dane obu drużyn (NIE zakładać 0 przy braku) | 9/50 |
| Składy wyjściowe obu drużyn — próbki | 25/25 |

**Uwaga:** wszystkie liczby próbek odnoszą się do **wybranych meczów**, nie do pokrycia pełnej ligi. `NULL` w statystykach oznacza brak danych, a nie zero fauli lub kartek.

## 3. Tabela liga × sezon × dane

Tabela pokazuje deklarowane pokrycie danych meczowych (D), liczbę spotkań (M), liczbę meczów zakończonych (F), faktycznie sprawdzone próbki statystyk obu drużyn (S), fauli (Fa), rożnych (R) i kompletny skład obu jedenastek w pojedynczej próbce (XI). Flagi deklarowane po stronie API **nie gwarantują** kompletności wszystkich spotkań.

| Liga | Sezon | M | F | D stat. | S | Fa | R | XI | D odds |
|---|---:|---:|---:|:---:|---:|---:|---:|:---:|:---:|
| Premier League | 2022 | 380 | 380 | TAK | 2/2 | 2/2 | 2/2 | TAK | NIE |
| Premier League | 2023 | 380 | 380 | TAK | 2/2 | 2/2 | 2/2 | TAK | NIE |
| Premier League | 2024 | 380 | 380 | TAK | 2/2 | 2/2 | 2/2 | TAK | NIE |
| Premier League | 2025 | 380 | 380 | TAK | 2/2 | 2/2 | 2/2 | TAK | NIE |
| Premier League | 2026 | 380 | 79 | TAK | 2/2 | 2/2 | 2/2 | TAK | TAK |
| La Liga | 2022 | 380 | 380 | TAK | 2/2 | 2/2 | 2/2 | TAK | NIE |
| La Liga | 2023 | 380 | 380 | TAK | 2/2 | 2/2 | 2/2 | TAK | NIE |
| La Liga | 2024 | 380 | 380 | TAK | 2/2 | 2/2 | 2/2 | TAK | NIE |
| La Liga | 2025 | 380 | 380 | TAK | 2/2 | 2/2 | 2/2 | TAK | NIE |
| La Liga | 2026 | 380 | 96 | TAK | 2/2 | 2/2 | 2/2 | TAK | TAK |
| Bundesliga | 2022 | 308 | 308 | TAK | 2/2 | 2/2 | 2/2 | TAK | NIE |
| Bundesliga | 2023 | 308 | 308 | TAK | 2/2 | 2/2 | 2/2 | TAK | NIE |
| Bundesliga | 2024 | 308 | 308 | TAK | 2/2 | 2/2 | 2/2 | TAK | NIE |
| Bundesliga | 2025 | 308 | 308 | TAK | 2/2 | 2/2 | 2/2 | TAK | NIE |
| Bundesliga | 2026 | 306 | 62 | TAK | 2/2 | 2/2 | 2/2 | TAK | TAK |
| Serie A | 2022 | 381 | 381 | TAK | 2/2 | 2/2 | 2/2 | TAK | NIE |
| Serie A | 2023 | 380 | 380 | TAK | 2/2 | 2/2 | 2/2 | TAK | NIE |
| Serie A | 2024 | 380 | 380 | TAK | 2/2 | 2/2 | 2/2 | TAK | NIE |
| Serie A | 2025 | 380 | 380 | TAK | 2/2 | 2/2 | 2/2 | TAK | NIE |
| Serie A | 2026 | 380 | 78 | TAK | 2/2 | 2/2 | 2/2 | TAK | TAK |
| Ligue 1 | 2022 | 380 | 380 | TAK | 2/2 | 2/2 | 2/2 | TAK | NIE |
| Ligue 1 | 2023 | 308 | 308 | TAK | 2/2 | 2/2 | 2/2 | TAK | NIE |
| Ligue 1 | 2024 | 308 | 308 | TAK | 2/2 | 2/2 | 2/2 | TAK | NIE |
| Ligue 1 | 2025 | 308 | 307 | TAK | 2/2 | 2/2 | 2/2 | TAK | NIE |
| Ligue 1 | 2026 | 306 | 66 | TAK | 2/2 | 2/2 | 2/2 | TAK | TAK |

## 4. Kursy (kontrola działania, nie historia)

| Liga | Rekordy na pierwszej stronie kursów dla sezonu 2026 | Liczba stron zwrócona przez API |
|---|---:|---:|
| Premier League | 10 | 3 |
| La Liga | 10 | 3 |
| Bundesliga | 10 | 2 |
| Serie A | 10 | 3 |
| Ligue 1 | 10 | 3 |

Dostęp do bieżących danych o kursach potwierdzony, ale NIE ma tutaj historycznego snapshotu bukmacherskiego dla meczów z 2022–2025. API podaje krótką retencję kursów przedmeczowych; dane historyczne do EV/ROI muszą mieć prawdziwy timestamp lub odrębne źródło, a nie zostać dopisane wstecz.

## 5. Limity i koszt

| Parametr | Wynik w czasie tego audytu |
|---|---|
| Plan dostępu | API-Football Pro z wcześniejszego kroku 01 |
| Nagłówek limitu dziennego | 7500 zapytań |
| Nagłówek limitu minutowego | 300 zapytań |
| Nagłówek remaining przy pierwszej odpowiedzi | 6982 |
| Nagłówek remaining przy ostatniej odpowiedzi | 6880 |
| Liczba rzeczywistych prób zapytań z audytu | 131, limit skryptu 145 |
| Nowe zakupy | Brak; wykorzystano istniejącą pulę abonamentu |

Liczniki pozostałych zapytań mogły zmieniać się także z powodu innych workflow. Nie wyliczamy kosztu pieniężnego pojedynczego zapytania, skoro mieściło się ono w posiadanym abonamencie. Nie traktować tego zrzutu jako aktualnego stanu limitu po audycie.

## 6. Wykryte odchylenia i ograniczenia

1. **Serie A 2022:** dostawca zwrócił **381** spotkań zamiast zwyczajowych 380. Nie należy automatycznie usuwać dodatkowego wiersza; w kroku 10 ustalimy, czy to mecz dodatkowy, duplikat czy inna definicja rozgrywek.
2. **Ligue 1 2025:** **308 rekordów**, ale tylko **307** ze statusem FT/AET/PEN. Jeden posiada `AWD` (walkower/rozstrzygnięcie administracyjne). Nie wolno bez ustalonej polityki używać go do treningu jako standardowego rezultatu 90 min.
3. **Sezon 2026:** jest w trakcie, więc wiele pozycji ma `NS`, `1H`, `2H`, a La Liga również `ABD`; nie wszystkie mogą być etykietami treningowymi.
4. **Czerwone kartki:** niezerowa liczba NULL w próbkach. Dla czerwonych kartek kompletna wartość była dostępna tylko w 9/50 kontrolowanych próbkach; nie imputować braków zerem.
5. **Liga/sezon coverage:** `coverage.fixture_statistics=true` oznacza deklarowaną obsługę, a nie kompletność dla 100% meczów.
6. **Prawdziwe xG:** niepotwierdzone w tym audycie; wymaga odrębnego testu PitchAPI w kroku 06. Nie zastępować xG liczbą strzałów.
7. **Historie składów:** odczyt składu po meczu nie dowodzi, że konkretny zawodnik lub absencja była potwierdzona przed kickoff. Wymagamy punktowych snapshotów w przyszłych modelach.
8. **Opóźnienie aktualizacji:** ta kontrola nie mierzyła różnicy pomiędzy prawdziwym czasem zdarzenia a czasem aktualizacji API; do monitorowania w przyszłych etapach, nie przypisywać metryki lag=0.
9. **Reprodukowalność:** kod i próbkowanie są deterministyczne. W bieżącym sezonie dane i liczniki będą się naturalnie zmieniały; zapisany snapshot z 25.10.2026 stanowi dowód historycznego odczytu.

## 7. Wynik bramki i przekazanie do kolejnych etapów

**KRYTERIA GATE 05:** tabela 25 liga×sezon×typ danych z liczebnościami — spełnione; konkretny skrypt i test wyboru próbek — spełnione; NULL nie zastępuje zera — spełnione; rzeczywiste odpowiedzi API i nagłówki limitu — potwierdzone; dowód [Actions](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40218180472) i [snapshot JSON](../data/api_football_coverage_2026-10-25.json).

**Ocena techniczna:** **PASS / ZALICZONO etap audytu**, nie oznacza to zatwierdzenia bazy treningowej. KROK 06 — audyt PitchAPI (xG) — nadal NIE ROZPOCZĘTY; KROKI 07–10 muszą oczyścić/matchować/archiwizować dane. Dane o kursach i punktowe zapisy przedmeczowe otrzymają osobne testy w krokach 19–21.
