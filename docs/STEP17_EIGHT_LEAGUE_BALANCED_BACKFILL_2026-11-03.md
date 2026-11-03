# KB Score 3.0 — 03.11.2026 — zrównoważone pobieranie historii ośmiu lig

## Powód wprowadzenia
Rzeczywisty [eksperyment xG5 PR #141](../data/audits/step17_xg5_ablation/STEP17_XG5_ABLATION_41691844430_1.json) został przeszkolony na 102 meczach (BEL 90, ESP 12) i zweryfikowany na 44 (BEL 16, ESP 28). Natywne xG5 dla obu drużyn w raporcie historycznym było kompletne tylko dla 106 BEL i 40 ESP; pozostałe sześć lig nie miało pełnych celów. Badanie jest ważnym pilotem, ale poważny shift lig i tylko pięć tygodni walidacji nie pozwalają oceniać ogólnej przydatności xG.

## Faktyczna zmiana
- W istniejącym scripts/kb3_historical_pitchapi_backfill.py dodano funkcję underserved_national_scope. Dla rzeczywistego pakietu >=32 meczów i co najmniej trzech dostępnych narodowych lig 2025/26 wybiera ona najmniej nasycony statystykami scope spośród ośmiu, gdy różnica pokrycia między ligami wynosi co najmniej 64 unikalne mecze.
- Cała właściwa partia **48 meczów** koncentruje się wtedy na wybranej lidze, żeby realnie zbudować serię poprzedników 5/10/15 dla konkretnych drużyn. Do 75% wybieranych źródeł stanowią brakujące faktyczne poprzedniki już pobranych meczów tej ligi; reszta dopełnia zwarte rzeczywiście rozegrane 2025/26 lub wcześniejsze sezony. Priorytet brakujących poprzedników i brak fałszywych zer pozostają zachowane.
- UCL celowo wykluczona z mechanizmu równoważenia narodowych lig, ponieważ bez potwierdzonego mapowania drużyn między rozgrywkami nie wolno jej mieszać z historią ligową. ENG Premier League TEST pozostaje wyłączone.
- Gdy nie ma dużego niezrównoważenia, gdy zakres jest zbyt mały albo brak potrzebnej liczby sezonowych spotkań, nadal działa dotychczasowy bezpieczny dobór exact last5/10/15 + gęsta historia. Nie zmienia to dopuszczonych źródeł, godzin workflow, maksymalnych 5×48 meczów, 150 żądań na partycję ani źródłowych szyfrogramów/SQLite.
- Dodano testy z osiemnastoma historycznymi targetami, sztucznymi ID i 8 sezonowymi grupami: priorytet bardzo niedoreprezentowanego GER zamiast ciągłego BEL/ESP oraz automatyczna rotacja następnego batch do ITA, brak UCL i brak zmiany zachowania dla małych partii.

## Bramka i ograniczenia
Zmiana celu pobrań nie dowodzi, że dane są kompletne lub że wydajność modelu wzrośnie. Odbiór wymaga offline PR CI oraz realnego GitHub Actions na main z prawdziwym raportem liczebności per league, SHA manifestów oraz obserwowaną poprawą w niedoreprezentowanych ligach. Jeżeli wynik nie jest poprawny — zachować ślad i wrócić do poprzedniego źródłowego selektora bez dotykania M0.

GATE16 i GATE17 pozostają PENDING, formalnie 15/29; żadnego nowego formalnego awansu, strojenia na VAL, dotykania EPL TEST ani nowej płatnej subskrypcji. Następny krok to nowy wieloligowy, wielotygodniowy eksperyment xG5; w ogólnym harmonogramie 29 kroków nadal potrzebna jest prospektywna kalibracja M0 na 100 FIT + 50 nowych HOLDOUT.
