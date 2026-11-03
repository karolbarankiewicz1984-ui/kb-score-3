# KB Score 3.0 — naprawy 1–3: szybszy backfill, xG i żółte kartki (03.11.2026)

## Decyzja właściciela i zakres
Polecenie bezpośrednie: **uruchomić naprawy 1–3**: przyspieszyć zbieranie 200–300 spotkań, zdiagnozować i zweryfikować niespójne xG oraz odzyskać brakujące wartości żółtych kartek. Zachować oddzielny, badawczy i append-only rejestr, nie modyfikować M0, zamrożonych prognoz, oryginalnych historycznych obserwacji i chronionej Premier League TEST 2026/27.

Stan potwierdzony przed zmianą: [realny run #41655564035](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/41655564035): 96 szczegółowych spotkań w źródłowym SQLite, 85 zweryfikowanych xG, 11 rozbieżności sumy xG strzałów vs statystyk, 70/96 meczów z liczbowymi danymi żółtych kartek obu drużyn. Indeks 8621 zakończonych spotkań. Pełne xG5 dla obu drużyn w 8/96 retrospektywnych celach; xG10/xG15 jeszcze 0.

## Naprawa 1: przyspieszone, ale bezpiecznie podzielone źródło

- Nowy skrypt `scripts/kb3_history_accelerated.py` uruchamia **do pięciu oddzielnych, w pełni zabezpieczonych pakietów po maksymalnie 48 zakończonych meczów**. **Maksymalnie 240 nowych spotkań na jeden workflow**; nie jest to obietnica, że każdy pakiet zwróci 48. Sumarycznie do 5 × 150 zapytań historycznych plus osobny ograniczony audyt problemów.
- Celowe rozdzielenie paczek pozwala zachować istniejący limit 16 MiB surowego pakietu dowodowego i poprawną weryfikację AES-GCM/RSA dla każdej partii; unikalny `run-token-b1..b5`, niezależny manifest SHA i bazowa baza SQLite po każdej udanej partii. W przypadku nieudanego całego jobu artefakty są uploadowane `if:always()`, a commity źródłowe na main dopiero po testach i weryfikacji wszystkich utworzonych paczek.
- **Nowa selekcja brakujących dokładnych poprzedników**: wybór brakujących meczów występujących w rzeczywistych last5/10/15 dla już zaobserwowanych historycznych celów. Preferencja last5, następnie last10 i last15; do 75% pakietu pochodzi z tej pilnej kolejki, pozostałe 25% uzupełnia zwarte sezony. Gdy pilnych braków nie ma, pobieramy zwarte ciągi i następnie głębszą historię. Nie wolno podmieniać brakującego z pięciu rzeczywistych poprzedników wcześniejszym spotkaniem z xG.
- Dalej 34 źródłowe zakresy liga×sezon (tam gdzie dostawca udostępnia), brak sztucznych sezonów POL 2023/24 i 2024/25, brak odczytu ENG. Harmonogram GitHub Actions bez dodatkowych automatyzacji.
- Brak gwarancji odporności na awarię pomiędzy commitem na main i artefaktem jobu: retry jest idempotentny według rzeczywistych ID, a nie syntetycznych braków. Nie zwiększono wersji produkcyjnej modelu.

## Naprawa 2: dokładna diagnostyka xG bez fałszywego dopuszczenia

- `scripts/kb3_history_issue_recheck.py` niezależnie pobiera od nowa `matches.stats(match_id)` oraz `matches.shots(match_id)` dla dotąd niezweryfikowanych meczów, maksymalnie 30 w jednym przebiegu. Zachowuje rzeczywisty `observed_at_utc`, xG obu zespołów z obu źródeł, bezwzględną różnicę każdej strony oraz stan.
- `XG_REVERIFIED` wyłącznie przy poprawnej tożsamości meczów i obu drużyn, pełnym okresie, prawdziwych strzałach oraz różnicach <= **0.15** w obu drużynach. Większa różnica pozostaje `XG_DISAGREEMENT_PERSISTS`; nie włączamy źródłowego xG do modelu. Powodem nie musi być błąd API: różne definicje shot xG, karne, samobójcze, zakresy zdarzeń trzeba audytować osobno.
- Nowa **oddzielna, niezmienna SQLite** `data/research/historical_multistat/issue_rechecks.sqlite` oraz nowa zaszyfrowana paczka z pełnym oryginałem `data/pit_sidecar/historical_issue_rechecks/YYYY-MM-DD/run-ID-issues/`. Starą tabelę `observations` pozostawiamy bez zmian. Oryginalne dzisiejsze odczyty nadal nie dowodzą provider first-published-at z 2024/25.
- Dopiero pozytywna, niezależna rewalidacja może zostać użyta jako **jawna retrospektywna korekta** w odtworzonym research `rolling_feature_cache`; nigdy do historycznej zamrożonej prognozy.

## Naprawa 3: żółte kartki ze zdarzeń meczowych
- Dla dotąd brakujących statystyk `yellow_cards` (maks. 45 spotkań/run) pobieramy udokumentowane `matches.events(match_id)`. Liczymy tylko **jawne zdarzenia `YellowCard`** przypisane do natywnych ID drużyn; red card i substitution nie oznaczają automatycznie żółtej kartki.
- Pełna kontrola tożsamości meczu, obu drużyn, minuty, znanych typów zdarzeń, niepustej osi zdarzeń i zgodności z już istniejącą statystyką, jeśli jedna strona ma wartość. Pusta/niedostępna oś nie dowodzi zero kartek. Rozbieżność `EVENTS_TEAM_STATS_CONFLICT` pozostaje kwarantanną, nie zastępuje oryginalnej wartości.
- `EVENT_YELLOW_CONFIRMED` może zostać nałożona wyłącznie na brakujące wartości w badawczym odtworzeniu statystyk; pierwotna próbka, jej SHA i publikacja pozostają bez zmian. Oddzielnie zapisujemy stan `RECHECK_ERROR` gdy API nie daje się odczytać — nie nazywamy tego sukcesem.
- API dokumentuje `client.matches.events` i typy `yellowcard`, `redcard`, `goal`, `substitution`, `penalty`: https://pitchapi.dev/ . Nie utożsamiać w tym etapie czerwonej po drugiej żółtej z dwoma osobnymi żółtymi bez twardych danych.

## Kontrola bezpieczeństwa, bramki i historia
- Nowy skrypt orchestrator używa istniejącego sekretu `PITCHAPI_API_KEY` wyłącznie na main, **PR tylko offline**.
- Offline testy: pięć niezależnych partii=240, brak sztucznego przyrostu przy pustym batchu, ograniczenia rozmiaru i brak dopuszczenia PIT; identyfikacja xG, trwała niespójność bez dopuszczenia, zdarzenia `yellowcard` vs `redcard`, błąd tożsamości, niepusta oś, konflikt znanych kartek, append-only SQLite i nałożenie wyłącznie zweryfikowanych poprawek.
- Akceptacja live wymaga rzeczywistego jobu main i sprawdzenia każdego `HISTORICAL_SOURCE.enc`+manifestu SHA, osobnego ISSUE_SOURCE.enc, raportów, integralności obu SQLite i nowego `ROLLING_AFTER_RECHECK.json`. Nie uznajemy samego merge za dowód rzeczywistych pobrań.
- Pozostawiamy oryginalne FIT100 + po-FIT HOLDOUT50, GATE16/17=PENDING. Niezależny CatBoost-xG nadal wymaga chronologicznego TRAIN/VALIDATION z prawdziwymi polami, bez przecieków.
- **Następne czynności w rejestrze**: rzeczywista ocena skuteczności 240-pakietu i kosztu/zawodności; analiza xG, które nadal się nie zgadzają; audyt kart `EVENTS_TEAM_STATS_CONFLICT`; przekrojowy komplet last5/10/15 i braków danych po ligach; POL 2024/25 oraz UCL mapowanie; trening badawczy bez awansu.
