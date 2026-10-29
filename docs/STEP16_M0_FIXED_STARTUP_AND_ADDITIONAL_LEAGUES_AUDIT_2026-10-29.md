# KB Score 3.0 — Krok 16: audyt startu stałego M0 i rozszerzenia lig
**29.10.2026 | rzeczywiste sprawdzenie GitHub main i PitchAPI | GATE16 PENDING | formalnie 15/29.**

## 1. Czy docelowy, dopasowany M0 już działa?
**NIE.** Aktualny dzienny freeze i realny settlement uruchamiają dokładnie `src/kb3_m0_shadow_1x2_live_freeze.py` z domyślnym `BaselineParameters()` i statusem `ILLUSTRATIVE_UNFITTED_NOT_FOR_BETTING`; kod `m0_shadow_1x2_forecasts` i `m0_shadow_1x2_settlements` jest wyłącznie badawczy. Wersja jest stała w zakresie demonstracyjnych parametrów, lecz **nie jest wersją M0 wytrenowaną na rzeczywistych 720 TRAIN**.

Z odrębnego niezależnego porównania `data/audits/STEP14_M1R_BASE_CATBOOST_720_374_REAL_METRICS_2026-10-29.json` odczytano **rzeczywiście dopasowanego M0 na 720 TRAIN** (374 osobne VALIDATION):
- średnia bramek HOME `base_home_goals = 1.6447363878515198`;
- AWAY `base_away_goals = 1.4381853609496382`;
- `elo_goal_elasticity = 0.6`;
- `initial_elo=1500, elo_k=20, elo_scale=400, elo_home_advantage=65, poisson_max_goals=64, poisson_tail_tolerance=1e-12`.
- Wynik benchmarku 374 VAL: **Brier sum3 0.6202985148675613, multiclass log loss 1.0351077036805323**. Wszystkie te liczby są z pierwotnego zapisanego audytu, nie z dzisiejszych rozliczeń forward.

Zapisano dokładny kandydat parametryczny: [models/research/M0_720_TRAIN_STABLE_CANDIDATE_20261029.json](../models/research/M0_720_TRAIN_STABLE_CANDIDATE_20261029.json). To **manifest RESEARCH**, nie nowa wersja live; ochrona 2026/27 Premier League TEST bez zmian. Retrospekcja wejściowa 720 miała formalnie przyjętą kategorię B, a **nie oryginalny strict PitchAPI PIT**.

**Werdykt:** `M0_720TRAIN_CANDIDATE_READY_FOR_SEPARATE_VERSIONED_SHADOW_RELEASE`, ale `M0_720TRAIN_ACTIVATED=false`. Nie wolno automatycznie doliczać 12 starych prognoz ilustracyjnego M0 do prób kalibracji nowej wersji: inne SHA/parametry to osobny strumień.

## 2. Prawdziwy, jednorazowy audyt lig z tym samym kluczem PitchAPI
[Github Actions #40939139273 — SUCCESS](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40939139273), **23 rzeczywiste wywołania API**, zero zapytań o wyniki chronionego Premier League TEST. W raporcie tylko tożsamość rozgrywek, pola statusu i hashe, nie ma nowych prognoz ani surowych źródłowych odpowiedzi.

Źródło: [data/audits/STEP16_ADDITIONAL_LEAGUES_LIVE_20261029.json](../data/audits/STEP16_ADDITIONAL_LEAGUES_LIVE_20261029.json).

| Dodatkowa liga | Sezony 25/26 + 26/27 | Przykładowy natywny xG (shots i stats) | Wniosek |
|---|---|---|---|
| Francja Ligue 1 | Tak | Potwierdzony | KANDYDAT DO PILOTA |
| Holandia Eredivisie | Tak | Potwierdzony | KANDYDAT DO PILOTA |
| Belgia Pro League | Tak | Potwierdzony | KANDYDAT DO PILOTA |
| Turcja Süper Lig | Tak | Potwierdzony | KANDYDAT DO PILOTA |
| Polska Ekstraklasa | Tak | Potwierdzony | KANDYDAT DO PILOTA |
| Portugalia Primeira Liga | Brak dopasowania nazwy i obu sezonów w katalogu | Nie sprawdzano | WYMAGA IDENTYFIKACJI NAZWY / POKRYCIA |
| Anglia Championship | 2026/27 dostępny, ale 2025/26 nie spełnił kontroli wszystkich spotkań zakończonych | Nie sprawdzano | WSTRZYMAĆ |

W pięciu pozytywnych przypadkach źródło PitchAPI raportuje `advertised_free=true` i rzeczywiście zwróciło dane z już skonfigurowanym kluczem, **bez opłaty za nowy pakiet**. To nie dowodzi jednak pełnego xG ostatnich 15 meczów każdej drużyny ani gotowości kompletnego automatu do zbierania próbek. NED 2025/26 ma 309 spotkań, BEL 2025/26 ma 313; istniejące, sztywne założenie dokładnie 306 meczów dla nowych 18-zespołowych lig jest więc niewłaściwe. Włączenie wymaga osobnej interpretacji meczów sezonu/play-off oraz kontroli ciągłości identyfikatorów drużyn.

## 3. Wdrożenie szybkiej kalibracji: czego jeszcze brakuje
1. Odseparowany nowy model/version i osobne append-only SQLite/predictions/settlement dla **720-TRAIN M0**. Najpierw zamrozić jeden parametr SHA i listę lig; stary badawczy M0 SHADOW nie może być przepisany ani mieszany.
2. Uogólnić dzienny kolektor, dopuszczenie liga–sezon, rozliczanie i kontrolę 1/X/2 z trzech do maksymalnie ośmiu lig, bez dotykania 2026/27 Premier League TEST. Zintegrować NATYWNYM PitchAPI regularny sezon i play-offs, brakujące xG zachowywać jako null z flagą, żadnego przyszłego wyniku w cechach.
3. Przed pierwszym zliczeniem prognoz doprowadzić osobny dowód pierwszego zewnętrznego utrwalenia SHA/czasu publikacji (sam SHA w repo nie dowodzi czasu pierwszego zapisu).
4. Dopiero **100 faktycznie zakończonych różnych meczów** nowej stałej wersji/tej samej polityki lig do T, a następnie **50 nowych prognoz powstałych po T** do niezależnego sprawdzenia. Dodatkowo stabilność wyników per liga, nie tylko aggregate. GATE16 nie zmienia się i kalibrator nie awansuje samoczynnie.
5. Sprawdzić działanie nowej wersji na żywo jako równoległy badawczy SHADOW, zanim zostanie nazwana docelowym Championem. Parametry dopasowane na Premier League mogą być nietrafne dla innych lig: sprawdzić transfer domenowy, nie zakładać z góry poprawnej kalibracji.

**Najbliższa decyzja techniczna:** przygotować osobne, wersjonowane uruchomienie M0 720-TRAIN z audytem pierwszego prawdziwego freeze i settlement, oraz kolektor najpierw z pięcioma pozytywnie sprawdzonymi dodatkowymi ligami. Nie uruchamiano jeszcze nowego produkcyjnego M0 ani nie zadeklarowano dodatkowych próbek. Bez nowego abonamentu.
