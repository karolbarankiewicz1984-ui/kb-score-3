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

## Wyniki rzeczywiście wykonanego eksperymentu — 04.11.2026

- **GitHub Actions:** [run #41915259711](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/41915259711) `completed / SUCCESS`, testy 5/5 i 7/7 PASS, dwie rzeczywiste sesje `CatBoostClassifier.fit`, obie zakończone, kontrole braku modyfikacji M0/danych i ochrony GATE PASS. Testowany SHA `73651676f15ab3a3cccfa70ce06b4510f35d1ea2`.
- **Artefakt:** [KB3_RESEARCH_RETRO_CATBOOST_PRIVATE_NO_PIT](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/41915259711/artifacts/13363568307) (ID `13363568307`), prywatny, datowany, z dwoma faktycznymi plikami `.cbm`, jednym raportem JSON i raportem źródeł. Retencja do **18.11.2026** wg metadanych Actions; nie są wdrożone ani wczytywane przez M0.
- **Archiwalne źródła:** stare 13 publicznych witness (oryginalne trzy sezony ENG) i 25 późniejszych publicznych wersji FPL-Core, **109** publicznych form5 target, niecertyfikowane native osiem lig. Audyt 1525 historycznych obserwacji (1520 krajowych) wykazał **0** `provider_first_published_at_utc`, **0** `original_provider_first_published_utc`, **0** dat źródłowego target-stats sprzed kickoff-90min i **0** zapisów indeksu fixture sprzed target kickoff-90min. Oryginalna historyczna baza nie jest dostępna jako dawne as-of; NIE oznacza to, że światowe archiwa takich źródeł nie mają. Archiwalny raport SHA `d2efc93969717699d362e099dd5c56917812d44cb5a83e535412fc8a109e823c`.
- **Oba rzeczywiście wytrenowane warianty** wykorzystały ten sam `1007 TRAIN / 376 VALIDATION` z siedmiodniowym embargo; wersja bez xG 14 cech, z xG 18 cech i brakami jako NaN. Kontrolna liczba próbek **N=376** w obu wynikach. To zupełnie nowe, odrębne CBM, bez nadpisywania dawnego M1-R 85 cech.
- **Bez xG:** `Brier sum3=0.6410348466`, `log loss=1.0629033841`, `top1=0.4414893617`, `ECE10=0.0227643078`.
- **Z xG:** `Brier sum3=0.6445418321`, `log loss=1.0686233758`, `top1=0.4228723404`, `ECE10=0.0517653486`.
- **Różnice z xG minus bez xG na tych samych meczach**: `Brier +0.003506986`, `log loss +0.005719992`, `top1 -0.018617021`. Bootstrap według tygodni (7 bloków, 600 replik): 95% CI dla różnicy log loss `[+0.00017501,+0.01318195]` (w tym teście wskazuje gorszy wariant z xG), Brier `[-0.00022939,+0.00891505]` (obejmuje zero, niejednoznaczne). Nie wykazano przewagi xG. Nie wnioskować automatycznie o jego bezużyteczności; braki publikacji i kompletności są istotne.
- **Raport z treningu SHA:** `3b371bdb0d6ccfe95851d7ca27174f0ddfd27786b168f7233cd213c6b4a9e525`. Metryki 1X2, Brier, log loss, ECE i osobne wyniki per liga oraz SHA obu modeli są w rzeczywistym JSON w artefakcie. Nie wyprowadzano żadnych typów bukmacherskich ani prognoz dla przyszłych meczów.
- **Bramki formalne:** historyczny native v2 TRAIN `0` certyfikowanych, research TRAIN 1007 i validation 376 **nie zwiększają FIT**, `GATE16=PENDING`, `GATE17=PENDING`, P1-01 PARTIAL, PR #151/#152/#153 DRAFT. Bez połączenia z produkcyjnym generatorem M0 i bez porównania prospektywnego na wspólnych meczach.

### Decyzja po wyniku

Zachować oba binaria tylko jako oddzielne artefakty RESEARCH; w obecnym materiale **nie dodawać historycznego xG do modelu docelowego na podstawie tego testu**. Kontynuować rzeczywiste zbieranie zamrożonych przedmeczowych danych i porównać poprawiony CatBoost z M0 dopiero na prawdziwych, sparowanych przyszłych meczach. Nie zastępować historii formalnej danych pochodzących z FPL/Opta pod zmienioną etykietą PitchAPI.
