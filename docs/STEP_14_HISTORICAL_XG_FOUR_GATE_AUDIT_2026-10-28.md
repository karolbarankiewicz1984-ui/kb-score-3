# KB Score 3.0 — krok 14: kompleksowy audyt historycznego xG, cztery niezależne warunki (28.10.2026)

**Cel:** udowodnić **as-of** dostępność xG *poprzednich* meczów dla cech modelu, z kompletną tożsamością spotkania, drużyny, jawnie zdefiniowaną statystyką i niezależnym czasem publikacji. **Status formalny 13/29, GATE14 PENDING, TRAIN 0/760 PIT, VALIDATION 0/380 PIT. Żadnego dopasowania M1 ani podmiany oryginalnych 121 cech i 38 flag.**

## Kontrakt 4G — co musi być spełnione łącznie

| Bramka | Wymagane dowody | Nie wolno uznać za dowód |
|---|---|---|
| 1. MECZ | historyczny identyfikator źródłowego `fixture_id`, stary blob SHA-256, wcześniejszy kickoff, zgodność z właściwym oryginalnym `PitchAPI fixture_id` osobno na RSA | zbliżona nazwa, ta sama data, współczesny terminarz po zmianach |
| 2. DRUŻYNA | `home/away` ze starego fixture, `was_home` każdego gracza, `opponent_team` zgodne z numerem FPL drużyny przeciwnej, spójny FPL team ID i brak duplikatu gracz–mecz; u oryginalnego PitchAPI osobno natywne team ID | automatyczne zamiany aliasów, porównanie wyłącznie nazw drużyn |
| 3. DEFINICJA | *FPL/Opta expected_goals zawodnika* sumowany jedynie dla własnej strony konkretnego spotkania; zachowana nazwa i metoda; oryginalna `PitchAPI team-match xG` musi być sprawdzona oddzielnie | automatycznie: FPL player xG ≡ team xG PitchAPI; `xP`, `npxG`, `expected_goals_conceded` powielane po graczach lub Understat ≡ PitchAPI |
| 4. PUBLIKACJA | identyczne SHA starego pliku, SHA źródłowego commita, niezależny GH Archive `PushEvent` dla tego SHA z serwerowym UTC oraz `published_at <= feature_cutoff < target kickoff`; opóźnienie wcześniejszego meczu minimum 3 h | git `author_date`/`committer_date`, późniejszy `captured_at`, dzisiejsza wartość sprzed lat |

Każda niespełniona bramka przerywa certyfikację danej **konkretnej** obserwacji, nie dopisuje xG=0 i nie przesuwa jej daty wstecz. Sytuacje z przeniesionymi kickoffami wymagają osobnej historii zmian terminarza. Oryginalny `src/kb3_features.py` w trybie `verified` żąda `VERIFIED_PREMATCH`, prawidłowego `published_at_utc`, `captured_at_utc` oraz dokładnego team–fixture. Wsparcie FPL pozostaje **warstwą badawczą**, nie modyfikacją tego kodu.

## Potwierdzone rzeczywistymi, starymi publicznymi plikami

| Źródło FPL/Opta | Rzeczywisty UTC niezależnej publikacji | Stare mecze z xG obu drużyn | Badawcze cele z poprzednim xG formy 5 |
|---|---|---:|---:|
| 2023/24 październik, commit `96fbc38...`, GH Archive `32344206544` | 05.10.2023 14:38:59 | **70** | **8/8** |
| 2023/24 grudzień, commit `c4f66ee3...`, GH Archive `33866831577` | 04.12.2023 13:04:15 | **140** | **8/8** |
| 2023/24 pełny sezon, commit `204c134d...`, GH Archive `38750359648` | 27.05.2024 18:05:12 | **380** | nie dowodzi as-of dla wcześniejszych meczów 2023/24; jest źródłem przed sezonem 2024/25 |

**Prawdziwy przebieg CI #40659018398:** stare pliki `data/2023-24/gws/merged_gw.csv` poświadczały odpowiednio **4 880 i 10 042** wiersze zawodnik–mecz. Dla **16 par (migawka, mecz docelowy)** test prześledził **160 dopasowań** właściwego wcześniejszego `fixture_id + team` z numerycznym xG, z publikacją źródła przed docelowym kickoffem. Są to *wejścia do formy 5 w alternatywnym źródle FPL/Opta*, nie kompletny oryginalny zbiór treningowy; te same poprzednie spotkania mogą wystąpić w kilku migawkach. Szczegółowy bezpieczny raport: [STEP14_2023_FPL_PLAYER_XG_REAL_PREMATCH_LAST5_16_PAIRS_2026-10-28.json](../data/audits/STEP14_2023_FPL_PLAYER_XG_REAL_PREMATCH_LAST5_16_PAIRS_2026-10-28.json). Oryginalne SHA `merged_gw.csv` z października i grudnia zostały zamrożone; 2023/24 pełny May snapshot ma oddzielny SHA i 29 725 wierszy. **Zero wyeksportowanych wartości xG, wyników, graczy, prywatnych PitchAPI IDs czy TEST.**

**Prawdziwy przebieg CI #40658359847:** kompletna publikacja 27.05.2024, 29 725 wierszy, dokładnie **380/380 fixture i 760/760 team-fixture-sides** z liczbowym FPL xG. Zachowana zgodność identyfikatora przeciwnika dla każdej strony, odrzucanie powtórzonych danych zawodnika, wymóg wcześniejszej publikacji i jawna separacja definicji statystyki. Przy pierwszym przebiegu błędny domyślny limit odczytu uciął plik po 3 MB; pełne bajty z podwyższonym limitem przeszły oryginalny SHA i 15/15 testów — **to był problem programu pobierającego**, nie niezgodność historycznych źródeł.

## Oddzielna diagnoza semantyczna i ograniczenia

- **FPL/Opta:** `expected_goals` dotyczy gracza w konkretnym spotkaniu, źródło udokumentowane w starym pliku. Suma po stronie daje *zrekonstruowane FPL/Opta team xG*; `xGA` można w tym odrębnym kontrakcie pochodnym odnieść do xG przeciwnej strony. Nie można sumować per-player `expected_goals_conceded` jako meczowego xGA: ta kolumna może powtarzać wartość z obrony dla wielu graczy.
- **Understat:** oferuje meczowe team `xG/xGA`, a także `npxG/npxGA`; jednak **nie mamy** niezależnego, imiennego, opublikowanego przed *każdym* analizowanym meczem historycznego datasetu Understat ze stałymi ID i SHA. Aktualna strona/współczesny plik nie wystarcza. Model strzałów i klasyfikacja zdarzeń różnią się między dostawcami.
- **PitchAPI:** historyczny `provider_original_published_at_utc` dla oryginalnych 2023–2025 team xG **nie został dostarczony/udowodniony**. Dostępność bieżącej próbki PitchAPI xG w 2026 r. nie stanowi dowodu publikacji z 2023 r. Nie ma zatem prawa certyfikować oryginalnych cech xG 5/10/15 i ich flag jako historycznie dostępnych tylko dlatego, że istnieje historyczne FPL xG.
- **2024/25 i 2025/26:** osobny `src/kb3_step14_xg_old_clock_probe.py` bada historyczne FPL `gw6.csv`/`merged_gw.csv` przy użyciu SHA i GH Archive. Bez niezależnego zdarzenia dany materiał jest co najwyżej retrospektywnym kandydatem; raport ma jawny FAIL CLOSED. Sam autor FPL informuje o zakończeniu cotygodniowych aktualizacji po 2024/25.

Dokumenty definicji:
- Opta xG: https://theanalyst.com/articles/opta-football-stats-definitions
- FPL i uwaga o przecieku `xP`: https://github.com/vaastav/Fantasy-Premier-League/blob/master/README.md
- Understat team xG i osobne `npxG`: https://github.com/withqwerty/football-docs/blob/main/docs/free-sources/understat.md
- Badania różnic definicji danych zdarzeniowych: https://dtai-static.cs.kuleuven.be/sports/blog/how-data-quality-affects-xg/

## Decyzja / kolejne wymagane dowody

**Podbramka badawczego historycznego FPL player-xG** w zakresie konkretnych 8+8 spotkań 2023/24: **PASS dla 4G publicznego źródła, NIE PASS oryginalnego kontraktu PitchAPI**. Publiczny pełny 2023/24 xG jest historycznie dostępny przed startem 2024/25, ale z tą samą różnicą definicji. Dla oryginalnego M1 PitchAPI wymagamy jeszcze niezależnego (najlepiej pierwotnego od dostawcy) `published_at` samej statystyki team xG dla konkretnego meczu, odwzorowania na natywne IDs, potwierdzenia zgodności metody i liczbowej różnicy; następnie per-target i per-field 121+38 z brakującymi wartościami jako `null` i prawidłowymi missing flags. Nie wolno „uznać” alternatywnego FPL lub Understat za oryginalne PitchAPI bez oddzielnej, jawnej, wersjonowanej zmiany projektu.

**Formalnie: GATE14 PENDING, TRAIN 0/760 i VALIDATION 0/380 certyfikowanego oryginalnego PIT, M1 nienaruszony, zamrożony TEST nieczytany.**


## Zbadane także źródła 2024/25 i 2025/26 — wynik rzeczywistego CI

W `src/kb3_step14_xg_old_clock_probe.py` wykonano prawdziwy skan publicznej historii commitów i GH Archive dla trzech celowych plików. [Zamrożona diagnoza](../data/audits/STEP14_XG_2024_2025_OLD_PUBLICATION_CLOCK_GAPS_2026-10-28.json):

- 2024/25 `gw6.csv` i `merged_gw.csv`: stara wersja pliku wskazuje commit `57caf7e165ba47b48de9f307785aac79cb03b8af` i **datę commita (nie publikacji) 01.10.2024 08:56:28 UTC**. Niezależny GH Archive `2024-10-01-08` w badanym przebiegu był **niedostępny**, więc nie potwierdzono `published_at` przed 05.10.2024. Brak takiego potwierdzenia nie dowodzi, że źródło wówczas nie istniało.
- 2025/26 `gw6.csv`: odnaleziono commit `cd74fdea7d792f816e96e9ada4551f443d0e82c9`, godzina autora 30.09.2025 20:29:48 UTC. Odczytane archiwum `2025-09-30-20` **nie zawierało dokładnego publicznego PushEvent tego SHA**, więc także brak dopuszczenia PIT. Brak jednego zdarzenia nie wyklucza alternatywnej publikacji w innej godzinie.
- **Wszystkie trzy są wyłącznie kandydatami źródłowymi, 0 z 3 poświadczonych tutaj czasów publikacji.** Nie wyciągamy na ich podstawie uogólnienia o całym sezonie ani nie przypisujemy historycznego xG PitchAPI.

Sam dostawca PitchAPI publikuje definicję `shots[].expected_goals` jako prawdopodobieństwa trafienia pojedynczego strzału w skali 0–1, a team xG w `matches/{id}/stats` i metrykach advanced. Jego dokumentacja zaznacza, że modele xG dostawców nie są wymienne: https://pitchapi.dev/ . **Nie odnaleziono w publicznym opisie ścisłego pola `published_at` dla starej statystyki 2023–2025**; nie jest to dowód, że takiego pola nie ma w wewnętrznych danych dostawcy. W konsekwencji import historycznego PitchAPI w 2026 r. nie uzyskuje retroaktywnie PIT w roku 2023.

## Konkluzja w ramach istniejącego kroku 14

Zabezpieczono **reprodukowany, sprawdzony zewnętrznym zegarem i właściwą stroną źródłową dowód FPL/Opta xG dla 16 par historyczna migawka–mecz**. Zabezpieczono pełną kopię 2023/24 jako dowód dostępności przed sezonem 2024/25. Nie uzyskano dowodu równoważności z oryginalnym meczowym xG PitchAPI i nie udokumentowano daty pierwotnej publikacji tego dostawcy.

Żeby cokolwiek z xG weszło do *oryginalnego* M1: wymagane jest osobne, pierwotne archiwum meczowych team xG PitchAPI z niezależnym `published_at` i dokładnymi natywnymi `fixture_id/team_id`; bez tego nie wolno ani dopisywać oryginalnej wartości, ani podstawiać alternatywnego wyniku FPL/Opta. Możliwe dalsze porównanie FPL–PitchAPI to **wyłącznie audyt skali i różnic na zgodnych meczach**, nie aprobatą automatycznej zamiany definicji. `missing` pozostaje `null` z odpowiednimi flagami.

**GATE14 PENDING — formalnie 0/760 TRAIN i 0/380 VALIDATION z kompletnym oryginalnym PIT.**
