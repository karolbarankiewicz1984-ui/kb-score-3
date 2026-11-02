# KB Score 3.0 — 02.11.2026: diagnostyczna kalibracja przyrostowa (SHADOW)

**Status:** kod badawczy w osobnej gałęzi; formalne GATE16 i GATE17 **PENDING**. Nie jest to produkcyjne wdrożenie ani zmiana modelu.

## Decyzja i uzasadnienie
Użytkownik polecił kontynuować budowę bez czekania na 100+50 meczów; model ma zbierać kolejne dane i dawać możliwość uczenia i kalibracji w tle. Rozdzielamy trzy strumienie:
1. **Stabilny M0 720 TRAIN** — istniejąca codzienna prognoza, niezmienny freeze, host proof, realne rozliczenia, pierwsza formalna temperatura dopiero 100 FIT + **50 nowych po FIT** HOLDOUT, brak automatycznej promocji.
2. **Uczenie modeli badawczych** — istniejący niepołączony PR #126 z 3 chronologicznymi foldami train-only CatBoost bez xG; bez dotykania 374 VAL i TEST oraz bez użycia 66 wyniku do strojenia M0.
3. **Nowy SHADOW prequential** — bez dodatkowego API i bez treningu CatBoost oblicza diagnostyczne, dynamicznie dobierane temperatury na historycznie znanych *w danym momencie* settlementach tego samego M0 i porównuje raw vs shadow. To osobna analiza, **nie zastępuje** 100 FIT + 50 HOLDOUT.

## Implementacja
- `src/kb3_step16_progressive_shadow.py`: odczyt SQLite **mode=ro**, integrity_check, foreign_key_check i wymagane tabele. Wybiera tylko 8 lig bez ENG, jedną wersję M0, rzeczywiste settlementy 90min i istniejące host-attested SHA. Ponownie kontroluje integralność payload SHA, serwerowy dowód przed kickoff i 90-minutowy lead. Nie zakłada, że SHA jest samodzielnym niezależnym dowodem publikacji.
- Dla każdego celu buduje pulę tylko z obserwacji **settled_utc < jego kickoff_utc**, bez lookahead; minimum **30** historycznie dostępnych settlementów do **diagnostyki**, nigdy do oficjalnego FIT. Dopasowuje T siatką istniejącej implementacji M1-math na *wyłącznie przeszłej* puli; ocenia tę zamrożoną surową prognozę z dwoma wynikami (raw vs shadow).
- `tests/test_step16_progressive_shadow.py`: synthetic forward-series 42, spóźnione rozliczenie, za mała liczność, duplikat, SQLite bez host proof, późna publikacja — wszystkie są wymogami odbioru CI.
- `.github/workflows/kb3-step16-progressive-shadow.yml`: offline PR CI, a po oddzielnym review/merge: cotygodniowy raport w niedzielę 23:49 UTC i ręczne wywołanie. **0 nowych wywołań PitchAPI**, brak GitHub write, brak sekretów, tylko 90-dniowy GitHub artifact. Trwała archiwizacja raportów wymaga osobnego zaakceptowanego mechanizmu, raporty CI nie zastępują rejestru decyzji.

## Ograniczenia i warunki odbioru
- Nie używać 2026/27 Premier League TEST; nie podłączać tego SHADOW do produkcyjnego generatora PDF ani podawać temperatury jako zatwierdzonej korekty.
- Nie stwierdzać poprawy modelu przed realnym przebiegiem na historycznych, host-attested settlementach i analizą liczebności oraz stabilności. Wraz z nowymi wynikami diagnosta rozszerza próbę automatycznie, **ale nie zmienia M0**.
- Wymagane: offline tests PASS, odczyt istniejącego SQLite z wynikami, potwierdzenie braków/pochodzenia, ocena czy zysk nie wynika ze szumu próby i formalny odbiór GATE16 dopiero po 100+50.
- PR #126 (walk-forward train-only) pozostaje osobnym eksperymentem — nie scalać w jeden trening bez audytu.
- Brak zmiany dotychczasowych 75 prognoz, 66 settlementów wg receipt z 02.11 18:24 UTC, żadnych zmian parametrów SHA, brak auto-awansu, koszt nowych subskrypcji = 0 zł.

## Rejestr operacyjny
2026-11-02, Europe/Warsaw: rozpoczęto niezależny badawczy mechanizm SHADOW. Po utworzeniu PR należy dopisać URL, commit SHA, wynik CI oraz stan na rzeczywistych danych. Do czasu wtedy jest to **IMPLEMENTED_ON_RESEARCH_BRANCH / CI_PENDING / UNMERGED**.
