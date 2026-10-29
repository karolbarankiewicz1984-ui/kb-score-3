# KB Score 3.0 — realny eksperyment CatBoost M1-R BASE, TRAIN 720, VALIDATION 374

**Data:** 2026-10-29. **Status:** realnie wytrenowany i oceniony **odrębny wariant badawczy**. To NIE jest oryginalny CatBoost M1; formalny **GATE14=PENDING** pozostaje bez zmian. [Powtarzalny kod eksperymentu](../scripts/step14_m1r_train_real_catboost_720_evaluate_374.py), [weryfikacja CI #40908406895](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40908406895).

## Twarde wyniki pierwszej walidacji

Z oryginalnego 1140-meczowego archiwum Premier League, [przeliczonego regułą 48h](STEP14_M1R_RELAXED_REAL_1140_720_TRAIN_374_VALIDATION_2026-10-29.md), rzeczywiście wzięto **720 wcześniej zakwalifikowanych TRAIN** (2023/24 + 2024/25) oraz dokładnie **374 VALIDATION** (2025/26). Te same identyfikatory, ten sam zestaw meczów i pojedyncza, niezależna ocena.

| Metryka | Nowy CatBoost M1-R BASE | M0 Elo + Poisson dopasowany na tym samym TRAIN 720 | Dodatkowy kontekst: wcześniejszy zamrożony M0 train 760 |
| --- | ---: | ---: | ---: |
| Multiclass log loss (mniej=lepiej) | **1.04835205** | **1.03510770** | 1.03514033 |
| Brier multiklasa, suma błędów 1/X/2 (mniej=lepiej) | **0.63171117** | **0.62029851** | 0.62034137 |
| ECE (5 binów pewności najczęstszej klasy, mniej=lepiej) | **0.05188980** | **0.02359672** | 0.01895464 |
| Accuracy top-1 (więcej=lepiej) | **0.46256684** | **0.50000000** | 0.49465241 |

Oryginalny M0 **wygrywa pod wszystkimi czterema miarami**. CatBoost ma o **0.01324435 większy log loss** i o **0.01141266 większy Brier sum3** względem uczciwego M0 z dopasowaniem na tych samych 720 danych. Wynik NIE uzasadnia zastąpienia M0.

**Jednostka Brier:** `Brier_sum3 = ((p1-y1)^2 + (pX-yX)^2 + (p2-y2)^2)` uśrednione po 374 meczach. Raport zawiera też `Brier_mean3 = Brier_sum3 / 3`. Nie należy porównywać tych dwóch wariantów bez podania skali.

## Jak zabezpieczono procedurę

1. TRAIN z dokładnie 720 zakwalifikowanych oryginalnych spotkań oraz 374 meczów VALIDATION; **nie użyto TEST 2026/27**. To wciąż **rekonstrukcja historyczna 48h**, nie oryginalny pełny dowód `published_at` sprzed kilku lat.
2. CatBoost `MultiClass`: 400 iteracji, depth 4, learning rate 0.035, L2=8, seed 20261029, nan_mode=Min. Stały zestaw hiperparametrów przed ewaluacją; **bez early stopping / eval_set na VALIDATION**.
3. Wybór aktywnych kolumn wyłącznie na 720 TRAIN: ze schematu 121 liczb i 38 flag usunięto stałe kolumny, niepoprawne/mieszane źródłowo xG i wszystkie alternatywne xG FPL. Braki liczb mają jawne NaN, bez podszywania się pod rzeczywiste xG=0.
4. Etykiety wyników 90 minut czytano z oryginalnych trzech sezonów PitchAPI **oddzielnie od 121/38 cech**. Do treningu CatBoost i M0 trafiały **wyłącznie wyniki TRAIN**; dla VALIDATION generowano prognozy przed oceną rzeczywistych etykiet. Prognozy i parametry zamrożono.
5. Uczciwy główny comparator M0: Elo na dokładnie tych samych zamrożonych snapshotach M1-R i Poisson dopasowany **wyłącznie na tych samych 720 TRAIN** metodą istniejącego `_train_poisson`. Wcześniejszy model M0 dopasowany do 760 TRAIN podano osobno jako **kontekst**, z zastrzeżeniem różnicy oryginalnego przeliczenia Elo.
6. Metryki Brier, log loss, ECE, accuracy są przeliczone niezależnie i krzyżowo sprawdzone z istniejącym `src/kb3_step13_retrospective._eval`. Raport zawiera **5 przedziałów kalibracyjnych pewności zwycięskiej klasy oraz dla każdej z 1/X/2** (średnia zadeklarowana szansa vs częstość rzeczywista); to kalibracja *diagnostyczna*, **bez trenowania Platt/Isotonic na VALIDATION**.
7. Brak jakichkolwiek wyników końcowych w zapisywanym pliku 374 prognoz; do audytu pozostają jedynie metryki agregowane, liczby klas, SHA modelu i predykcji. Model .cbm zapisany w izolowanym `models/research/`, nie jest podpinany do uruchomionych prognoz i nie aktualizuje M0.

## Materiały dowodowe (po uruchomieniu workflow `main`)

- [Rzeczywisty raport metryk, 3 modele, parametry i bins 1/X/2](../data/audits/STEP14_M1R_BASE_CATBOOST_720_374_REAL_METRICS_2026-10-29.json).
- [374 zamrożone prognozy prawdopodobieństw 1/X/2 (bez wyników)](../data/audits/STEP14_M1R_BASE_CATBOOST_374_FROZEN_PROBS_2026-10-29.jsonl.gz).
- [Wytrenowany, odrębny plik CatBoost M1-R BASE](../models/research/M1_R_BASE_CATBOOST_720_TRAIN_2026-10-29.cbm).
- [Skrypt, identyczne obliczenia M0 i własne mierniki](../scripts/step14_m1r_train_real_catboost_720_evaluate_374.py) i [testy](../tests/test_step14_m1r_train_catboost_720_eval_374.py).

## Decyzja i dalsze eksperymenty

- **Nie promować M1-R BASE do produkcji.** Oryginalny M0 wygrywa uczciwe porównanie log loss, Brier, ECE i top1; nadal zachować oba modele do audytu.
- Można później badać cechy xG po źródłowym uzgodnieniu definicji i reguły 48h, stabilność modelu w kolejnych przedziałach czasowych, nadmierne dopasowanie, sezonowy drift, alternative feature subsets, a także trening tylko na wcześniejszej części TRAIN z walidacją na jego późniejszym fragmencie. **Nie stroić hiperparametrów na chronionym TEST.** Dalsze testy na tej samej VALIDATION po obejrzeniu wyników wymagają jawnego oznaczenia eksploracyjnego / ryzyka wielokrotnego testowania.
- Ten dokument i pełne artefakty zostają w repozytorium; oryginalny **GATE14=PENDING**, a 2026/27 TEST, M0 i stary CatBoost M1 bez zmian.
