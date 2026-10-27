# KB Score 3.0 — Krok 14: pierwszy bezpieczny kontrakt CatBoost M1 (27.10.2026)

**Zakres:** wyłącznie techniczny, syntetyczny test 1X2 CatBoost CPU. Zamknięty krok 13 pozostaje bez zmian; nie zmieniono M0, podziału Step12 ani 20 podpisanych przedmeczowych prognoz. Krok 14 pozostaje **W REALIZACJI**, a nie ZALICZONO.

## Kontrakt i testy

- Skrypt src/kb3_step14_synthetic.py generuje **wewnętrznie** 90 fikcyjnych spotkań SYNTH_TRAIN i 30 fikcyjnych SYNTH_VALIDATION w oddzielnych, chronologicznych okresach. **Nie przyjmuje pliku z realnymi meczami** ani ścieżki do repozytoryjnych danych, nie uruchamia API, nie czyta historycznego TEST.
- Wzorzec pól: fixture_id, kickoff_utc, feature_cutoff_utc, source_observed_at_utc, partition, evidence_class, features, feature_availability, label_1x2. Dokładnie siedem dozwolonych cech (Elo, forma 5, xG, dwie flagi braku xG). Brak pól odds, wyniku z meczu docelowego i nieznanych metadanych. Obserwacja i dostępność **każdej** cechy nie mogą następować po cutoff; cutoff musi być przed kickoff.
- Dwa warianty CPU: NO_XG (3 cechy) i WITH_XG_MASKS (7 cech); brakujące xG pozostaje null oraz jawna flaga missing, **nigdy zastąpione zerem**. CatBoost otrzymuje techniczne NaN wyłącznie dla brakującej cechy numerycznej i widzi oddzielną maskę.
- Parametry demonstracji: seed 141027, iteracje 36, głębokość 3, learning rate 0.08, MultiClass, CPU single-thread. Kontrolowane są wszystkie klasy 1/X/2, suma prawdopodobieństw 1, syntetyczny log loss i Brier sum3. Eksport .cbm jest wykonywany do katalogu tymczasowego z SHA256, po czym plik jest usuwany; **nie jest to model użytkowy**.
- Testy negatywne wykrywają przeciek dat, rolę TEST, pola kursów i wyników, sprzeczne maski xG, brak strefy UTC oraz duplikaty. Metryki fikcyjnej walidacji nie mogą służyć do wyboru parametrów produkcyjnych.

## Bramki i kolejne czynności

Flaga synthetic_pipeline_ready może być true po wykonaniu demonstracji na CPU. Jednocześnie real_data_training_eligible=false, historical_pit_certified=false, production_approved=false i gate14_pass=false **pozostają niezmienne**. Sam napis SYNTHETIC w jakichkolwiek zewnętrznych danych nie jest dowodem ich pochodzenia: interfejs treningowy **nie przyjmuje danych zewnętrznych**. Do właściwego treningu konieczny jest niezależny dowód point-in-time dla wejściowych cech, odrębne dopuszczenie danych, a następnie oryginalna bramka kroku 14: wersjonowany zbiór, odtwarzalność, eksport i ocena bez przecieków. Prawdziwe VALIDATION i TEST pozostają poza treningiem. Bez nowych zakupów.

**Weryfikacja lokalna:** 27.10.2026, Python unittest: 10/10 PASS; dwa warianty CatBoost CPU ukończyły syntetyczną demonstrację. Niezależne CI GitHub pozostaje do weryfikacji na PR — lokalnego wyniku nie nazywamy automatycznie GitHub Actions PASS.
