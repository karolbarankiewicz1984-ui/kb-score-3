# CODEX-02 — rzeczywisty CatBoost A/B/C i wspólna próba z M0

**Wynik odbioru: PARTIAL.** Proces badawczy wykonany i zweryfikowany; brak
potwierdzonej poprawy na późniejszej walidacji. Kod można oceniać jako osobne
narzędzie badawcze. Odbiór źródeł CODEX-01 / PR #143 pozostaje warunkiem
integracji. Awans modelu: **NO-GO**, GATE17 **PENDING**. Produkcyjny M0,
kalibracja, stare prognozy i chronione dane pozostają bez zmian.

## Co już istniało

| Rozwiązanie | Wykorzystanie / brak |
| --- | --- |
| Main `eabab06139b185d34450d314989783bdc980b088` | Istnieją Elo/forma, natywne indeksy poprzedników, `rolling_window`, stały M0-720, scoring, bootstrap tygodni i weryfikacja oryginalnych forward receiptów. |
| [Draft PR #126](https://github.com/karolbarankiewicz1984-ui/kb-score-3/pull/126), head `70e520465fdbcd420641972f14c438856238fbc6` | Ma TRAIN-only walk-forward na 720 przykładach i wybór zmiennych w TRAIN. Trzy profile parametrów, potrzeba pobrania etykiet przez API, M0 dopasowywany w foldach. Brak xG B/C i dostępnego raportu rzeczywistego wykonania. Nie przeniesiono starego patcha w całości. |
| [M1-R 720/374](STEP14_M1R_REAL_CATBOOST_720_TRAIN_374_VALIDATION_VS_M0_2026-10-29.md) | Gotowy rzeczywisty CatBoost bez xG i metryki/reliability. M0 wygrywał wtedy Brier 0.620299 vs 0.631711. Inna angielska próba, 48h dojrzałości wyników, inne cechy i parametry. Nie uruchamiano ponownie jej VALIDATION ani nie porównywano tych liczb bezpośrednio z nowym eksperymentem. |
| [Rzeczywisty PR #141](https://github.com/karolbarankiewicz1984-ui/kb-score-3/pull/141) | Pilot 102 TRAIN / 44 VAL, bez Elo i walk-forward, dwie ligi. Bez xG Brier 0.638039 / log loss 1.057706; xG5 0.638483 / 1.059655. Brak dowodu korzyści xG i brak wspólnego M0. Wykorzystano mechanikę rzeczywistych poprzedników i z góry stały profil 175/depth3/.035/L2=8. |
| Istniejące forward CatBoost no-xG / Elo-only | Oddzielne wersje i receipt'y, nie są nowymi wariantami A/B/C. Nie podmieniono ich modeli ani nie przypisano im dzisiejszych prognoz retrospektywnych. |

Nowe elementy: wspólny kontrakt cech TRAIN/inference A/B/C, pełny indeks
poprzedników zamiast cache, read-only kontrola źródeł i kwarantanna w pamięci,
stałe foldy, trzy rzeczywiste modele na każdym foldzie, wspólne mecze z
`M0_FIXED720_REPLAY`, niezależny weryfikator wyników i ścisły most do przyszłych
oryginalnych zamrożonych prognoz.

## Dane i brakujące wartości

- Snapshot zawiera 8621 wyników w indeksie i 816 szczegółowych obserwacji.
  Po wykluczeniu UCL pozostaje 8064 wyników i 811 obserwacji w ośmiu ligach;
  wszystkie ENG są zabronione. Brak pięciu rzeczywistych poprzedników obu
  drużyn wyklucza 617 celów. Dostępne 7447 przykładów to **nie** 7447 pełnych xG.
- 682 pary xG są spójne z przechowanymi strzałami i statystykami; 56 konfliktów
  liczby strzałów trafia do kwarantanny w pamięci; 73 inne źródła nie mają
  zweryfikowanego xG. Oryginalne rekordy nie zostały poprawione ani nadpisane.
- PitchAPI powtarza `total_shots` w grupach `Shots` oraz `Top stats`. Czytnik
  dopuszcza tę konkretną reprezentację wyłącznie przy zgodnych wartościach obu
  grup i niezależnie przechowanych counts. Zero wymaga jawnej wartości, brak
  pozostaje NULL. To osobna, badawcza polityka; nie scala konserwatywnego
  patcha źródłowego z PR #143 ani nie rozstrzyga wszystkich ustaleń R1–R5.
- Zweryfikowany overlay odzyskuje 140 **stron** żółtych kartek, nie 140 nowych
  spotkań. To późniejsza rekonstrukcja o zachowanym rzeczywistym czasie źródła.
- A: Elo, forma bramek/punktów/siły rywali 5/10/15, home/away, odpoczynek,
  liczności i flagi braków. B: dokładnie A + xG/xGA obu drużyn z last5.
  C: dokładnie B + xG10/15 i 17 statystyk na oknach 5/10/15: strzały, celne,
  niecelne, faule, rożne, żółte/czerwone kartki, spalone, podania, celne podania,
  przechwyty, wybicia, obrony bramkarza, duże okazje, strzały z pola i spoza pola karnego
  i kontakty w polu karnym rywala.
- Każda średnia dodatkowej statystyki wymaga N/N rzeczywistych poprzedników;
  inaczej NULL → natywne NaN. Nie zastępujemy brakującego meczu starszym ani
  braku zerem. Częściowe pokrycie jednej drużyny nie usuwa celu z szerokiej próby.
  Osobno raportowana jest próba z pełnym xG5 obu drużyn.

Źródło SQLite SHA256:
`bf95048fdff2dc098d0d3add55a0a3b5fadc45687f4a24703a03f9cbf87ed164`;
overlay:
`c6aa172b35680a985f9f60d6a4210914552ff45eafbf0656c12b7d99bc50f09d`.
Kontrole integralności, tożsamości meczów/stron, wyników, czasów i SHA przeszły.
**Nie odszyfrowano i nie uwierzytelniono ponownie raw receiptów.** Spójność
zarchiwizowanych projekcji nie jest certyfikacją źródłowego PIT.

## Chronologia i ochrona przed przeciekiem

[Protokół](CATBOOST_ABC_PROTOCOL_2026-11-03.md) zapisano przed pierwszym fit.
Stałe parametry są wspólne A/B/C; brak search, eval_set, early stopping,
kalibratora lub wyboru zwycięzcy na VALIDATION. Wyłącznie TRAIN decyduje,
które kolumny mają zmienność. Jedna funkcja tworzy cechy treningowe i prognostyczne,
bez czytania wyniku celu. Zera liczbowe nie są imputacją.

Cutoff celu = kickoff−90 min; wcześniejszy wynik jest dopuszczany dopiero od
kickoff+3h. Etykiety całego TRAIN muszą być dostępne przed najwcześniejszym
cutoff ocen; remisy godzin nie są rozdzielane. Nie użyto chronionego ENG TEST
2026/27 ani zastrzeżonego angielskiego VALIDATION. Aktualizacja formy podczas
oceny używa wyłącznie wcześniejszych rozliczalnych spotkań, bez ponownego fit
w obrębie danego okna.

Rzeczywiste historyczne `observed_at` i SHA pozostają w metadanych, poza
kolumnami modelu. Klasa danych zawsze
`HISTORICAL_RECONSTRUCTED_NOT_ORIGINAL_PIT`. Odczytane później źródło nie
staje się oryginalną cechą zamrożoną przed meczem. Testy odrzucają takie
przeklasyfikowanie. Rezerwa +3h jest założeniem rekonstrukcji, nie dowodem
rzeczywistej publikacji. Etap rozgrywek/play-off i korekty dostawcy nie mają
niezależnej historycznej certyfikacji w tym eksperymencie.

| Okno oceny (koniec wyłączny, UTC) | TRAIN | Ocena | Pełne xG5 TRAIN / ocena | Wybrane cechy A/B/C |
| --- | ---: | ---: | ---: | ---: |
| WF1: 2025-07-01 → 2025-11-01 | 4280 | 640 | 10 / 6 | 81 / 85 / 117 |
| WF2: 2025-11-01 → 2026-02-01 | 4920 | 746 | 16 / 5 | 81 / 85 / 187 |
| WF3: 2026-02-01 → 2026-05-01 | 5666 | 839 | 21 / 22 | 81 / 85 / 187 |
| Późniejsza walidacja badawcza: 2026-05-01 → 2026-11-03 | 6505 | 942 | 43 / 26 | 81 / 85 / 189 |

Foldy WF są wewnątrz badawczego TRAIN; późniejsza walidacja ma 19 tygodni ISO.
Ten okres częściowo pokrywa już znany PR #141: jest **ponownie wykorzystaną
retrospekcją**, a nie nietkniętą próbą potwierdzającą. Nie dobierano na niej
parametrów, terminów ani cech po zobaczeniu wyników.

## Co dokładnie oznacza M0 w tabelach

`M0_FIXED720_REPLAY` korzysta z niezmienionych parametrów istniejącego M0-720
i jego funkcji Elo/Poisson; SHA parametrów
`55310f0e1dd3842e6d876069ef21b1380901b3a6cc6884cf6ec6ea351a5812d1`.
Nie dopasowano go ponownie. Oceny zaczynają się po obu sezonach jego TRAIN.

Historyczny Elo został odtworzony na całym dostępnym wcześniejszym indeksie
danej ligi z istniejącą regułą retencji sezonowej. Live forward korzysta z
własnego, dwusezonowego inwentarza źródeł. Dlatego ten replay nie gwarantuje
identyczności z bajtami autentycznych dawnych prognoz M0. Tabele nie podają
wyniku produkcyjnego M0 ani porównania z jego oryginalnymi 74 rozliczeniami.

## Rzeczywiste wyniki na wspólnych meczach

Brier = średnia sumy trzech błędów kwadratowych 1/X/2; mniej lepiej.
Log loss i ECE5: mniej lepiej; accuracy: więcej lepiej.
Reliability pięciu przedziałów dla każdej klasy i per liga jest w pełnym JSON.

Walk-forward: 2225 różnych ocen poza TRAIN danego foldu:

| Model | Brier sum3 | Log loss | Accuracy | ECE5 |
| --- | ---: | ---: | ---: | ---: |
| M0_FIXED720_REPLAY | 0.607017 | 1.016882 | 50.74% | 0.033511 |
| A bez xG | 0.600798 | 1.005192 | 50.07% | 0.024814 |
| B + xG5 | 0.600858 | 1.005236 | 50.02% | 0.027233 |
| C rozszerzony | 0.600199 | 1.004221 | 50.07% | 0.033654 |

Bootstrap całych tygodni (1200 replikacji) daje ujemne CI obu strat A/B/C
względem replay M0 w tej części. Jest to sygnał z wcześniejszej części
badawczej, nie końcowy dowód poprawy ani powód do wyboru C.

Późniejsza walidacja: dokładnie te same **942 mecze** dla wszystkich modeli:

| Model | Brier sum3 | Log loss | Accuracy | ECE5 | Wniosek wobec M0 replay |
| --- | ---: | ---: | ---: | ---: | --- |
| M0_FIXED720_REPLAY | 0.596539 | 1.000187 | 52.44% | 0.065660 | Punkt odniesienia |
| A bez xG | 0.589255 | 0.990083 | 52.76% | 0.018749 | Brak potwierdzonej poprawy |
| B + xG5 | 0.590495 | 0.991630 | 52.55% | 0.019150 | Brak potwierdzonej poprawy |
| C rozszerzony | 0.591913 | 0.993788 | 52.44% | 0.018375 | Brak potwierdzonej poprawy |

| Różnica model − M0 replay | CI95 Brier | CI95 log loss |
| --- | --- | --- |
| A | [−0.014862, +0.001197] | [−0.022345, +0.004094] |
| B | [−0.013485, +0.002290] | [−0.020660, +0.005081] |
| C | [−0.012245, +0.003823] | [−0.019029, +0.007311] |

Wszystkie przedziały obejmują brak poprawy. ECE5 wygląda lepiej, ale jest
diagnostyką, bez osobnego dopasowania kalibratora i bez dowodu przewagi
prospektywnej. B i C są punktowo słabsze od A w obu stratach.

W pełnej xG5 podpróbie jest **26 meczów / 7 tygodni**. Brier A/B/C:
0.502488 / 0.504806 / 0.505299; log loss:
0.868215 / 0.872212 / 0.872327. Wynik korzyści xG jest **nierozstrzygający**:
do zadeklarowanego minimum 100/8 brakuje **74 meczów i jednego tygodnia**.
To minimum raportowe, nie obietnica wystarczającej mocy statystycznej.

## Rozkład według lig, późniejsza walidacja

W komórkach Brier / log loss; pozostałe metryki ligowe i reliability są w JSON.
Nie ogłaszamy zwycięzców na podstawie małych podgrup.

| Liga | N | M0 replay | A | B | C |
| --- | ---: | ---: | ---: | ---: | ---: |
| BEL | 114 | .57370 / .96827 | .56551 / .95413 | .56679 / .95624 | .56900 / .96016 |
| ESP | 145 | .58406 / .98553 | .57170 / .96946 | .57196 / .97004 | .57327 / .97149 |
| FRA | 100 | .61283 / 1.02119 | .61298 / 1.02239 | .61874 / 1.03103 | .61849 / 1.03035 |
| GER | 85 | .61119 / 1.01777 | .61426 / 1.02359 | .61475 / 1.02409 | .61856 / 1.02974 |
| ITA | 140 | .56370 / .95377 | .55157 / .94086 | .55141 / .94036 | .55294 / .94263 |
| NED | 119 | .61224 / 1.02384 | .61264 / 1.01995 | .60860 / 1.01301 | .61472 / 1.02166 |
| POL | 136 | .62643 / 1.04225 | .61298 / 1.02019 | .61394 / 1.02091 | .61214 / 1.01896 |
| TUR | 103 | .59852 / 1.00147 | .58944 / .99254 | .59664 / 1.00249 | .59564 / 1.00133 |

## Oryginalne zamrożone prognozy

Odczyt read-only bazy forward: 91 prognoz M0, 74 zweryfikowane rozliczenia.
Wspólne oryginalne pary z nowymi wersjami A/B/C: **0**. Każdemu wariantowi
brakuje **100 nowych prawdziwych par i 8 tygodni** do minimum porównania.
Nie da się dopisać challengerów po czasie do starych 74 meczów.

`compare_original_m0` przygotowuje porównanie wyłącznie na identycznych
natywnych meczach, drużynach i cutoff. Wymaga niezależnego weryfikatora
oryginalnych bajtów archiwum i serwerowego zegara; samodzielnie zadeklarowany
SHA/boolean nie jest dowodem. Odrzuca rekonstrukcje, późne źródła i trening,
spóźniony freeze, duplikaty i mieszanie wersji. Integracja z publikacją nowych
challengerów oraz rzeczywistym weryfikatorem archiwum pozostaje kolejną pracą.

## Weryfikacja i odtworzenie

- Rzeczywisty fit CatBoost 1.2.8: **12 modeli**, 3 warianty × 4 okna.
  3167 unikatowych ocen (2225 + 942), bez API i bez fit na VALIDATION.
- Pełna regresja: **1209/1209 PASS**, 0 failures/errors/skips na Pythonie
  **3.11.17 i 3.12.14**, w tym 29 nowych testów. Każde ID policzone raz;
  wcześniejsze zestawy częściowo nakładają się i nie są dodawane do tej sumy.
  Sieć, zapis chronionych źródeł i trening na rzeczywistych danych blokowane
  w testach; dopuszczone wyłącznie nazwane stare regresje syntetyczne.
  SQLite chronionych plików wymuszony na mode=ro również dla starych czytników.
- Niezależny skrypt ze standardowej biblioteki przeliczył Brier, log loss,
  accuracy i ECE z wszystkich 3167 prognoz, metryki per liga i agregację WF
  (zgodność 1e−12); sprawdził embargo oraz SHA **12 modeli**: PASS.
- Zachowany ślad prób nieudanych: pierwszy fit zatrzymał się przed pierwszym
  modelem przez błędny argument SDK `feature_names`; poprawiono na `Pool`
  i wykonano rzeczywisty smoke oraz cały fit. Zaostrzenie blokady regresji
  ujawniło trzy istniejące testy syntetyczne; dodano ich jawną listę. Późniejszy
  ujemny test małej próby miał błędne oczekiwanie dla foldu z <80 TRAIN;
  skorygowano oczekiwanie. Podane PASS dotyczą końcowego kodu.
- Brak migracji SQLite w tym PR. SHA źródeł przed/po bez zmian; brak diff
  `data/`, `models/`, `config/`. Bez zakupów, backfillu i nowych zapytań API.

Materiały w repo:
[pełny raport](audits/CATBOOST_ABC_FULL_RESULTS_2026-11-03.json.gz),
[czytelne podsumowanie](audits/CATBOOST_ABC_SUMMARY_2026-11-03.json),
[3167 prognoz](audits/CATBOOST_ABC_PREDICTIONS_2026-11-03.jsonl.gz).
Pełny JSON zawiera coverage każdej cechy, wybrane kolumny, parametry,
SHA modeli i wszystkie przedziały kalibracji. Osobny pakiet przekazany
właścicielowi zawiera również 12 rzeczywistych plików `.cbm` i logi regresji.

```bash
# Nowy katalog wyjściowy; fit jest jawny, domyślnie tylko preflight.
python -m scripts.step17_catboost_abc_research --fit \
  --out /tmp/abc-new/report.json \
  --predictions /tmp/abc-new/predictions.jsonl.gz --model-dir /tmp/abc-new/models
python scripts/verify_catboost_abc_results.py \
  --report /tmp/abc-new/report.json --predictions /tmp/abc-new/predictions.jsonl.gz \
  --models /tmp/abc-new/models
# Weryfikacja zapisanych wyników bez ponownego treningu:
python scripts/verify_catboost_abc_results.py \
  --report docs/audits/CATBOOST_ABC_FULL_RESULTS_2026-11-03.json.gz \
  --predictions docs/audits/CATBOOST_ABC_PREDICTIONS_2026-11-03.jsonl.gz
```

Pierwsze wykonanie przygotowało cechy oddzielnie, aby po korekcie wywołania SDK
nie powtarzać kosztownego odczytu; przed fit sprawdzono hash buildera,
wszystkie cechy i oba źródłowe SHA. Ten sam `experiment` trenował modele;
nie powstała alternatywna implementacja treningu. SHA przygotowanego zbioru:
`9d8a82ca96e46eb2f4d42a84d3bd5ea5c7c3dc477be653ff1eeacd80f01324ae`.
Automatyczny CI wykonuje regresję i niezależną kontrolę archiwalnych wyników.
Nowy rzeczywisty fit w Actions wymaga jawnego workflow_dispatch z
`run_research_fit=true`; nie ma harmonogramu ani publikacji do main.

## Co dalej przed decyzją o modelu

1. Odebrać źródła CODEX-01, wyjaśnić konflikty i semantykę okresów; zachować
   kwarantannę zamiast luzować kryteria lub zmieniać historyczne dowody.
2. Zwiększyć rzeczywiste kompletne xG5/10/15 w wielu ligach i okresach.
   Przygotować nowy protokół na przyszły, nieoglądany okres; ewentualny search
   wykonywać wyłącznie wewnątrz TRAIN z kolejnymi foldami.
3. Osobno zintegrować i zweryfikować oryginalny freeze A/B/C dla nowych meczów,
   bez autoawansu i bez dopisywania replay do dawnych prognoz.
4. Zebrać co najmniej 100 wspólnych oryginalnych rozliczeń / 8 tygodni na
   wariant, potem ocenić niepewność. To nie zastępuje oddzielnego GATE16
   FIT100 + nowych po fit HOLDOUT50 ani pełnego zakresu GATE17.

**Wniosek:** A/B/C uzyskały lepsze wartości punktowe od replay M0, ale żaden
nie wykazał potwierdzonej poprawy na późniejszej próbie. Nie wykazano korzyści
xG5 ani rozszerzenia C względem A. M0 pozostaje bez zmian.
