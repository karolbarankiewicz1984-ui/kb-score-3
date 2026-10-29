# KB Score 3.0 — Krok 16: kalibracja prawdopodobieństw
Data rozpoczęcia: 29.10.2026. **W REALIZACJI; GATE16 PENDING. Formalnie 15/29.**

## Zakres
Kalibracja 1/X/2: reliability bins per-klasa, Brier sum3, log loss, ocena przed i po. Nie przenosić map KB Score 2.1, nie używać sezonu TEST 2026/27. M0 zostaje benchmarkiem; challenger ML goli z kroku 15 nie awansował.

## Warunek autentycznych danych 100+50
Diagnostyka od 20–30. Kandydat temperatury dopiero po co najmniej 100 różnych, rzeczywiście wygenerowanych i niezmiennie zamrożonych przed kickoff oraz potem rozliczonych prognozach tej samej wersji, identycznego SHA parametrów, fazy, wariantu i zakresu lig. Dopasowanie wyłącznie na historii dostępnej przed datą fit. Następnie 50 kolejnych *nowych* prognoz powstałych po fit temperatury i z kickoff po fit, których wyniki zostaną później poznane. Bez autowdrożenia, bez przepisywania prognoz.

Temperatura T=softmax(log(P)/T) z wcześniej określoną siatką 0.7, 0.85, 1.0, 1.15, 1.4, 1.8, 2.2. Neutralne T=1. Nie trenować na 374 VALIDATION z kroku 15 i nie otwierać TEST. Dla O/U i BTTS osobna matematyka zachowująca wspólny rozkład.

## Istniejące komponenty
- src/kb3_step14_m1_math_calibration.py — metryki i temperatura.
- src/kb3_m0_live_settlement_calibration.py — rzeczywisty M0 shadow, SQLite, wersjonowanie, autentyczne rozliczenia, 100+50.
- docs/ADR_2026-10-29_FORWARD_M0_PIT_CALIBRATION_STORAGE.md — polityka i zakazy.

## Następne czynności
1. Zweryfikować liczbę realnych rozliczeń i daty freeze; nie mylić stanu kodu z wystarczającą próbką.
2. Przetestować odrzucenie przecieków, mieszanych SHA, duplikatów, spóźnionych prognoz i mieszanych faz.
3. Przygotować raport per-klasa 1/X/2, porównanie przed/po dla niezależnego holdoutu i rejestr decyzji.
4. GATE16 dopiero po audycie rzeczywistego procesu; nie ogłaszać PASS przy braku 100+50.

**Krok 16 otwarty, brak automatycznie zatwierdzonej temperatury i kosztów.**
