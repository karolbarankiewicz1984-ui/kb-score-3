# KB Score 3.0 Step17 — przyspieszenie pozyskiwania ostatnich 5 xG bez zwiększania limitu API

**2026-11-01 | KROK 4 | BADAWCZY DRAFT PR #125 | LIVE NIEZMIENIONE NA MAIN**

## Ostatni rzeczywisty stan i zasób

- [2026-10-29 XG_READINESS_RECEIPT](https://github.com/karolbarankiewicz1984-ui/kb-score-3/blob/main/data/pit_sidecar/step17_native_xg_eight/2026-10-29/XG_READINESS_RECEIPT.json): 7 prawidłowych par natywnych `shots/stats` z 8, 1 niezgodność źródeł; zero pełnych rzeczywistych last5 dla 74 analizowanych przyszłych meczów. Żadnej próby trenowania modelu z xG.
- Kod aktualnie używany w `main`: z 17 wywołań katalog+fixtures wybiera w każdej z ośmiu lig **jeden** najnowszy istotny, ukończony mecz; następne 16 wywołań `shots/stats`, limit **33/cykl**, `06:41 UTC`. To wybór na podstawie chronologii, nie na podstawie liczby nadal brakujących pięciu poprzedników.
- Próba przyspieszenia nie polega na użyciu innego API, kupnie nowego abonamentu, retrospektywnej imputacji ani ujawnieniu chronionego TEST.

## Rzeczywiście zapisany eksperyment w odrębnej gałęzi

`src/kb3_step17_xg_priority_research.py` (commit początkowy `e38bd3a2...`) liczy dla każdego przyszłego meczu **dokładnie rzeczywistych ostatnich pięć zakończonych spotkań obu drużyn**, weryfikuje `kickoff+3h<=capture cutoff`, nie wykorzystuje wyników niezakończonych, pomija wcześniejsze xG już potwierdzone (`known`) i ocenia, które **brakujące** mecze należy pobrać w pierwszej kolejności. Im mniej danych brakuje do kompletnej serii, tym większa waga; bliższe przyszłe spotkanie ma priorytet wyższy.

`ranked_eight(... budget=8, per_league=1)`: **≤8** par `shots+stats` na cykl, nie więcej niż 1/ligę. `17+2×8=33` to maksymalna liczba wywołań. Brak sztucznego uzupełnienia brakującego xG i żadnego nowego ML fit. Nowe cechy nie są używane do prognoz ani do kalibracji.

- `src/kb3_step17_xg_capture.py` w **PR #125, nie na main**, najpierw oblicza oryginalny ranking, potem wybiera `ranked_eight` i do receipt dodaje nazwę polityki, baseline_count i audyt priorytetu. Dokumentuje porównanie selektorów bez dodatkowego requestu do PitchAPI.
- `tests/test_step17_xg_priority_research.py` zawiera cztery izolowane testy: ograniczenie 8 lig/33 call, preferencja brakującej niemal kompletnej serii, odmowa zbyt świeżych i nieukończonych źródeł, twarde strażniki budżetu. Prototypowa równoważna wersja tych testów lokalnie 4/4 PASS (Python 3.13).
- Harmonogram `06:41 UTC`, limit 33, nazwy ośmiu lig, oryginalne archiwum, blokady przedmeczowe, trigger `main`, wykluczanie ENG, nienaruszalność `data/`/`models/` bez zmian.
- Pierwsza zdalna [próba GitHub Actions #41284536791](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/41284536791) — `offline-xg-semantic-and-time-audit=SUCCESS`, `real-eight-native-xg-source=SKIPPED`, zatem **0 nowego API przez PR**. Obejmuje stare testy `test_step17_xg_capture.py` na zmienionej logice `run()`, lecz nie osobny czterotestowy nowy plik.
- Nowy [GitHub Actions #41284624705](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/41284624705), commit `1a4d61ead0bdf81818aa8db6dcf318e989651af8`: **offline-xg-semantic-and-time-audit SUCCESS**, w logach potwierdzone **4/4** nowych `test_step17_xg_priority_research.py`, **4/4** integracyjnych `test_step17_xg_capture.py`, **2/2** bramki xG oraz dalsze testy semantyki; `real-eight-native-xg-source SKIPPED`. Brak aktywności dostawcy i żadnych kosztów API w tym przebiegu. Komentarz nie upoważnia automatycznie do merge.

## Bramka przed ewentualnym połączeniem z produkcją

1. Nowe CI HEAD przechodzi dla całości, bez wywołań `real-eight-native-xg-source`.
2. Na **autentycznych, uprzednio zebranych snapshotach fixture** liczymy różnicę pokrycia `complete_last5_both_team_xg` nowego vs poprzedniego rankingu przy **identycznych max 33 provider requests**. Celem jest uzasadniony wzrost kompletnych serii, nie sama zmiana kolejności.
3. Osobna zgoda na merge i jeden kontrolowany live receipt; brak wstecznego dozbierania przedmeczowych xG, brak promowania CatBoost z xG.

**Status:** TESTOWANY RESEARCH / NIE WDROŻONY do `main`; `GATE16=PENDING`, `GATE17=PENDING`, formalnie 15/29. Dzienny faktyczny wzrost xG nie został jeszcze potwierdzony.
