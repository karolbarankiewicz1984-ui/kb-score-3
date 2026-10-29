# KB Score 3.0 — Krok 15: rozpoczęcie (29.10.2026)

**Oficjalny stan: W REALIZACJI; postęp nadal 14/29.** Krok 14 zaliczono według zatwierdzonego wariantu B. Oryginalna certyfikacja historycznego PIT pozostaje oddzielnie PENDING. Chroniony TEST 2026/27 pozostaje zamknięty.

## Pierwotny zakres z PLAN.md

Modele goli: Over/Under 1,5, 2,5 i 3,5; BTTS TAK/NIE; gole gospodarzy/gości; porównanie rozkładu bazowego z ewentualnym kandydatem ML. Test matematyki 90 minut i spójności. Wymagany działający kod, testy i raport na porównywalnych spotkaniach.

## Wykonany pierwszy moduł M2: adapter do M0 Poisson

- Kod: [src/kb3_step15_goal_markets.py](../src/kb3_step15_goal_markets.py).
- Testy: [tests/test_step15_goal_markets.py](../tests/test_step15_goal_markets.py).
- CI: [kb3-step15-goal-markets.yml](../.github/workflows/kb3-step15-goal-markets.yml).
- Wszystkie rynki pochodzą z **jednego wspólnego rozkładu wyników 90-minutowych**. 1X2, Over i BTTS są kontrolowane numerycznie względem niezmienionego M0 Step13.
- Nowość: Under wszystkich trzech linii, BTTS NIE, dokładnie 0/1/2/3 goli i przynajmniej 1/2/3 gole drużyny (home/away), pięć najbardziej prawdopodobnych wyników dokładnych.
- Sprawdzane własności: Over 3,5 <= Over 2,5 <= Over 1,5; dopełnienia O/U i BTTS, monotoniczność team totals, sumy 1X2=1, prawdopodobieństwa z [0,1], brak dogrywki.
- Testy analityczne Poissona, wartości skrajne, deterministyczność, porównania z oryginalnym M0 oraz testy negatywne manipulacji, NaN, kursów i dogrywki.
- **Nie trenowano** odrębnego ML goli, nie sprawdzano jakości empirycznej na 374 walidacyjnych meczach, nie kalibrowano modelu i nie czytano TEST 2026/27.

## Do ukończenia oryginalnego GATE15

1. Zamrozić prawdopodobieństwa wszystkich rynków na tych samych 374 historycznych meczach VALIDATION co M1-R, używając parametrów M0 wyznaczonych tylko na wcześniejszych 720 TRAIN. Nie używać do fit etykiet VALIDATION.
2. Oddzielnie pobrać rzeczywiste 90-minutowe gole do oceny; policzyć Brier i log loss dla O/U, BTTS i team totals; podać dokładne N i coverage.
3. Porównać M0 ze specjalizowanym wariantem ML wyłącznie gdy realnie istnieje porównywalny zestaw danych; bez automatycznego założenia przewagi ML.
4. Niezależny audyt testów własności + wyników empirycznych + identyfikatorów wersji. Dopiero potem formalne GATE15 PASS w PLAN/ZMIANY.

## Kontrakt bezpieczeństwa

Wyłącznie matematyczny adapter badawczy; niepublikowany i nieskalibrowany, nie jest ofertą do obstawiania. Step13 M0, M1-R CatBoost oraz ich archiwa nie są zmienione. Nie wolno odblokować TEST ani awansować nowych modeli. Przyszła zasada kalibracji 100+50 pozostaje bez zmian. Bez nowych kosztów i zakupów API.

## Wykonana rzeczywista walidacja — 374 VALIDATION, 29.10.2026

**PASS dla technicznego przeliczenia 22 rynków z rzeczywistych wyników, ale GATE15 wciąż PENDING.** Rzeczywisty [GitHub Actions #40920143414](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40920143414) zakończył się SUCCESS: 720 TRAIN, 374 VALIDATION, niezmienny bazowy benchmark M0 1X2, wszystkie 22 kontrakty na tych samych 374 meczach (każdy N=374), brak użycia 2026/27 TEST, brak walidacyjnych etykiet w fit, brak zmiany produkcyjnej. Kod: [skrypt ewaluacji](../scripts/step15_real_validation_374_goal_markets.py) + [testy](../tests/test_step15_real_validation_374_goal_markets.py).

Wyniki bez kalibracji (mniej = lepiej):

| Rynek | N | Brier binary | Log loss binary | ECE 5-bin |
|---|---:|---:|---:|---:|
| Over 2,5 | 374 | 0.25038978 | 0.69415417 | 0.05267028 |
| BTTS TAK | 374 | 0.24706266 | 0.68736515 | 0.04242771 |

Pozostałe 20 rynków ma wyniki w **pełnym 22-rynkowym raporcie** (artifact ID 12918051653, nazwa KB3_STEP15_REAL_374_GOAL_MARKET_METRICS_RESEARCH; 90-dniowa retencja GitHub Actions). Trwale zapisany [dowód metryk wybranych i identyfikator artefaktu](../data/audits/STEP15_REAL_374_VERIFIED_SELECTED_GOAL_METRICS_2026-10-29.json). Źródła i algorytm są wersjonowane, a pełne obliczenia odtwarzalne.

**Interpretacja:** Brier około 0,25 dla O2,5 jest bliski wartości z prognozy 50/50; nie jest to dowód dobrej przewagi nad innymi metodami. M0 nie został tu porównany z niezależnym ML goli ani skalibrowany (krok 16). To retrospektywny RESEARCH z umownym 48h po meczach, **nie** certyfikat prawdziwego historycznego PIT danych providerów i nie prognozy do obstawiania.

**Koszty i re-run:** wykorzystano istniejące połączenie PitchAPI, bez nowego zakupu. Po pierwszym pozytywnym przebiegu workflow ponownej realnej ewaluacji ograniczono do ręcznego uruchomienia, żeby nie zużywać powtarzalnych zapytań API na każde zapisanie dokumentu. Status formalny: **14/29; krok 15 W REALIZACJI** do porównania z ewentualnym ML i niezależnego audytu kompletnego GATE15.
