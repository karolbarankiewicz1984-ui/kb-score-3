# KB Score 3.0 — obowiązująca rekonstrukcja FPL74, skorygowany parser i 40 xG5 TRAIN

**Data:** 29.10.2026. **Status:** zatwierdzony tor badawczy; formalny **GATE14=PENDING**, nadal 13/29. [PR #96](https://github.com/karolbarankiewicz1984-ui/kb-score-3/pull/96) i [PR #98](https://github.com/karolbarankiewicz1984-ui/kb-score-3/pull/98) scalone. Rzeczywisty końcowy przebieg [GitHub Actions #40898237848](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40898237848) — **SUCCESS**, w tym utrwalenie wyników w `main`.

## Wyniki — obowiązuje poprawiona wersja v2

| Pozycja | Realny wynik |
|---|---:|
| Historyczne rewizje `vaastav/Fantasy-Premier-League/fixtures.csv` w inwentaryzacji | **74** (2023/24:38 + 2024/25:36) |
| Dowody dawnego upublicznienia przez graf Git i starsze niezależne zdarzenie GH Archive | **74/74** |
| Rewizje bezpiecznie przetworzone do źródłowych danych meczowych | **71/74** |
| Odrzucone rewizje (przyszły target miał w źródle już wpisany wynik) | **3** |
| Rygorystyczny historyczny publiczny FORM5 na oryginalnym TRAIN | **54/760** |
| **Pełne alternatywne FPL/Opta player-sum xG5 obu drużyn TRAIN** | **40/760** |
| VALIDATION z historycznie dowiedzionym FORM5 | **109/380** |
| VALIDATION z pełnym alternatywnym xG5 | **107/380** |
| Wersje starego `merged_gw.csv` 2024/25 o zmienionym układzie skorygowane | **3** |
| Historyczne wiersze przetworzone w zmienionym formacie 49 kolumn w 3 źródłach | **25 905** |
| Oryginalne natywne rekordy 121+38 PitchAPI dopuszczone PIT do M1 | **0 TRAIN + 0 VALIDATION** |

## Skąd wynik xG5 i dlaczego zmienił się z 31 na 40?

Pierwsza kompletna analiza wszystkich 74 rewizji prawidłowo odtworzyła **31** źródłowo poświadczonych rekordów pełnego xG5. Odrzuciła także trzy późniejsze archiwalne pliki, zgłaszając `UNKNOWN_FPL_VENUE_SIDE`. Odkryto, że od **GW22** 2024/25 do części wierszy FPL `gws/merged_gw.csv` dodano **7 kolumn przed polem `modified`**, bez uaktualnienia starego 42-kolumnowego nagłówka. W źródle są zatem równolegle rekordy 42- i 49-kolumnowe.

W osobnej **korekcie v2** stary surowy plik, jego commit SHA i SHA256 są zachowane. Do obliczeń w pamięci dopuszcza się wyłącznie dokładnie potwierdzone układy: 42 kolumny zgodne z nagłówkiem lub 49 kolumn z siedmioma całkowitoliczbowymi dodatkami na pozycjach 21–27, poprawną flagą `modified`, znanym `was_home` i `GW≥22`. Tylko dla drugiego układu pomija się 7 nowych, niepotrzebnych pól; sam oryginalny tekst `expected_goals`, `fixture`, `opponent_team`, `team`, `element` nie jest przeliczany ani zmieniany. Dodatkowo zapisuje się osobne sumy kontrolne starego pliku i pamięciowej normalizacji.

Po ponownej kontroli unikalnego `fixture`, `team`, `opponent_team`, `was_home`, braku duplikatów zawodników, pełnych danych dla obu stron oraz pięciu bezpośrednio poprzedzających meczów wynik zwiększył się do **40**. Jednocześnie FORM5 pozostał **54**, bez fikcyjnego rozszerzenia liczby targetów. Te 40 cech xG5 są **FPL/Opta player expected-goals sum**, nie oryginalnym natywnym xG PitchAPI — **nie wolno ich cicho podstawiać do starego M1**.

### Ważne o poświadczeniu czasu publikacji

Dla wszystkich 74 commitów potwierdzono ich przynależność do historycznej gałęzi poprzedzającej wcześniejszy, niezależnie poświadczony publiczny push `GH Archive`. Źródłowy czas as-of jest konserwatywną datą takiego poświadczonego **potomka**, nie dowodem dokładnej pierwszej publikacji każdego z 74 oryginalnych commitów. Wynik jest więc odporny na fałszywe daty `git author/committer`, lecz konserwatywny: nie rozszerza 54 kompletów TRAIN bez dowodu, że starsza wersja była publiczna wcześniej.

## Zapisane trwałe artefakty

- [74 historyczne SHA, osobny dowód DAG/przedmeczowego czasu i 3 wykluczone źródła](../data/audits/STEP14_ALL_74_FPL_REVISIONS_ANCHORED_GHARCHIVE_2026-10-29.json).
- [Wynik v2: 40 historycznych FPL player xG5, 54 FORM5, poprawione SHA i liczba 25 905 wierszy](../data/audits/STEP14_FPL74_2024_MIXED_XG_CORRECTED_V2_RESEARCH_SUMMARY_2026-10-29.json).
- [Wspólna, nadal odizolowana badawcza macierz 1140×159 v2, gzip](../data/audits/STEP14_FPL74_2024_MIXED_XG_CORRECTED_V2_1140x159_2026-10-29.jsonl.gz).
- [Końcowy, realny audyt oryginalnego M1 po korekcie](../data/audits/STEP14_FPL74_2024_MIXED_XG_CORRECTED_V2_ORIGINAL_M1_GATE_2026-10-29.json).
- [Kod bezpiecznej normalizacji 42/49 pól](../scripts/step14_fpl74_2024_mixed_schema_xg_corrected_v2.py) i [testy](../tests/test_step14_fpl74_2024_mixed_schema_v2.py).

Poprzedni raport [v1: 31 xG5](STEP14_FPL74_HISTORIC_2023_2025_REAL_PLAYER_XG_AND_PIT_2026-10-29.md) pozostaje nienaruszony jako historia audytu, lecz **dla dalszych prac obowiązuje 40 w v2**.

## Następne realne blokady

GATE14 nadal wymaga oryginalnych natywnych wartości 121+38 ze zweryfikowaną dostępnością as-of, szczególnie semantyką i pierwszym czasem publikacji drużynowego xG PitchAPI, oraz większej liczby TRAIN. Najbardziej wartościowym następnym krokiem byłoby odszukanie **bezpośrednich** PushEvent dla poszczególnych commitów spośród 74, aby zastąpić konserwatywny czas późniejszego potomka faktycznym wcześniejszym czasem, a potem porównać FPL/Opta xG dla tych samych poprzednich meczów z oryginalnym PitchAPI. Oryginalny CatBoost M1 nie został wytrenowany, ani nie zmieniono modeli M0, metodologii Elo, wag, splitu i chronionego TEST 2026/27. Nie dodano płatnych usług ani szyfrowania.
