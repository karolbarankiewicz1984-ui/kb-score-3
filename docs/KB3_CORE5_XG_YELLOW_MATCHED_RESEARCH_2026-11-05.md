# KB Score 3.0 — CatBoost Core5 / xG / żółte kartki: rzeczywisty eksperyment badawczy — 05.11.2026

## Dowód źródłowy i sposób wykonania

- Oryginalne archiwum GitHub Actions **#42002590625**, ZIP **artifact #13402849432** pobrany przez połączoną aplikację GitHub; źródłowa 53 837 824-bajtowa `data/research/historical_multistat/observations.sqlite`, **SHA-256 `0eae525fac24c359b6441160950cd32f907ebbb64a815dafa957f5ef2ff4e765`**. SQLite read-only, `integrity_check=ok`, `foreign_key_check=[]`; zero nowego pobrania PitchAPI i zero zmian oryginalnej bazy.
- **Rzeczywiście wytrenowano lokalnie** izolowane nowe klasyfikatory CatBoost `1.2.8`, `MultiClass`, `iterations=180, depth=3, learning_rate=.035, l2_leaf_reg=8, random_seed=20261104, thread_count=2`. Algorytm tylko z historycznego wyliczenia średniej ostatnich **pięciu faktycznych meczów**, bez wstawiania braków jako 0; kontrola teoretycznego `cutoff=kickoff−2 h` i dojrzewania `predecessor kickoff+3 h`; **0 rozbieżności** kolejności pięciu poprzedników względem obliczonej bazy. Użyto 8 lig i sezonów 2023/24–2025/26; UCL, bieżący 2026/27 i angielski TEST wyłączone.
- Kod do odtworzenia na tej i przyszłych historycznych wersjach bazy: `scripts/kb3_core5_matched_experiment.py`; oddzielne testy `tests/test_kb3_core5_matched_experiment.py`; niezależne offline CI `.github/workflows/kb3-core5-matched-retro-research.yml`. Wyniki poniżej pochodzą z obliczenia na oryginalnym ZIP; formalny odbiór GitHub CI i ewentualny merge rejestrować osobno.

## Liczebność i chronologia

| Badawcza kohorta | Wszystkie mecze | TRAIN | VALIDATION | Embargo 7 dni |
|---|---:|---:|---:|---:|
| Historia pięciu poprzednich meczów z wynikami | 1 915 | — | — | — |
| Core5: gole + strzały, faule, rożne, żółte kartki | **976** | **683** | **256** | 37 |
| Core5+xG5 kompletne na tych samych fixture | **280** | **196** | **74** | 10 |
| Gole + strzały, faule, rożne, bez obowiązkowych kartek | **1 362** | 904 dostępne **przed granicą TRAIN Core5** | wspólne 256 Core5 | n/d |

- Dodatkowa populacja przy usunięciu żółtych: **+386** spotkań z 1915, a do wcześniejszego TRAIN można dołączyć **+221** rzeczywistych spotkań. Nie porównywano dokładności walidacyjnej na różnych zestawach fixture.
- CORE5 train do **2026-04-11 17:00 UTC**; validation od **2026-04-18 17:00 UTC**. Kompletny CORE5+xG5 train do **2026-04-26 17:15 UTC**, validation od **2026-05-03 17:15 UTC**.
- Odrębny eksperyment tylko z historyczną chronologią. Żaden z 976/280 rekordów nie jest oryginalnie poświadczoną migawką sprzed historycznego kickoff. `PIT_CERTIFIED=0`, `OFFICIAL_FIT_INCREMENT=0`.

## Uczciwe, sparowane porównania Brier sum3 / log loss

Mniejszy Brier / log loss oznacza lepszą ocenę probabilistyczną. Różnica w ostatniej kolumnie jest **nowy wariant − bazowy**, zatem *ujemna* oznacza poprawę. Każda para jest oceniana na **tych samych wynikach i identycznych meczach walidacyjnych**.

| Test | Walidacja | Bazowy log loss / Brier | Nowy log loss / Brier | Δ log loss / Δ Brier |
|---|---:|---|---|---|
| Core5 bez xG → Core5 z opcjonalnym xG (w brakach NaN, wspólne TRAIN 683) | **256** | 1.049704 / 0.631335 | **1.054534 / 0.634457** | **+0.004830 / +0.003122** |
| Core5 bez xG → bez kart, identyczny TRAIN 683 | **256** | 1.049704 / 0.631335 | **1.051268 / 0.632302** | **+0.001564 / +0.000967** |
| Core5 bez xG (TRAIN 683) → bez kart, rozszerzony TRAIN 904 wyłącznie ze starszych meczów | **256** | 1.049704 / 0.631335 | **1.050511 / 0.633155** | **+0.000807 / +0.001820** |
| Core5 bez xG → Core5 z kompletnym xG, ten sam pełny TRAIN 196 | **74** | 1.074711 / 0.649624 | **1.078749 / 0.650608** | **+0.004038 / +0.000984** |
| Podzbiór 100 meczów z kompletnym xG w walidacji pierwszego eksperymentu | **100** | 1.008746 / 0.607306 | **1.022394 / 0.616163** | **+0.013648 / +0.008857** |

**Trafność 1/X/2**: przy 256 spotkaniach Core5 bazowy `0.472656`, Core5 z opcjonalnym xG `0.460938`; przy 74 z kompletnym xG bez xG `0.459459`, z xG `0.486486`. Pokazuje, dlaczego nie wolno wybierać modelu wyłącznie według procentu trafień — Brier i log loss nie potwierdziły korzyści.

## Przedziały niepewności: brak dowodu przewagi

Bootstrap **600** prób blokowych po tygodniu kickoff, sparowane różnice nowy−bazowy:

| Test | 95% CI Δ log loss | 95% CI Δ Brier |
|---|---|---|
| 256: opcjonalne xG vs bez xG | **[−0.008403; +0.022053]** | **[−0.005940; +0.015166]** |
| 256: bez kart z szerszym TRAIN vs Core5 | **[−0.010443; +0.012071]** | **[−0.005203; +0.008866]** |
| 74: kompletne xG vs bez xG | **[−0.051838; +0.084774]** | **[−0.029981; +0.053354]** |

Wszystkie przedziały przecinają zero. **Nie ma stabilnego dowodu, że dodanie xG pomaga albo szkodzi, ani że pominięcie żółtych kartek poprawia prognozy.** Te wyniki są wyłącznie wskazówką do dalszych badań, nie zatwierdzeniem modelu.

## Wniosek i kryteria decyzji

1. **Utrzymać wariant z/bez xG jako równoległy eksperyment**, bez produkcyjnej promocji, gdyż ocena na historycznej retrospekcji nie potwierdza jego przydatności i brak historycznego PIT.
2. **Kontynuować zbieranie prawdziwych, zamrożonych przed meczami par M0–Shadow** i ich późniejsze rozliczanie — to właściwa niezależna walidacja.
3. Wariant bez żółtych kartek jest użyteczny do zwiększania pokrycia badań, ale nie jest obecnie wyraźnie lepszy prognostycznie. Kontynuować źródłowe odzyskiwanie żółtych kartek dla NED/POL/TUR, nie wpisywać pustych wartości jako 0.
4. Dopiero po większej chronologicznej walidacji, testach per liga, pełnej zgodności train/forward i dowodach przedmeczowych rozważyć następne decyzje. Utrzymać `M0`, `Shadow Six`, `100 FIT + 50 przyszłych HOLDOUT`, `GATE16/GATE17=PENDING` i 0 formalnych historycznych FIT.

**Nie wykonano** nowego live forecast, zmian dat, rekonstrukcji brakujących xG, trenowania prawdziwego 85-cechowego M1-R ani zmiany istniejącego CatBoost Shadow. Raport ma status **offline research-only**.
