# KB Score 3.0 — Krok 15: ML gole kontra Poisson M0 — realne 374

**29 października 2026 | DO ODBIORU / GATE15 PENDING | 14/29.** Niezależny eksperyment badawczy. **POISSON M0 WYGRYWA**, ale oba silniki są matematycznie spójne.

## Metoda porównania

- Dokładnie **720 TRAIN** z dwóch starszych sezonów, następnie **374 VALIDATION** Premier League 2025/26, wyłączone 46 cold-start z poprzedniego kontraktu. Na obu modelach te same 374 ID, 90 minut i źródła.
- M0: istniejący Elo + Poisson z intensywnościami dopasowanymi wyłącznie na 720 TRAIN.
- ML: dwa odrębne modele CatBoostRegressor z funkcją celu Poisson dla liczby goli gospodarzy/gości. **85 aktywnych cech** wybranych tylko na TRAIN, bez xG, żadnego użycia kursów. Stałe wcześniej hiperparametry: 350 drzew, depth 4, learning_rate 0.035, L2 8, seedy 20261029 i 20261030. Bez walidacyjnego early stopping, parametry niezmieniane po ujawnieniu wyników.
- Zarówno M0, jak i ML generują prawdopodobieństwa z **jednego wspólnego niezależnego dwuwymiarowego rozkładu goli Poissona**. ML uczy samą intensywność goli, nie każdego rynku osobno.
- Najpierw zamrożono 374 pary prognoz, **bez zapisanych etykiet**. Dopiero potem policzono wyniki; nie trenowano na VALIDATION.
- 22 kontrakty binarne: 6 O/U 1,5–3,5, 2 BTTS i 14 kategorii goli drużyn. Główne porównanie obejmuje **18 unikalnych** zdarzeń, eliminując podwójne liczenie par Over/Under i BTTS TAK/NIE.
- Ocena Brier i log loss oraz ECE 5-bin, paired cluster bootstrap 1000 replikacji z **36 tygodniowymi blokami** (stały seed, dla tych samych meczów); przy pojedynczych rynkach CI często obejmuje zero.
- **Chroniony TEST Premier League 2026/27 nietknięty**. Dane historyczne to rekonstrukcja z opóźnieniem 48h, **nie certyfikowany autentyczny historyczny native PIT**. Ten eksperyment nie dowodzi dokładnej jakości przyszłych prognoz na żywo.
- Bez nowych zakupów API, żadnej kalibracji ani promocji modelu. Każdy dalszy wariant ML należy badać na nowej próbie forward zamiast wielokrotnie stroić na tych samych 374.

## Wynik podstawowy: średnia z 18 unikalnych rynków

| Miara (niżej lepiej) | Poisson M0 | CatBoost ML | ML minus M0 |
|---|---:|---:|---:|
| Brier | 0,18746462 | 0,19316377 | +0,00569914 |
| Log loss | 0,55666742 | 0,57275732 | +0,01608989 |

95% orientacyjny paired bootstrap: ΔBrier = **0,0005706 do 0,0109684**, Δlogloss = **0,0032895 do 0,0294657**. Dodatnie różnice oznaczają przewagę M0. Brak automatycznych wniosków o istotności wszystkich pojedynczych rynków ani gwarancji na następny sezon.

## Wszystkie 22 rynki, te same 374 spotkania

| Rynek | N | Brier M0 | Brier ML | Log loss M0 | Log loss ML | Lepszy |
|---|---:|---:|---:|---:|---:|---|
| Over 1,5 | 374 | 0,16553 | 0,18002 | 0,51363 | 0,54937 | M0 |
| Under 1,5 | 374 | 0,16553 | 0,18002 | 0,51363 | 0,54937 | M0 |
| Over 2,5 | 374 | 0,25039 | 0,26094 | 0,69415 | 0,71630 | M0 |
| Under 2,5 | 374 | 0,25039 | 0,26094 | 0,69415 | 0,71630 | M0 |
| Over 3,5 | 374 | 0,21385 | 0,21502 | 0,61970 | 0,63023 | M0 |
| Under 3,5 | 374 | 0,21385 | 0,21502 | 0,61970 | 0,63023 | M0 |
| BTTS TAK | 374 | 0,24706 | 0,25634 | 0,68737 | 0,70612 | M0 |
| BTTS NIE | 374 | 0,24706 | 0,25634 | 0,68737 | 0,70612 | M0 |
| Gospodarze 1+ | 374 | 0,16884 | 0,17795 | 0,51495 | 0,53900 | M0 |
| Gospodarze 2+ | 374 | 0,24074 | 0,25983 | 0,67454 | 0,72002 | M0 |
| Gospodarze 3+ | 374 | 0,16232 | 0,16913 | 0,50145 | 0,53187 | M0 |
| Gospodarze dokładnie 0 | 374 | 0,16884 | 0,17795 | 0,51495 | 0,53900 | M0 |
| Gospodarze dokładnie 1 | 374 | 0,20821 | 0,20859 | 0,60750 | 0,60768 | M0 |
| Gospodarze dokładnie 2 | 374 | 0,19724 | 0,20084 | 0,58370 | 0,59650 | M0 |
| Gospodarze dokładnie 3 | 374 | 0,13650 | 0,14119 | 0,44167 | 0,46741 | M0 |
| Goście 1+ | 374 | 0,19431 | 0,19556 | 0,57444 | 0,57717 | M0 |
| Goście 2+ | 374 | 0,22376 | 0,23043 | 0,63926 | 0,65485 | M0 |
| Goście 3+ | 374 | 0,11105 | 0,11332 | 0,37958 | 0,38828 | M0 |
| Goście dokładnie 0 | 374 | 0,19431 | 0,19556 | 0,57444 | 0,57717 | M0 |
| Goście dokładnie 1 | 374 | 0,23673 | 0,23778 | 0,66679 | 0,66932 | M0 |
| Goście dokładnie 2 | 374 | 0,17168 | 0,17316 | 0,52654 | 0,53146 | M0 |
| Goście dokładnie 3 | 374 | 0,08299 | 0,08335 | 0,30533 | 0,30790 | M0 |

**Na 22/22 rynków M0 ma niższy Brier i log loss.** Niezależny audyt wyniku PASS (132 oddzielne odtworzone metryki i 748 kontrolowanych prognoz; w każdej te same reguły i brak sprzeczności).

## Spójność matematyczna — niezależny audyt PASS

W obu modelach dla **748 prognoz (374 × 2)** potwierdzono:
1. 1/X/2 sumuje się do 1, brak nielegalnych prawdopodobieństw poza [0,1].
2. Over 3,5 ≤ Over 2,5 ≤ Over 1,5; Under = 1 − Over.
3. BTTS NIE = 1 − BTTS TAK; BTTS TAK ≤ Over 1,5 i ≤ gol 1+ każdej drużyny.
4. Team totals 1+/2+/3+ są malejące i zgodne z dokładnie 0/1/2/3 bramkami.
5. Wyniki dokładne pochodzą z tego samego rozkładu regularnych 90 minut (bez dogrywki), top 5 unikatowych i malejąco uporządkowanych.
6. 2× CatBoost .cbm i 374 zamrożone prognozy mają zweryfikowane SHA i odtwarzalną implementację. **0 prognoz ML wymagających przycięcia intensywności**.

Spójność nie jest gwarancją kalibracji: każdy wariant Poissona może być w pełni spójny, a jednak słabiej dopasowany do rozgrywek.

## Trwale zachowane dowody (prywatne repo)

- [Pełne wyniki wszystkich 22 rynków, ECE i bootstrap](../data/audits/STEP15_ML_VS_M0_374_FULL_REPORT_20261029.json).
- [Niezależny audyt wyników, SHA i spójności](../data/audits/STEP15_INDEPENDENT_SECOND_SCORE_AUDIT_20261029.json).
- [Zamrożone 374 par prognoz bez etykiet](../data/forecasts/STEP15_374_PAIR_GOAL_PROBABILITIES_NO_LABELS_20261029.jsonl.gz).
- [Model HOME](../models/research/STEP15_CATBOOST_GOALS_HOME_720_20261029.cbm) i [model AWAY](../models/research/STEP15_CATBOOST_GOALS_AWAY_720_20261029.cbm) — tylko research.
- [Kod treningu i uczciwego porównania](../scripts/step15_goal_ml_catboost_720_374.py), [drugi niezależny audyt](../scripts/step15_independent_market_audit.py).
- [CI eksperymentu SUCCESS #40922276524](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40922276524), [audyt SUCCESS #40922881340](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40922881340), [roboczy PR #103](https://github.com/karolbarankiewicz1984-ui/kb-score-3/pull/103). Gałąź main niezmieniona.

## Decyzja

**Nie promować nowego CatBoost do produkcji, zachować M0 jako benchmark. Krok 15: DO ODBIORU, GATE15 PENDING, 14/29** do jawnego formalnego zamknięcia. Późniejszy krok 16: kalibracja na rzeczywistych zamrożonych próbach 100+50 w odizolowanym forward. Zmiany i status w PLAN.md oraz ZMIANY.md.
