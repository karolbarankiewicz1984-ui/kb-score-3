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
