# KB Score 3.0 — Krok 14: 18/18 prawdziwych native PitchAPI ID, xG 2025 i pozostałe cechy

**Wykonanie:** 29.10.2026. [Rzeczywisty GitHub Actions PR — SUCCESS](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40870078157).

## 1. Oryginalne identyfikatory spotkań (realny odczyt API)

- Wykorzystano istniejący sekret PitchAPI GitHub Actions, bez nowych kluczy, szyfrowania i opłat.
- Oryginalny SDK `pitchapi==0.1.6`; katalog Premier League ENG `2025/2026` i dokładne 380 oryginalnych natywnych fixture IDs. Zgodność *całego zbioru 380* z zamrożonym SAFE VALIDATION została sprawdzona przed indywidualnym dopasowaniem.
- **18/18** publicznych listopadowych i styczniowych spotkań udało się związać z oryginalnym `PitchAPI match.id`, oboma oryginalnymi `team.id`, datą/godziną UTC oraz zgodnymi home/away. Bez fuzzy matching i dopasowywania wyłącznie po czasie; **0 nierozstrzygniętych**.
- Identyfikatory, home/away i źródłowy SHA historycznej publikacji są w [raporcie audytu](../data/audits/STEP14_2025_FPLCORE_NATIVE_18_XG_SEMANTICS_2026-10-29.json), powiązane z pierwotnym [raportem badawczym](../data/audits/STEP14_2025_FPLCORE_INDEPENDENT_ASOF_RECOVERY_2026-10-29.json).
- Ani wyników, ani xG docelowych 18 meczów nie wykorzystano. Chroniony TEST 2026/27 nieodczytany.

## 2. Rzeczywista różnica xG między źródłami

- Osobne **6 poprzednich, już rozegranych** spotkań z historycznego `FPL-Core-Insights` z dokładnej wersji opublikowanej 07.11.2025, dopasowanych również po obu stronach, terminie i natywnym fixture ID.
- 6 wywołań `PitchAPI matches.stats`, łącznie **8 wywołań SDK** w tym pobranie katalogu i całego sezonu. Okres **All**, pole `expected_goals` z prawidłowej grupy `Expected goals (xG)`, nie `xGOT`, `npxG`, I połowa.
- **12 stron drużynowych**, średnia absolutna różnica **0,0**, maksymalna różnica **0,0** w zwróconej precyzji. Jest to lokalna zgodność numeryczna na małej próbce; nie potwierdza uniwersalnej równoważności definicji i nie dowodzi, że historyczne PitchAPI podawało tę samą wartość przed przyszłymi meczami. Archiwalne xG trzymamy jako **alternatywne źródło**, bez cichej podmiany oryginalnego xG.

## 3. Odzyskanie pozostałych cech

Nowy [skrypt](../scripts/step14_fplcore_2025_extended_field_recovery.py) pobrał ponownie *oryginalne, historycznie poświadczone* pliki `FPL-Core-Insights` z dokładnych commitów, a nie z dzisiejszej gałęzi. Na 18 docelowych meczach obliczył dostępne:
- **FORM5, FORM10, FORM15**: punkty, gole strzelone i stracone oraz historyczne wartości alternatywne xG/xGA;
- osobne okna **all/venue** (drużyna gospodarza u siebie, drużyna gościa na wyjeździe);
- liczność okna, liczność dostępnych wcześniejszych wyników i statystyk, czas od ostatniego kickoff i odpowiadające im flagi braków.

**Rzeczywisty wynik:** na 18 historycznie poświadczonych publicznych targetach:
- **102 spośród 121** nazw pól liczbowych otrzymały przynajmniej jedną *badawczą* wartość (nie oznacza to 102 kompletnych wartości w każdym meczu);
- **1336** niepustych wartości liczbowych oraz **499** niepustych flag braków, w odrębnej, niekwalifikującej się do oryginalnego M1 macierzy;
- pozostałe pola zachowują **null**, a nie wymyślone 0. **Nie odtwarzamy pozornie prawdziwego Elo** z niepełnego łańcucha poprzednich sezonów; sam FPL-Core rating Elo ma inną metodologię.
- Testy kontrolują zgodność wszystkich odzyskanych FORM5 z oryginalnym 18-row as-of, blokują przyszłe wyniki i niedostępne poprzedniki. Odizolowane wadliwe pliki nadal pozostają odizolowane.

[Zapisany wynik pełnej częściowej macierzy](../data/audits/STEP14_2025_FPLCORE_EXTENDED_121_38_PARTIAL_2026-10-29.json). Można go wykorzystać w badawczym porównaniu alternatywnej specyfikacji, ale **nie** jako oryginalny PitchAPI `121 + 38` treningowy snapshot.

## 4. Stan formalny i pozostające wymagania

**GATE14=PENDING, formalnie 13/29.** Oryginalny CatBoost M1 nie został wytrenowany, nie modyfikowano splitu, 2026/27 TEST, prognoz M0 ani Elo/Poisson.

Do pełnego oryginalnego odbioru nadal brakuje:
1. Potwierdzenia **natywnej zgodności oryginalnych wartości 121+38** (nie tylko nazwy i ID targetu), przede wszystkim Elo z pełnym łańcuchem 2023–2025.
2. Autentycznego `provider original first_published_at` oraz historii korekt xG PitchAPI dla dawnych spotkań (lub jawnej decyzji o nowym, alternatywnym kontrakcie xG).
3. Pełnego coverage historycznych TRAIN 760 i VALIDATION 380 — aktualne 18 to **badawczy podzbiór źródłowo poświadczony**, nie automatyczne dopuszczenie tych 18 do modelu oryginalnego.

Nie wolno mylić technicznego PASS dopasowania i odzyskania części statystyk z matematycznym zatwierdzeniem oryginalnego M1.

## Potwierdzenie końcowe po scaleniu do main

[PR #92](https://github.com/karolbarankiewicz1984-ui/kb-score-3/pull/92) **MERGED**. [GitHub Actions main #40870289735](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40870289735) **SUCCESS**, w tym testy, oba rzeczywiste skrypty, 8 połączeń do PitchAPI, wygenerowanie dwóch artefaktów oraz skuteczny zapis trwałych raportów w prywatnym `main`. Pliki pobrano ponownie po zapisie:
- [Native 18/18 i xG](../data/audits/STEP14_2025_FPLCORE_NATIVE_18_XG_SEMANTICS_2026-10-29.json): 18/18 dokładnych połączeń, 0 błędów, 12 porównanych xG, MAE = 0, MAX = 0 na badawczej próbce.
- [Wektor badawczy 121+38 z brakami](../data/audits/STEP14_2025_FPLCORE_EXTENDED_121_38_PARTIAL_2026-10-29.json): 18 rekordów, 102 nazwy numeryczne z ≥1 odzyskaną wartością, 1336 wartości liczbowych, 499 flag. **19 niedostępnych nazw cech** dotyczą pełnego Elo / wcześniejszych sezonów / średniego Elo rywali. To techniczne pola nieodtworzone przez to jedno źródło, nie podstawiane fikcyjnymi danymi.
