# KB Score 3.0 — Krok 14: karta rozpoczęcia (27.10.2026)

**Krok 13 zakończony jako techniczny baseline:** [protokół odbioru](STEP_13_FINAL_ACCEPTANCE_2026-10-27.md). **Krok 14 otwarty do prac planistycznych** zgodnie z niezmienioną mapą 29 etapów. To nie jest jeszcze zaliczenie kroku 14 ani wytrenowanie CatBoost.

## Pierwotny cel z PLAN.md

- Niezależny CatBoost M1 dla klas 1/X/2 wykorzystujący wyłącznie cechy dostępne przed meczem.
- Odtwarzalny pipeline: zbiór danych z wersją i hashem, stały seed, jawna konfiguracja, eksport modelu z hashem.
- Wartości P(1)+P(X)+P(2)=1, bez przecieków i bez kursów jako wejść.
- Oddzielny etap oceny na dopuszczonych danych, bez podglądu wyniku i bez selekcji pod TEST.
- Wymagany wynik końcowy kroku 14: model, hash, metryki i log, ale **tylko po dowodzie uprawnienia do treningu**.

## Co można wykonywać od razu, bez naruszania danych

1. Zdefiniować kontrakt cech i jednolity schemat `features_asof_utc`, `source_observed_at_utc`, `fixture_id`, `kickoff_utc`, maski braków i kolejność cech; osobno cechy xG i wariant bez xG.
2. Przygotować deterministyczny szkielet CPU CatBoost z testami **wyłącznie sztucznymi** (seed, hashe, walidacja typów, obiektywna kontrola normalizacji i zakazu odds).
3. Zweryfikować, że data źródła każdej cechy jest wcześniejsza od kickoff oraz że 2026/27 holdout i wcześniej ujawnione VALIDATION nie trafiają do treningu.
4. Utrzymywać rozdział między `synthetic_pipeline_ready`, `real_data_training_eligible` i `production_approved`. Żaden status nie jest automatycznie promowany.

## Co nadal jest zabronione

- Uznawanie retrospektywnego odczytu w październiku 2026 za udowodnione historyczne cechy dostępne przed meczem.
- Trening na 380 VALIDATION ani na 2026/27 TEST, nawet po poznaniu części wyników.
- Wykorzystywanie pierwszych 20 zamrożonych prognoz do dobierania parametrów M1.
- Nowy płatny dostawca lub przejście do produkcji bez osobnego pozwolenia.

**Stan:** KROK 14 W REALIZACJI — faza specyfikacji/testów syntetycznych. `actual_catboost_fit_completed=false`, `real_training_allowed=false`, `new_api_cost=0`, 13/29 zakończonych. Nie dodano żadnego kroku do planu.
