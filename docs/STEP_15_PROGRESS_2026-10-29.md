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
