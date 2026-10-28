# KB Score 3.0 — krok 14: końcowe Elo 2023/24 → 2024/25 i historyczne xG (28.10.2026)

## Granica sezonów i matematyka

W oryginalnym `src/kb3_features.py`, `EloParameters(initial=1500, k=20, home_advantage=65, scale=400, season_retention=0.85)`. Zespół rozgrywający mecz w kolejnym sezonie zachowuje dokładnie:

```text
Elo_2024_before_first_match =
    1500 + (Elo_2023_at_end_of_available_history - 1500) * 0.85
```

W meczach rozpoczynających się jednocześnie korygujemy Elo dopiero po wyliczeniu wszystkich prawdopodobieństw z ratingów sprzed tej godziny. Przy drużynie debiutującej w 2024/25 `Elo=1500`. Utrzymanie istniejącej drużyny należy rozstrzygać po stabilnym natywnym `PitchAPI team ID`, nie z nazwy czy z ID FPL następnego sezonu; w odtworzeniu badawczym wyłącznie z publicznych nazw jest to **niezależny, niezatwierdzony** join.

**Decydująca godzina:** Premier League oficjalnie potwierdziła pierwszy mecz nowego sezonu w piątek **16.08.2024, 20:00 BST = 19:00 UTC**, Manchester United–Fulham, https://www.premierleague.com/en/news/4083040 . Zatem zbiór wszystkich 380 rezultatów 2023/24 wystarcza do odtworzenia punktu końcowego i jego przeniesienia do 2024/25 *tylko wtedy*, gdy mamy autentyczny stary plik z 380 FT i niezależną datę upublicznienia **przed** tym startem. Nie trzeba 380 codziennych skanów publikacji dla samego ratingu **końcowego**; te są potrzebne dopiero, gdy chcemy certyfikować Elo dla każdego wcześniejszego docelowego spotkania 2023/24.

Warunki osobno:
1. Autentyczne stare 2023/24 CSV / JSON z 380 kompletami FT (nie 380 pustymi terminami), 20 drużyn po 38 spotkań, daty meczów wcześniejsze od publikacji.
2. Zweryfikowany hash starego pliku i niezależny historyczny **GH Archive PushEvent** dokładnego source `commit SHA` na publicznej gałęzi przed 16.08.2024 19:00 UTC. Godzina autora / commitera nie jest publikacją. Jeśli brakuje dowodu — BLOCK.
3. Pierwotne wyniki wszystkich 380 porównać lokalnie z RSA PitchAPI po 100% identyfikacji 2023/24; dowód 270/270 poprzednich porównań **nie jest** takim testem 380/380, ponieważ kilka migawek zawiera powtórzone wcześniejsze wyniki.
4. Dopiero po zamrożeniu kompletnego 2023/24 ciągu, weryfikacji stabilności natywnych `team_id` oraz izolowanego 2024/25 wcześniejszego ciągu 60 sprawdzić `Elo_2024` z `season_retention=.85` i opublikować **wyłącznie agregaty** zgodności, nie wartości ratingów/oryginalne wyniki.
5. Dopuszczenie do historycznego treningu CatBoost wymaga nadal odrębnego per-target, per-field PIT 121+38 oryginalnych cech, w tym xG/xGA, więc samo pełne końcowe Elo nie otwiera GATE14.

## Historyczne xG: odrębne kontrakty

W repozytorium publicznym [vaastav/Fantasy-Premier-League](https://github.com/vaastav/Fantasy-Premier-League) historyczne `gws/gw38.csv`, `gws/gw6.csv` mogą zawierać **Opta/FPL player `expected_goals`** oraz fixture ID. Oryginalny model wymaga **obserwacji team xG/xGA dla konkretnego meczu od PitchAPI**, co nie jest semantycznie tożsame z pojedynczą kolumną xG zawodnika. Zsumowanie xG zawodników może być odrębną cechą, ale zmieniłoby kontrakt/definicję cech i na obecnym etapie jest **zakazane jako cicha podmiana**.

[Understat](https://understat.com/) ma własne meczowe team `xG/xGA` i oddzielną metodologię; publiczny aktualny plik i `capture_at` po kilku latach **nie dowodzi** historycznej dostępności przed dawnym meczem ani równoważności z PitchAPI. Nie wolno użyć `npxG` zamiast `xG` ani interpolować braków jako 0. Dla obu kandydatów wymagamy: stary, surowy, identyfikowalny blob; niezależne serwerowe `published_at` z granicą na początku późniejszego meczu; stabilny `fixture_id`; jawna definicja xG; ewentualnie lokalna kontrola skali z oryginalną obserwacją PitchAPI. Źródła pomocnicze: https://github.com/withqwerty/football-docs/blob/main/docs/free-sources/understat.md oraz https://www.premierleague.com/en/news/4083040 .

## Wynik badania (obowiązuje log rzeczywiście ukończonego workflow)

Program `src/kb3_step14_elo_rollover_xg_clock_discovery.py` i workflow `.github/workflows/kb3-step14-2023-end-elo-xg.yml` sprawdzają cztery zamknięte zakresy historyczne:

- kompletny 2023/24 `fixtures.csv` od końca maja do połowy sierpnia 2024;
- FPL 2023/24 GW38 `gw38.csv` — kontrola pierwotnego występowania player xG;
- FPL 2024/25 i 2025/26 GW6 `gw6.csv` — analogiczna kontrola historycznego player xG.

Wybór SHA jest jedynie wyszukiwaniem, nigdy dowodem publikacji. W przypadku błędów publicznego API, ograniczeń sieci lub niedostępności GH Archive program zwraca nieudowodnienie, nie wydaje fałszywego PASS. Przebieg GitHub Actions uruchamia się bez klucza RSA, danych TEST, oryginalnych celów lub płatnych usług sportowych.

**Wcześniej rzeczywiście potwierdzone:** 270/270 porównań wcześniejszych publicznych FT z zaszyfrowanym PitchAPI w 3 migawkach, 0 rozbieżności, 8 + 8 częściowych par Elo 2023/24 i 10 izolowanych źródłowych par Elo 2024/25. Nie jest to 380/380 koniec 2023/24. Oryginalny M1 wciąż zablokowany; 13/29, TRAIN 0/760, VALIDATION 0/380; GATE14 PENDING, TEST nienaruszony.


## Rzeczywiste wyniki niezależnych archiwów (CI #40632634060)

**NOWY POTWIERDZONY DOWÓD** — publiczny GitHub `vaastav/Fantasy-Premier-League`, commit `204c134d8e90e2b6e69ec252aa3ef6f10f21e73c`, `data/2023-24/fixtures.csv` SHA256 `d8521bdbb80edb5141bc17df71bf6026275f2e56fd6a6dc6041b3ae23a39ce6a`, **380/380 FT**. **NIEZALEŻNY** GH Archive PushEvent `38750359648` powiązał ten SHA z serwerowym UTC **2024-05-27T18:05:12Z**, tj. przed pierwszym meczem nowego sezonu 2024-08-16T19:00:00Z. Rzeczywisty publiczny replayer Elo obliczył 380 wydarzeń dla 20 zespołów po 38 i zastosował oryginalny wzór przeniesienia `1500+(rating−1500)*0.85`, nie ujawniając żadnego ratingu. Wcześniejszy plik 370/380 miał godzinę GH Archive niedostępną i nie jest potrzebny do końcowego Elo. [Trwały rejestr](../data/audits/STEP14_FPL_2023_FULL_380_GHARCHIVE_PUSH_AND_XG_2026-10-28.json). **Uwaga:** fakt 380 publicznych wyników nie dowodzi jeszcze 380/380 zgodności z prawdziwym oryginalnym PitchAPI, która wymaga lokalnej RSA kontroli.

W **tym samym niezależnie potwierdzonym zdarzeniu** udokumentowano historyczną kolumnę `expected_goals`, `fixture`, `team` w `data/2023-24/gws/gw38.csv` (SHA256 `8228d44505d2c27b79fc2b0079d48115be040e81906b4140217d64fb91da0fef`): jest to **Opta/FPL player GW xG z 2023/24**, dostępne **27.05.2024**, a nie dowód danych dla każdego wcześniejszego meczu **2023/24**. Dla dawnych 2024/25 `gw6.csv` i 2025/26 `gw6.csv` potwierdzono **stare SHA i obecność kolumny**, lecz niezależne historyczne `published_at` konkretnych wersji nie zostało potwierdzone. Player xG FPL nie podmieniamy na oryginalne team xG PitchAPI i nie uznajemy zmiany dostawcy xG bez jawnej decyzji i pomiaru różnic.

## Ostatnia brakująca kontrola pełnego rollover po natywnych ID — przygotowany kod owner-only

Zabezpieczony `src/kb3_step14_owner_elo_2023_to_2024.py` i wrapper `scripts/step14_owner_elo_rollover_380_local.py` na oryginalnym RSA właściciela:

1. Powtórnie weryfikuje źródłowy, niezależnie datowany pełny publiczny blob 2023/24 oraz 60 wcześniejszych FT w OpenFootball 2024/25 (02.10.2024), oba SHA.
2. Uwierzytelnia oryginalne ZIP i `receipt chain`; odtwarza w pamięci 1140 **tożsamości**, ale czyta **wyłącznie** wyniki 380 spotkań 2023/24 oraz 60 wcześniejszych spotkań 2024/25, które są udokumentowanymi poprzednikami dla **październikowych 2024/25 celów**. Nie czyta innych wyników TRAIN ani VALIDATION czy TEST.
3. Wymaga 380/380 i 60/60 zgodności z PitchAPI, pełnego dopasowania FPL team ID do PitchAPI, stabilnych `team ID` 17 pozostających i dokładnie 3 nowych klubów (inicjalne Elo 1500). W razie jakiejkolwiek rozbieżności kończy FAIL CLOSED.
4. Odtwarza prawdziwy ciąg 2023/24 Elo (K20, home 65, scale 400), carry-over `season_retention=0.85` po **oryginalnych natywnych ID**, a następnie 60 aktualizacji Elo 2024/25 z grupowaniem równoczesnych meczów; weryfikuje, które z 10 2024/25 celów mają pełnych poprzedników bez przecieku wyników.
5. Wyświetla i zapisuje **wyłącznie agregaty**, nie wyniki czy ratingi, w nowym JSON poza repozytorium. Jest to **osobny etap lokalny, którego nie wykonywano w GitHub Actions** — nie ogłaszać 380/380 natywnej zgodności ani 10/10 pełnego Elo przed tym przebiegiem.

Po pobraniu aktualnego `main` z GitHub w nowym folderze na Windows uruchomić:

```powershell
py -3 -m scripts.step14_owner_elo_rollover_380_local --archive-zip "$HOME\Downloads\KB3_PITCH_PL_2023_2026_NATIVE_20261026.zip" --private-key "$HOME\Desktop\KB3_760_PAKIET_ODZYSKIWANIA_POUFNE\KB3_760_KLUCZ_ODZYSKIWANIA.pem" --output "$HOME\Desktop\KB3_STEP14_ELO_2023_2024_PRIVATE_AGGREGATE.json"
```

Nie przesyłać RSA PEM, odszyfrowanego ZIP, ani prywatnych ID. Zapis ekranu z samymi agregatami można wykorzystać jako kolejne potwierdzenie. **Nadal formalnie GATE14 PENDING, 0/760 TRAIN, 0/380 VALIDATION** — bez certyfikacji xG i wszystkich 121+38 oryginalnych cech nie ma produkcyjnego M1.


## Dodatkowy faktyczny wynik: stary pełny FPL xG GW zawodników (CI #40633173937)

Wbrew wcześniejszej sytuacji, gdy znaleziono tylko `gw38.csv`, zbadano także *rzeczywisty* stary `data/2023-24/gws/merged_gw.csv` z tego samego opublikowanego `204c134d8e90e2b6e69ec252aa3ef6f10f21e73c`, SHA256 `e9c09c8856f1c86b4f920f46ddd5033af83409439dfda53be925df2a3e7c8a9e`. CI #40633173937 **SUCCESS, 5/5 testów**: **29 725 wierszy zawodnik–mecz, 380/380 identyfikatorów spotkań FPL z liczbowym `expected_goals`, 0 nieprzypisanych spotkań, 0 brakujących xG**. Publiczna wersja pliku została poświadczona niezależnym GH Archive PushEvent `38750359648` **2024-05-27 18:05:12 UTC**, a więc przed otwarciem 2024/25.

Jest to **historyczny dowód dostępności FPL/Opta *player-per-fixture xG***, ale **nie** dowodzi, że te wartości były dostępne *przed każdym docelowym spotkaniem 2023/24*, ponieważ pełny snapshot opublikowano dopiero po zakończeniu sezonu. W październiku 2024 wartości mogą stanowić alternatywne historyczne wejście, lecz nie podmieniamy automatycznie nimi oryginalnego zespołowego `PitchAPI team xG/xGA` ani nie uznajemy ich za 121+38 pełnych oryginalnych cech. Konieczna byłaby jawna osobna metodologia xG, zgodność tożsamości i kontrola danych wejściowych z chwili przed każdym targetem. [Zamrożony rzeczywisty raport xG](../data/audits/STEP14_FPL_2023_ALL380_PLAYER_XG_PUBLISHED_MAY2024_2026-10-28.json).

**Lokalny kod full 2023/24 FT → Elo 2024/25 ma przejść jedynie na komputerze właściciela z jego RSA i oryginalnym ZIP**; testy GitHub Actions tylko symulują źródła i bezpieczne bramki. Do czasu prawdziwego przebiegu nie twierdzimy, że 380/380 historycznych FT jest zgodnych z natywnym PitchAPI ani że 10/10 oryginalnych docelowych Elo ma zweryfikowaną ciągłość. GATE14 pozostaje PENDING.
