# KB Score 3.0 — krok 03: P1-01 / P1-02, kontrola fail-closed

**Data:** 2026-11-04. **Status:** PARTIAL IMPLEMENTATION / AWAIT CI; step 03 is **NOT** fully closed.

P1-02: stare ścieżki kalibracji trzech lig nie mają niezależnego dowodu GitHub host first-publication z dokładnym hashem danych i czasem przed kickoff-90min. Dotychczas 100 fikcyjnych albo niepoświadczonych rozliczeń mogło uruchomić fit. Nowy kod zachowuje raportowanie Brier/log loss, ale **blokuje fit i HOLDOUT review nawet przy 100+**. Wcześniejsze zapisane kandydaty nie są usuwane ani akceptowane. Formalny ośmioligowy M0 posiada odrębny rygorystyczny system host proof i nie jest modyfikowany.

P1-01: w istniejącym CatBoost M1-R szkolenie rekonstruowano z innym time-policy (kickoff + 48h poprzedniego spotkania) niż żywe źródła (capture cutoff + 3h). GATE18 odmawia teraz nawet badawczego „ready” dla tej rodziny, niezależnie od CI95 na rozłącznych okresach. **To blokada promocji, a nie naprawa zgodności definicji cech**. Rzeczywistą zgodność trzeba zbudować w osobnej wersji train/forward i potwierdzić audytem na tych samych meczach oraz timestamptach.

Zakres: bez API, SQLite binary changes, historycznego reforecast, zmian parametrów M0 i dostępu do protected ENG TEST. Weryfikacja: pełne CI PR i nowy zestaw testów P1; oryginalny `#143` pozostaje NO-GO, dopóki jego wszystkie wątki i konsumenci nie zostaną odebrane. Wprowadzone zmiany są odwracalne na poziomie kodu.
