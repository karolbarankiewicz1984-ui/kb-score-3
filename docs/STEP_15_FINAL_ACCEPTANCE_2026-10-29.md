# KB Score 3.0 — formalny odbiór kroku 15
Data: 2026-10-29. Decyzja użytkownika: zamknąć krok 15 i przejść do 16.
**GATE15 PASS — KROK15 ZALICZONO; postęp 15/29.**

## Potwierdzone warunki odbioru
- 22 rynki O/U, BTTS i gole drużyn, wspólny rozkład 90 minut; monotoniczność i dopełnienia PASS na 748 zestawach prognoz.
- 720 TRAIN i 374 niezależne chronologiczne VALIDATION; Brier i log loss z rzeczywistych wyników.
- M0 wygrywa z osobnym CatBoost na 22/22 rynków. Brier średnio po 18 unikalnych zdarzeniach: 0,18746462 kontra 0,19316377; log loss 0,55666742 kontra 0,57275732.
- Niezależny audyt ponownie policzył 132 wyniki metryk i sprawdził spójność 748 prognoz. GitHub Actions 40922276524 i 40922881340: SUCCESS.
- TEST Premier League 2026/27 pozostaje nieotwarty. Brak wdrożenia ML, kalibracji i zakupów API.

## Granice zaliczenia
Historyczne cechy w badaniu są rekonstruowane; nie udowodniono pierwotnych czasów ich publikacji przez PitchAPI. GATE15 PASS oznacza odbiór matematyki i porównania modeli, nie certyfikat historycznego PIT ani produkcyjną kalibrację. Oryginalny M0 pozostaje bez zmian.

[Pełny raport](STEP15_ML_GOALS_VS_POISSON_REAL_374_2026-10-29.md).
[Niezależny audyt](../data/audits/STEP15_INDEPENDENT_SECOND_SCORE_AUDIT_20261029.json).
[Realna walidacja](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40922276524).
[Kontrola niezależna](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40922881340).

**Następny krok 16: kalibracja, rozpoczęty, GATE16 PENDING.** Zasada autentycznych przyszłych prognoz 100+50, bez dotykania TEST i bez autowdrożenia.
