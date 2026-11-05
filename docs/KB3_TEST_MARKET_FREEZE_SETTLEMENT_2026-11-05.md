# KB Score 3.0 — oddzielny rzeczywisty freeze rynków TEST i rozliczenia

**Data:** 05.11.2026, Europe/Warsaw. **Status przed odbiorem live:** izolowany kod badawczy, PR #165; nie jest nowym Championem, nie zmienia M0 ani rozliczeń GATE16/17.

## Uzasadnienie

W PR #164 zbudowano read-only podgląd rynków z oryginalnych host-poświadczonych prognoz M0. Tamte 74 wyniki nie były nowym przedmeczowym freeze rynku. Dla dalszej budowy TEST potrzebny jest **odrębny, rzeczywiście opublikowany przed kickoff rynkowy zapis** z dokładnym rynkiem, linią, wyborem, prawdopodobieństwem i własnym serwerowym dowodem czasu. Nie wolno wstecznie nadawać takiego czasu dawnym podglądom.

## Nowy przepływ (wyłącznie badań)

1. Wyłącznie odczyt prawdziwej SQLite M0-720 (URI mode=ro i PRAGMA query_only). Wymagana istniejąca oryginalna host-proof dla rodzica. Nie otwierać chronionego ENG Premier League TEST; nie uruchamiać PitchAPI, API-Football ani dopasowania modelu.
2. Nowa migawka rynków dla **faktycznie przyszłego** meczu: tylko jeśli realny czas nowego zapisu jest co najmniej **100 minut przed kickoff**. Przyjmujemy 10 minut bufora na artefakt i niezależny serwerowy dowód GitHub. Późny mecz nie tworzy nowego market freeze.
3. Każda migawka ma własny SHA256 i zawiera **28 odrębnych wyborów rynkowych**: trzy 1X2, trzy podwójne szanse, Over/Under 1.5/2.5/3.5, dwa BTTS, dwanaście rynków home/away team-total half-lines 0.5/1.5/2.5 i dwa wybory na liczbie goli 2.0 ze zdefiniowaną masą prawdopodobieństwa zwrotu. Wszystkie wartości są pochodnymi dokładnie tego SAMEGO zamrożonego lambda M0; wchodzą w oddzielny Research TEST, nie do FIT.
4. CI przesyła nowo utworzone bajty do odrębnego artefaktu GitHub Actions. Dopiero PO serwerowej publikacji kod pobiera z API GitHub **oryginalny ZIP** i weryfikuje jego SHA256, listę plików, każdy bajt oraz serwerowy created_at sprzed kickoff-90min. Gdy którykolwiek warunek nie przejdzie, **nie dokonuje publikacji do main**. Po PASS dopisywane są odrębne pliki do data/test_markets/freezes i data/test_markets/host_proofs. Nie zmienia istniejącej SQLite.
5. Późniejsze rozliczanie następuje tylko przy prawdziwym, immutable i prawidłowo zahashowanym **oryginalnym** rozliczeniu M0, z rzeczywistym wynikiem 90 min dostępnym najwcześniej trzy godziny po kickoff. Każdy wybór jest rozliczany osobno. Brier i log loss per-binarny rynek wylicza się wyłącznie dla WIN/LOSS; dla PUSH/VOID pozostają NULL, a dla linii 2.0 używana jest odpowiednio warunkowa prob. wygranej po wykluczeniu PUSH. VOID nie jest samodzielnie stwierdzany z braku wyników; wymaga osobnego potwierdzonego źródła, obecny live nie deklaruje żadnych VOID.
6. Zapis postmatch jest oddzielnym append-only plikiem w data/test_markets/settlements; brak realnego zakończonego wyniku nie generuje żadnego pozornego settlement. Poprawność starego oryginalnego wyniku źródłowego pozostaje odziedziczona po źródle M0, bez dopowiadania nowej niezależnej weryfikacji provider. Nie używać metryk poszczególnych zależnych wyborów jako niezależnych 28 próbek efektywności modelu.
7. Harmonogram wspomagający cztery razy dziennie UTC + uruchomienie na zmianę oryginalnej SQLite M0; **bez nowych sportowych API**. Zdarzenia pochodzące z modyfikacji data/test_markets nie uruchamiają ponownie workflow. Brak założeń o prawidłowości zegara na maszynie runner: dowodem jest serwerowa data archiwum i oryginalne bajty.

## Testy i bramki

- tests/test_kb3_test_market_ledger_v1.py — 6 scenariuszy (28 wierszy, sumy, PUSH, VOID tylko jawne, bezwzględny termin +100min, odmowa przekłamania SHAs, poprawność ZIP-bajtów i host time, prawdziwy model źródłowy, idempotencja, rozliczanie wyłącznie dojrzałych wyników).
- W CI włączone dodatkowo 7 dotychczasowych testów PR #164 i 12 testów matematyki Step15. Suma **25 testów**.
- Pierwszy CI PR #165 wskazał NameError przy sprawdzaniu linii oraz zbyt wąskie dopasowanie oczekiwanego wyjątku w teście negatywnym. Poprawiono obie sprawy w oddzielnych commitach. Właściwy odbiór opiera się tylko na kolejnych rzeczywistych zakończonych CI, nie pierwszym nieudanym przebiegu.
- **Formalny GATE**: niezależny dowód nowego host czasu + dokładne bajty, rzeczywista przedmeczowa migawka, następnie po ukończeniu spotkań prawdziwe rozliczenie wszystkich obecnych rynków. Dopiero potem rozważyć osobny generator 3 PDF. Bez automatycznej produkcji.
- **Zasady:** wszystkie nowe wpisy to badawczy TEST, bez kursów, bez typów do obstawiania, bez włączania na tej podstawie Championa i bez dopisywania żadnych obserwacji do 100 FIT+50 kolejnych HOLDOUT. P1-01 nadal PARTIAL, historyczny native PIT w formalnym TRAIN=0; główny plan nadal 15/29.

## Miejsca kodu

- src/kb3_test_market_ledger_v1.py
- scripts/kb3_test_market_ledger_runner.py
- tests/test_kb3_test_market_ledger_v1.py
- .github/workflows/kb3-test-market-freeze-settlement.yml

**Decyzja operacyjna:** dopuszczenie tylko po zatwierdzonym CI i kontrolowanym merge PR #165. Oryginalne M0, przypięty Shadow Six i archiwa prognostyczne muszą pozostać niezmienne; nie korzystać z prywatnych kluczy.
