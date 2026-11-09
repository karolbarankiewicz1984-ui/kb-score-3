# Wynik porównania wszystkich 87 cech z oryginalnym builderem — 09.11.2026

**Test wykonany, PASS na obu wersjach Python (3.11 i 3.12).**

- Kod testu: `tests/test_kb3_retro87_original_parity.py`, commit `90f95bbed`.
- Integracja CI: `.github/workflows/kb3-p1-shared-asof-v2-offline.yml`, commit `99f79aa7`.
- GitHub Actions run: `42576712770`, dwa joby `safety-and-parity (3.11)` i `safety-and-parity (3.12)`, oba `success`, krok `Compare all 87 independent retro values with original builder` `success`.
- Test generuje 25 syntetycznych wcześniejszych meczów, dwie drużyny docelowe, jeden cutoff, zaświadczenia `NETWORK_OBSERVED` wyłącznie **syntetyczne**. Następnie wywołuje **oryginalny** `build_shared_features(purpose='FORWARD',...)` i niezależną funkcję `baseline(...)` odpowiadającą algorytmowi `train_retro_87.py`.
- Porównano zbiory nazw **87/87** i wartości każdej kolumny (73 numeryczne + 14 missing flags). Różnice: **0**. W razie różnicy test wypisuje dokładne klucze i wartości i kończy się błędem.
- Ograniczenia: pojedynczy scenariusz testowy, jeden sezon, brak xG, brak sytuacji równoczesnych kickoffów, brak niezależnych realnych receiptów. **Nie jest to dowód identyczności na wszystkich historycznych 3592 rekordach** ani certyfikacja PIT. Funkcja baseline jest implementacją algorytmu w teście, nie importem lokalnego skryptu z GitHub (który nie jest w repo).
- Formalny model V3 pozostaje `NOT_TRAINED`, brak zatwierdzenia Shadow. M0/Champion/TEST bez zmian, 0 nowych wywołań płatnego API.

Wniosek: **PASS 87/87 na identycznym kontrolowanym wejściu**, należy rozszerzyć na reprezentatywne przypadki graniczne i archiwum rzeczywiste.
