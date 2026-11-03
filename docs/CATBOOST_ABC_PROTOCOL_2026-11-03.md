# CODEX-02 — zamrożony protokół badawczy A/B/C

Protokół zapisany przed pierwszym dopasowaniem tego eksperymentu. Baza main
`eabab06139b185d34450d314989783bdc980b088`. To osobne badanie od PR #126/#141
i od nieukończonego odbioru źródeł w PR #143. Bez awansu modelu i GATE17.

- Populacja: zakończone mecze ESP/ITA/GER/FRA/NED/BEL/TUR/POL z istniejącego
  indeksu. ENG (w tym zastrzeżone VALIDATION i TEST) oraz UCL wykluczone.
  Wymagane pięć rzeczywistych poprzedników obu stron; brak statystyk nie usuwa
  poprzednika. Nie dobieramy starszego dostępnego meczu zamiast brakującego.
- Dane wyłącznie read-only. Cache nie jest dowodem: cechy liczone ponownie.
  Każda statystyka jest średnią wyłącznie kompletnego okna N/N albo NULL.
  xG dodatkowo wymaga zgodności przechowanych shots counts z All total_shots,
  zgodnych natywnych stron i xG. Rzeczywiste powtórzenie total_shots w grupach
  Shots/Top stats jest dopuszczone tylko przy zgodności obu niezależnie
  przechowanych wartości. Nie odtwarzamy zaszyfrowanych raw ani starego PIT.
- Wszystkie trzy modele uczą się na identycznych meczach. A: Elo i forma
  bramkowa 5/10/15, odpoczynek i kompletność. B: A + dokładne xG5/xGA5.
  C: B + dostępne xG10/15 i nazwane statystyki strzałów, rożnych, kartek,
  fauli itd. Braki B/C są NaN; raport pokazuje także wspólną kompletną xG5
  podpróbę. Wynik szerokiej próby z brakami nie dowodzi sam w sobie korzyści xG.
- Jedna definicja cech do treningu i prognozy: cutoff kickoff−90 min,
  wynik poprzednika dopuszczany od kickoff+3h. To modelowana rekonstrukcja,
  a nie historyczny dowód publikacji. Zachowujemy rzeczywiste observed_at
  i SHA źródeł w metadanych; nie dodajemy ich jako zmiennych modelu.
- Parametry wspólne A/B/C z uprzedniego pilota: CatBoost 1.2.8, 175 drzew,
  depth=3, learning_rate=.035, l2=8, MultiClass, seed=20261103, 2 wątki.
  Bez search, early stopping, eval_set i strojenia na VALIDATION.
  Zmienne/niepuste kolumny wybierane wyłącznie w każdej części TRAIN.
- Walk-forward wyłącznie wewnątrz badawczego TRAIN: wcześniejsze dane →
  [2025-07-01, 2025-11-01), następnie → [2025-11-01, 2026-02-01),
  następnie → [2026-02-01, 2026-05-01). Minimum 80 TRAIN i 25 ocen.
  Wszystkie TRAIN muszą być rozliczalne przed pierwszym cutoff ocen.
- Zablokowana z góry późniejsza walidacja badawcza:
  [2026-05-01, 2026-11-03). Nie jest nietknięta: częściowo pokrywa znane wyniki
  #141. Raport jawnie nazywa ją ponownie wykorzystaną retrospekcją;
  nie wybieramy na jej podstawie parametrów, cech ani zwycięzcy produkcyjnego.
- M0: niezmienione parametry 720-TRAIN i istniejąca matematyka Elo/Poisson.
  Oceny dopiero od 2025-07-01, po obu sezonach jego treningu. Jest to
  M0_FIXED720_REPLAY, oddzielnie od oryginalnych zamrożonych forward forecastów.
  Te ostatnie mogą być porównane tylko z autentycznymi prognozami challengerów
  sprzed tego samego meczu/cutoff, nigdy z dopisanym później replay.
- Brier sum3, log loss, accuracy, ECE5, reliability per klasa i liga,
  paired bootstrap całych ISO tygodni (1200 replikacji, stały seed).
  Wniosek o poprawie wymaga obu strat lepszych, CI95 w całości <0,
  minimum 100 wspólnych ocen i 8 tygodni. Pokazujemy brakującą liczbę meczów
  i tygodni. Dla korzyści xG obowiązuje też ta sama bramka na pełnej xG5 próbie.
- Rekonstrukcja i oryginalne freeze są rozdzielone. Żadnej automatycznej
  kalibracji, zmiany M0, pobrania API, backfillu i publikacji modelu produkcyjnego.
