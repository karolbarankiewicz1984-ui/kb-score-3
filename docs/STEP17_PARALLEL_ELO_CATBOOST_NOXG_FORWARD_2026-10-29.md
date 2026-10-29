# KB Score 3.0 — Krok 17: uruchomienie równoległych challengerów Elo-only i CatBoost bez xG

**29.10.2026 | etap przygotowania rzeczywistych prognoz, GATE17 PENDING, ukończone 15/29.**

## Decyzja i zabezpieczenia

Następne czynności właściciela: dwa kolejne silniki na identycznych nowych meczach, które ośmioligowy M0 720-TRAIN już obejmuje. Nie wolno dopisać po fakcie nowych prognoz do wcześniejszych **73** M0 z 29.10.2026 (nawet gdy część spotkań jeszcze nie ruszyła), bo horyzont/źródło by się różniły. Start wspólnych nowych prognoz następuje dopiero po przyjęciu zmiany przez `main` w kolejnym rzeczywistym nowym przebiegu. **Zero domysłów co do liczby nowo zamrożonych prognoz dopóki nowy live run nie zakończy się sukcesem.**

## Wykonanie

- `src/kb3_step17_forward_challengers.py`: dwie odseparowane wersje badawcze:
  - `KB3_STEP17_ELO_ONLY_TRAIN720_DRAW_V1`. Wykorzystuje faktycznie wyliczone `EloExpectedHomePoints`, nie traktuje tych punktów błędnie jako `P(wygrana)`. Szacuje P(remis) ze **168/720 remisów TRAIN**; `P(1)=ExpectedPts-0,5*P(X)`, `P(2)=1-ExpectedPts-0,5*P(X)`, z deterministycznym ograniczeniem P(X) zapewniającym dodatnie prawdopodobieństwa. Wagi nie były dopasowywane na 374 VAL, TEST ani na przyszłych wynikach.
  - `KB3_STEP17_CATBOOST_M1R_BASE_TRAIN720_NOXG_V1`: istniejący rzeczywisty `M1_R_BASE_CATBOOST_720_TRAIN_2026-10-29.cbm`, dokładny SHA256 **07af285ff9dd45fa13dd54fd5e805270aff469434955cce998b601875f8fdab8**, 85 cech i ich ustalona podczas **720 TRAIN** kolejność. `CatBoostClassifier.load_model` i `predict_proba`, nigdy `fit`, `eval_set` lub tuning po zobaczeniu wyników. CatBoost SDK `1.2.8`. xG oraz brakujące dane o xG wyłączone, ponieważ historyczny PIT xG w innych ligach nie został dostatecznie poświadczony. Status **RESEARCH**.
- Obie wersje są liczone **w tym samym wywołaniu** `make_forecasts()` co oryginalny ośmioligowy M0 720-TRAIN, na tym samym `feature_sha256`, w tej samej chwili cutoff oraz na tych samych `league,provider_match_id,kickoff_utc`. **Nie dodano żadnego nowego zapytania PitchAPI** (pozostaje oryginalnie 17 zapytań na forecast).
- Niezależna append-only tabela `step17_frozen_challengers` w izolowanej 8-ligowej bazie M0. Powiązanie z oryginalną niezmienną prognozą M0 przez `source_m0_forecast_sha256`. Jedno `ELO_ONLY` i jedno `CATBOOST_NO_XG` na każdy nowy parent M0; hard stop jeśli choć jedna para niepełna. `UPDATE` i `DELETE` trigger zablokowane. Id, data, wersja i SHA modelu/cech/źródła zapisane. Nie zmieniono wcześniejszych `forecasts`, SHA modelu M0 ani jego kalibratora.
- Operacja na kopii staging SQLite oznacza, że niekompletne wyniki **nie są** utrwalane; oryginalne archiwum M0 pozostaje, kiedy nowy kod zawiedzie. Nie odtwarzamy challengerów retrospektywnie po zakończeniu lub rozpoczęciu meczu.

## Protokół niezbędnego odbioru

1. Testy offline i prawdziwy model CBM: SHA binarki, 85 nazw cech, etykiety 1/X/2, dodatnie P, zgodność daty i `feature_sha256`, scenariusze 64 spotkań → 128 challengerów, brak duplikatów, zakaz nadpisania starych rekordów. `tests/test_step17_forward_challengers.py` na oryginalnym binarnym modelu; GitHub Actions CI musi przejść.
2. Pierwsze rzeczywiste nowe wywołanie `mode=forecast` po wdrożeniu powinno utworzyć `step17_challenger_research.new_challengers = 2 × new_forecasts`. Jeśli `new_forecasts=0`, jest to **0 prawdziwych nowych challengerów**, nie 2×73. Dowód: nowy GitHub Actions log, snapshot SQLite/sha i serwerowy czas uploadu archiwum przed kickoff.
3. Dotychczasowy niezależny audyt prognoz M0 i protokół rozliczeń 100+50 nie są modyfikowane. Oddzielny formalny GATE17 wymaga **przyszłych rozliczonych i poświadczonych** prognoz wszystkich odpowiednich silników na identycznych meczach, etykietach i horyzontach.
4. Wersja CatBoost z xG i ensemble pozostają **NIEURUCHOMIONE**, dopóki nie ma certyfikowanych xG i przedmeczowych zamrożonych składników, a wagi ensemble nie zostaną ustalone poza chronionymi walidacjami. Do uczciwego porównania służy `src/kb3_step17_engine_comparison.py`; jego metryki NIE są jeszcze bieżącą oceną challengerów.

## Ryzyka / ograniczenia

- Train 720 to badanie historyczne na Premier League, z rekonstrukcjami `B_RECONSTRUCTED` zamiast udowodnionych dawnych natywnych timestampów PitchAPI. Transfer do pozostałych 8 lig jest eksperymentalny.
- Sama nazwa `ELO_ONLY` nie oznacza statystycznie wytrenowanego ani zweryfikowanego samodzielnego estymatora rozkładu remisu; reguła z TRAIN jest jawnym punktem porównawczym, wymagającym oceny.
- Stałe zapisanie przed meczem to warunek konieczny, ale dla formalnego GATE17 potrzebny będzie dodatkowy audyt binarnych danych `step17_frozen_challengers` we wcześniejszym serwerowo opatrzonym znacznikiem artefakcie GitHub. Bez takiego audytu liczymy je jako **research shadow pending external proof**. M0 ma osobny dowód 73/73, którego nie wolno przenosić domyślnie na dopiero utworzone challengery.
- Nie są pobierane nowe kursy lub dane xG, nie ma zakupu abonamentu. Premier League TEST 2026/27 nienaruszona. Nie awansowano żadnego modelu do Championa.

**Status:** Krok 17 **W REALIZACJI**, uruchomiono techniczne równoległe prognozowanie; GATE17 **PENDING**, krok 16 nadal **PENDING**, ukończonych formalnie **15/29**.
