# KB3 — krok 19: przygotowanie offline exact-market odds, 2 listopada 2026

**Zakres:** wyłącznie badawcza matematyka 1X2 na przykładach; bez pobierania kursów i bez zmian modeli. Formalny krok 19 zależy od niezamkniętych jeszcze 16–18 i pozostaje **PENDING**.

## Dlaczego już teraz
Użytkownik polecił kontynuować budowę równolegle do gromadzenia prospektywnych wyników. Po połączeniu bezsieciowego mechanizmu diagnostycznej kalibracji (PR #132) można przygotowywać niezależne komponenty kolejnych etapów, bez wyboru Championa, bez publikacji typów i bez czekania na 100+50.

## Co zaimplementowano
- `src/kb3_step19_market_math.py` — strict 90min market `FT_90MIN_1X2`, dokładnie komplet 1/X/2 jednego fixture, provider, bookmaker oraz UTC snapshot; kontrola kickoff/cutoff, brak obsługi innych rynków/line (fail closed), brak duplikatów, sprawdzanie decimal odds i wektora P niezależnego modelu.
- Zwraca surowe implied P, marżę sum(1/odds)-1, normalizację no-vig oraz EV arytmetyczne per jednostka, oddzielnie od samego prawdopodobieństwa P. Zwracany wynik jawnie mówi: quote proof unverified, no recommendation, no automatic bet, not formal GATE19.
- `tests/test_step19_market_math.py` — pięć testów poprawnej matematyki, mismatch rynku/line, bookmaker/snapshot, spóźniona obserwacja, duplikaty i niepoprawne ceny.
- `.github/workflows/kb3-step19-exactmarket-offline.yml` — wyłącznie darmowy test Python 3.11 na PR, bez sekretów/API i bez nadpisania danych.

## Otwarte bramki
- Dopuścić konkretne rzeczywiste kursy dopiero po audycie API-Football market ID, provider timestamp, bookmaker, dokładnej linii oraz po zapewnieniu poświadczenia publikacji; niczego nie rekonstruować wstecz bez dowodu.
- Zestaw 1X2 to tylko kontrolny przykład, pozostałe rynki wymagają osobnych kontraktów i reguł PUSH/VOID.
- Ranking HIGH PROBABILITY vs VALUE wymaga odrębnej kwalifikacji na zatwierdzonych P oraz konkretnych aktualnych kursach; ten moduł niczego nie wybiera i nie obstawia.
- Nie wpływa na M0, 66 wcześniej rozliczonych prognoz, istniejące 100+50, modele CatBoost, test 2026/27 Premier League, GATE16/17/18/19.

**Status:** na gałęzi research, CI i niezależny review wymagane do merge; brak nowego kosztu API.
