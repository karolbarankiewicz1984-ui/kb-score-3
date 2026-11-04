# KB Score 3.0 — odzyskanie historycznych źródeł i niezależny CatBoost retrospektywny (04.11.2026)

**Polecenie użytkownika:** zbadać możliwości odzyskania archiwalnych snapshotów sprzed meczu i równolegle **wykonać** osobne badawcze trenowanie CatBoost, z wpisem do rejestru.

## 1. Sprawdzanie archiwów — bez powielania starych prac

- Narzędzie: `scripts/kb3_p1_archived_source_recovery_audit.py`; nie uruchamia sieci/API, tylko sprawdza już zachowane źródła i rzeczywiste historyczne repozytoryjne SQLite. Dotychczasowa praca Step14 znalazła **13** niezależnie datowanych dawnych źródeł FPL/OpenFootball w trzech sezonach oryginalnego angielskiego scope, co pozwoliło odtworzyć publiczne `form5` dla **106** meczów w tamtym zbiorze. Późniejszy osobny audyt znalazł **25** potwierdzonych dawnych wersji publicznego zbioru FPL-Core dla 2025/26, w tym **109** przypadków pełnej publicznej form5 i **107** par alternatywnego xG5. Zbiory i rewizje mogą się pokrywać; **nie sumować 13 + 25** jako niezależnych nowych rekordów modelu.
- Materiał historyczny FPL/Opta i OpenFootball ma **inne źródło, definicję xG i zakres angielski** niż obecne osiem lig narodowych. Nie uznawać 106/109/107 jako certyfikowanego PitchAPI PIT, nie używać do chronionego ENG TEST 2026/27. Kod jedynie odczytuje istniejące jawne raporty zagregowane, bez pobierania oryginalnych historycznych źródeł z Internetu.
- `observations.sqlite` zawiera 1525 realnych historycznych rekordów statystycznych, 1520 w ośmiu ligach i 5 izolowanych UCL. Historyczne pola pierwszej publikacji oryginalnego PitchAPI pozostają NULL. Audyt kontroluje również, czy archiwalne źródło nie było obserwowane przed cutoff celu. **Nie pobiera ani nie fabrykuje** brakującego dawniej archiwum.
- Wynik to oddzielne zestawienie tego, co zostało naprawdę znalezione i wcześniej poświadczone, oraz **braku materiału poświadczającego pełny native v2 TRAIN** w aktualnie przejrzanej puli. Nie utożsamiać dowodu braku wewnątrz sprawdzanych plików z dowodem, że inny archiwalny dostawca nie ma takich danych.

## 2. Prawdziwy, całkowicie niezależny model eksperymentalny

- `scripts/kb3_p1_retro_catboost_1007_376.py` odczytuje aktualny rzeczywisty historyczny SQLite w trybie read-only, wykorzystuje **dokładnie 1007** wcześniej chronologicznie przydzielonych badawczych TRAIN i **376** VALIDATION, rozdzielone 7-dniowym embargo. Nie obejmuje ENG, UCL ani 2026/27.
- **Bardzo ważne:** liczy cechy z autentycznych ostatnich pięciu poprzednich spotkań (goals for/against, points, four core stats i opcjonalne xG) przed **HIPOTETYCZNYM** cutoff = kickoff−2h z heurystyką zakończenia poprzednika +3h. Źródłowe historyczne statystyki były jednak pobrane później; ten eksperyment pozostaje `HISTORICAL_RECONSTRUCTED_NOT_ORIGINAL_PIT`. Nie jest formalnym wytrenowaniem kontraktu v2, nie dowodzi faktycznej skuteczności prognozy zamrożonej przed meczem. Zero imputacji brakujących core/xG: tylko CatBoost NaN/MIN.
- Dwa **nowe osobne** modele CatBoost, każdy na dokładnie tych samych 1007 TRAIN i 376 VAL: `CATBOOST_RESEARCH_NO_XG` (14 cech), `CATBOOST_RESEARCH_PLUS_XG_WITH_MISSING` (18 cech). Stałe hiperparametry `iterations=180, depth=3, learning_rate=0.035, l2_leaf_reg=8, seed=20261104` bez strojenia na walidacji. Porównanie z prostą stałą częstością 1/X/2 wyliczoną wyłącznie z TRAIN. Poprawna kolejność etykiet, Brier sum3, log loss, top1 accuracy, ECE, metryki per liga i delty na tych samych meczach oraz bootstrap wg tygodni.
- **Etykieta celu** pochodzi z wyniku meczu dopiero po zbudowaniu cech z wcześniejszych fixture IDs; nie jest cechą modelu. Dawny `M1_R_BASE_CATBOOST_720_TRAIN...` nie jest nadpisany lub podłączony. Obecny M0 Elo+Poisson, FIT100/HOLDOUT50, GATE16/GATE17 pozostają bez zmian.
- Dwa badawcze binaria `.cbm` i zagregowany raport JSON trafiają jedynie do prywatnego artefaktu GitHub Actions przez 14 dni; **bez publikowania prognoz lub etykiet per fixture, bez dołączania do dziennego modelu**.

## 3. Odbiór i następne decyzje

Workflow `.github/workflows/kb3-p1-retro-catboost-and-archive-recovery.yml` na osobnej gałęzi (zależnej od roboczych PR #151 i #152) wykonuje realny archiwalny audyt i dwa rzeczywiste fity CatBoost w ramach testu, przy użyciu przypiętego pakietu CatBoost 1.2.8. Sprawdza liczby 1007/376, izolację TEST i brak zmiany działającego M0. Wydatki na provider API: 0; klucze prywatne i RSA: niewymagane.

**STATUS PRZED WYKONANIEM CI:** tylko implementacja. Podać prawdziwe wyniki, SHA i link do zakończonego runu w tym dokumencie oraz w `docs/ZMIANY.md`. Brak PASS w razie nieudanych testów.

**Kolejny cel:** w razie braku historycznych źródeł *nie odblokowywać formalnego v2*, a eksperymentalne wagi traktować wyłącznie jako źródło hipotez do testowania na autentycznie zamrożonych przyszłych prognozach. Wymagane osobne przyszłe sparowane porównania jakości M0/Elo/CatBoost i niezależny odbiór GATE16/GATE17.
