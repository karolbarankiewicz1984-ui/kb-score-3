# KB Score 3.0 — badawcze porównanie z i bez xG5, 3 listopada 2026

## Polecenie
Kontynuacja po audycie pełnych 29 pierwotnych etapów. Formalnie ukończono 1–15, krok 16/17 PENDING. Celem jest bezpieczne przyspieszenie pierwszego uczciwego badania wpływu xG5 bez naruszania stałego M0, chronionego TEST i kalibracji.

## Rzeczywisty stan na wejściu
- Ostatni [M0 settlement 3 XI 16:17 UTC](../data/pit_sidecar/m0_720_eight/2026-11-03/settle-161734908878/RECEIPT.json): 91 prawdziwych zamrożonych prognoz, 74 kwalifikujące się rozliczenia, brak 26 do FIT100, następnie 50 nowych po FIT HOLDOUT. Brak zatwierdzonego kalibratora. Brier sum3 0,56181793, log loss 0,94705081, trafność 59,46%, tylko jeden wspólny rozliczony mecz istniejących trzech silników.
- [Raport historyczny PitchAPI](../data/pit_sidecar/historical_multistat/2026-11-03/run-41665018210-1-summary/ROLLING_AFTER_RECHECK.json): 576 autentycznych szczegółowych meczów, 522 zweryfikowane natywne xG; 146 pełnych par xG5 (BEL=106, ESP=40), 32 xG10 i 5 xG15. To retrospekcja, bez historycznego dowodu pierwszej publikacji sprzed dawnych spotkań.
- Formalne kroki GATE16/GATE17 nie są zakończone; nikt nie może wyciągać skuteczności xG z samych liczników.

## Eksperyment wdrażany oddzielnie
1. Nowy skrypt scripts/step17_xg5_research_ablation.py odczytuje wyłącznie istniejącą bazę historyczną SQLite w trybie read-only. Wymaga rzeczywistego indeksu zakończonych meczów, oryginalnej obserwacji i badawczego cache prawdziwych poprzedników. Odrzuca każdą niekompletną ostatnią piątkę xG, fałszywą certyfikację PIT, ENG i UCL bez mapowania drużyn. Nigdy nie wykorzystuje własnego wyniku celu jako cechy.
2. Podział chronologiczny jest ustalony przed dopasowaniem: co najmniej 80 wcześniejszych przykładów TRAIN oraz 25 późniejszych VALIDATION, te same kickoff nie mogą znaleźć się po obu stronach granicy. Jeśli brakuje przykładów — raport NO_GO zamiast fikcyjnego treningu.
3. Dwa CatBoostClassifier, całkowicie identyczne parametry, ta sama populacja i ta sama walidacja: pierwszy używa bramek, punktów, strzałów, fauli, rożnych i żółtych kartek z ostatnich 5; drugi dodaje dokładnie cztery cechy xG/xGA obu drużyn z 5 faktycznych meczów. Brier sum3, log loss, accuracy, ECE i delty są raportowane dla tych samych gier. Parametrów ani progu dopuszczenia nie stroimy po wyniku walidacji; brakujące nie-xG statystyki są NaN, a nie zero.
4. Testy test_step17_xg5_research_ablation.py i workflow kb3-step17-xg5-chrono-research.yml: PR bez sekretów i bez sieci, po merge na main prawdziwy fit offline z CatBoost, odrębna kontrola i raport zbiorczy archiwizowany w data/audits/step17_xg5_ablation. Harmonogram raportu 19:45 UTC, zero dodatkowych zapytań PitchAPI.
5. Uczciwy status: ten sparowany eksperyment jest porównaniem ablacyjnym dwóch małych CatBoost i NIE JEST porównaniem z oryginalnym M0 na identycznych meczach, wyborem zwycięzcy, formalnym GATE17 ani dowodem dla ośmiu lig. Każdy prawdziwy wynik i jego GitHub Actions trzeba osobno potwierdzić, a zamrożona Premier League 2026/27 pozostaje nietknięta.

## Kontynuacja wszystkich pierwotnych etapów
- Krok 16: zachować niezmienne M0 i 74 rozliczenia, zebrać rzeczywiste 100 FIT oraz 50 przyszłych HOLDOUT; nie dopasowywać przedwcześnie.
- Krok 17: zwiększyć pokrycie poza BEL/ESP, połączyć M0, Elo-only, CatBoost bez xG, CatBoost z xG i ensemble na dokładnie tej samej walidacji z bootstrapem tygodniowym i kontrolą kosztu braków; formalna zależność od 16 pozostaje.
- Krok 18: bez wyboru Championa z małego retrospektywnego eksperymentu; decyzja tylko po dowodach i zatwierdzeniu właściciela.
- Kroki 19–22: równolegle rozwijać exact-market odds i kryteria WATCH/HIGH P/EV, kompletne przedmeczowe EARLY/FINAL oraz settlement.
- Kroki 23–29: generator trzech PDF, harmonogram dostarczania, powiadomienia, cykliczny Challenger, monitoring, dodatkowe rynki i panel mobilny pozostają do formalnego odbioru.
