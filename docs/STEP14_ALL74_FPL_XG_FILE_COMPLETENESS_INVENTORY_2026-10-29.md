# KB Score 3.0 / Step 14 — dodatkowy, kompletny audyt 74 historycznych rewizji FPL i plików player xG

**29.10.2026.** To rozszerzenie [zakończonej rekonstrukcji 74 FPL](STEP14_FPL74_HISTORIC_2023_2025_REAL_PLAYER_XG_AND_PIT_2026-10-29.md), a nie nowy trening M1. [Pomyślna procedura w GitHub Actions #40897665574](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40897665574).

## Rzeczywiste ustalenia

- Zbadano dokładnie **74** bezpośrednio pobrane historyczne rewizje `fixtures.csv`: **38** w sezonie 2023/24 i **36** w 2024/25. Repozytorium, pełne SHA i zawartość historycznych plików są zapisywane osobno dla każdej rewizji.
- Dla **71/74** znaleziono historyczny niepusty `data/<season>/gws/merged_gw.csv` z danymi `expected_goals` zawodników.
- **56/74** przeszło pełny audyt spójności historycznego player-xG: unikatowy zawodnik/mecz, prawidłowy `fixture`, kierunek `was_home`, `opponent_team`, nieujemne skończone liczby xG, 11 aktywnych zawodników dla każdej zliczanej drużyny i brak błędnych rekordów przy źródle.
- W **pozostałych 15 rewizjach z niepustymi plikami** audyt nie zezwala na automatyczne użycie xG jako wiarygodnej agregacji; szczegóły błędów zachowano per SHA. Trzy rewizje nie miały niepustego `merged_gw.csv`. **Nie zastępujemy ich zerem.**

## Ważne rozgraniczenie dowodu i modelu

Wcześniejszy osobny audyt [grafu 74 rewizji](../data/audits/STEP14_ALL_74_FPL_REVISIONS_ANCHORED_GHARCHIVE_2026-10-29.json) dowodzi, że wszystkie 74 SHA były przodkami autentycznie opublikowanych, niezależnie datowanych historycznych zdarzeń GH Archive. **11** wybranych SHA plików FPL ma bezpośrednie poświadczenie starych pushów; dla pozostałych **63** stosujemy **konserwatywny czas publikacji potomka**, nie niezweryfikowany zegar autora commita. Obecność starego player-xG nie oznacza, że można go wykorzystać dla meczu, który zaczął się **przed** konserwatywną datą poświadczenia.

Ta nowa inwentaryzacja dotyczy **plików źródłowych**, nie jest licznikiem kolejnych kwalifikowanych spotkań. Po oryginalnym, odrębnym [teście pełnej rekonstrukcji i powiązania do natywnych IDs](../data/audits/STEP14_FPL74_TRAIN_ASOF_xG_RESEARCH_SUMMARY_2026-10-29.json) mamy **54/760 TRAIN** z historycznym FORM5 i **31/760** z pełnym historycznym `FPL/Opta player-sum xG5`; bez dodatkowego zwiększenia liczby kwalifikowanych wierszy. W VALIDATION pozostaje **109/380 FORM5** i **107/380 alternatywnego xG5**.

**56 poprawnych źródeł != 56 meczów z xG5**, gdyż potrzebne są jeszcze konkretne dziesięć poprzednich spotkań, kompletność obu stron i historyczny świadek opublikowany przed targetowym kickoffem. Wymagane oryginalne `PitchAPI team-xG first_published_at` i równoważność semantyczna nie są udowodnione.

Raport z odrębnym SHA, liczbą historycznych zakończonych spotkań, obecnością player-xG, SHA pliku, liczbą wierszy i błędami dla każdej z 74 rewizji:
[STEP14_ALL_74_2023_2025_FPL_REVISIONS_PLAYER_XG_2026-10-29.json](../data/audits/STEP14_ALL_74_2023_2025_FPL_REVISIONS_PLAYER_XG_2026-10-29.json).

**GATE14 = PENDING, 13/29**, oryginalny CatBoost M1 nie był fitowany, żadnego treningu na badawczym xG, brak TEST 2026/27, nowych kosztów, szyfrowania lub zmiany oryginalnego modelu.
