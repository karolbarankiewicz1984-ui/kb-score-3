# KB Score 3.0 — audyt CatBoost i niezależny wariant as-of v3, 09.11.2026

Status: **naprawy techniczne i pipeline badawczy; nowy rzeczywisty model NOT_TRAINED**.
Brak dopuszczonego zbioru v3 jest blokadą danych, nie powodem odkładania kodu/testów do 150 próbek.
M0, Champion, TEST Premier League i harmonogramy nie zostały zmienione. Nie wykonano płatnych API calls, nowych rzeczywistych prognoz, backfillu prognoz ani produkcyjnego fitu.

## Audyt istniejących wersji

| Obszar | M0 / Elo-only forward | M1-R BASE 85 | Shadow Six | Nowy wariant v3 |
|---|---|---|---|---|
| Wagi i źródło | M0 720 TRAIN Elo+Poisson; Elo-only stały draw prior 168/720 | osobny CBM, 720 TRAIN / 374 VALIDATION, 85 zmiennych wybranych wyłącznie na TRAIN | osobny CBM, 1007/376 odtworzonej historii, 6 średnich last5 | osobny identyfikator, stałe 87 kolumn przed selekcją danych, brak rzeczywistego CBM |
| Selekcja wyniku poprzednika | status finished + kickoff+3h przed obserwacją źródła | historyczny release kickoff+48h, nie czas rzeczywistej publikacji | historia kickoff celu−2h−3h; forward jak M0 | rzeczywisty observed/captured/host receipt <= cutoff, minimalne 3h; brak certyfikacji przez sam lag |
| Zegar dni od poprzednika | cutoff−kickoff poprzednika | kickoff celu−kickoff poprzednika | brak takiej kolumny | cutoff, wspólne TRAIN/FORWARD |
| Okna | Step11 5/10/15, all i venue, poprzedni + bieżący sezon w strumieniu M0 | osobny replay historii; nie identyczny selektor forward | pełne 5/5, gole/punkty; bez Elo/xG | jedna funkcja shared v2, te same dostarczone źródła/sezony; nie zmieniać zestawu źródeł między TRAIN i FORWARD |
| Braki | Step11 null + maski; częściowe średnie i liczności | null→NaN, oryginalna zamrożona lista kolumn | brak pełnych 5/5 blokuje scoring | jawne null→NaN/Min; 14 masek boolean→0/1, 73 numeric, bez imputacji zerem |
| xG / pozostałe statystyki | M0 forward nie pobiera shots/stats; xG null | BASE bez xG; nie dokładać missing xG do innego modelu | tylko gole i punkty, brak shots/fouls/corners/xG | bez xG; nie przyjmuje wartości/receiptów xG |
| Dostępność PIT | bieżące zamrożenia; pierwotna publikacja dostawcy nieznana | odtworzone historyczne wejścia nie są oryginalnym PIT | trening odtworzony; 23 rzeczywiste forward freeze | dokładne bajty wejścia i natywnych odpowiedzi w niezależnym archiwum przed cutoff; pierwszy provider published_at nadal nieznany |

**Wniosek:** równe nazwy i kolejność 85 kolumn nie dowodzą parytetu M1-R. Zmiana samego laga albo podanie wartości v2 do starych wag nie naprawia rozkładu treningowego. Stare CBM/parametry zostają niezmienne, historyczne wyniki zachowują kwalifikację research. M1-R forward można mierzyć empirycznie jako tę samą starą wersję, z jawną wadą semantyki; nie uzyskuje przez to zgodności TRAIN/FORWARD.

Przeczytano ADR, PLAN, ZMIANY, dokumentację shared v2/Shadow Six, audyty M1-R, manifest pinned Six i istniejące testy. Wykorzystano istniejące `_compose_features`, `feature_clock_map`, GitHub archive clients, `score_predictions` i `paired_ci`; nie tworzono drugiego Elo, agregatora formy, kalibratora ani kolektora API.

## Naprawy mechanizmów

1. `scripts/kb3_catboost_feature_semantics_gate.py`: wersja diagnostyki v2 sprawdza prawdziwy format SHA256, treść kontraktu, obydwa manifesty, ich kanoniczne SHA oraz skończony nieujemny lag. Tekst `verified-contract`, same flagi i równe nieskończoności nie przechodzą. Przy zgodnym lagu nie raportuje fikcyjnej przyczyny 48h/3h. To nadal **diagnostyka metadanych, nie certyfikat źródłowych bajtów**; Champion zawsze false.
2. Shared as-of v2: ścisłe UTC, tożsamość drużyn, aliasy `123`/`"123"`, dodatkowe etykiety celu, publikacja/capture celu po cutoff, aktualizacja wyniku po obserwacji. Dostępność xG i missing xG uwzględnia zakończenie capture. Elo otrzymuje konserwatywny lineage wszystkich zaakceptowanych wyników (zależności przeciwników). Bez zmian `_compose_features` ani mappera używanego przez M0.
3. `contracts/kb3_catboost_asof_v3.json`: jedna uporządkowana lista 87 pól, jednostki, definicje, null/maski, zegary, parametry Elo i SHA implementacji. Kanoniczny kontrakt SHA256: **`0c4347e58af678f44a1ca7ad042633b8825be885f3225dbed669a8896ba33eca`**. Zmiana kodu buildera, bazowego Step11 lub mappera bez nowego kontraktu blokuje pipeline.
4. `src/kb3_catboost_research_v3.py`: ten sam builder i adapter kolumn w fit/shadow. Weryfikator pobiera niezależne metadane GitHub, kontroluje SHA ZIP i dokładnego membera, zgodność oryginalnych `matches` z ID/czasem/drużynami/wynikiem, oraz host-created time przed cutoff. Obserwacja po historycznym cutoff nie zostaje cofnięta w czasie. Obsługuje cache artefaktów i wyłącznie istniejący token GitHub; nie wywołuje PitchAPI.
5. Chronologiczny TRAIN/VALIDATION i osobna rezerwacja HOLDOUT, embargo >=7 dni, bez duplikatów i ENG. Wszystkie etykiety TRAIN i ich dowody muszą istnieć przed train_end i pierwszym validation cutoff. HOLDOUT nie jest przyjmowany przez fit. Brak eval_set, early stopping, skalowania lub selekcji kolumn na VALIDATION. Parametry stałe: 180, depth3, lr .035, L2=8, seed20261109, CPU1, CatBoost1.2.8. Walidacja fitu daje tylko metryki retrospektywne, **nie zamrożone prognozy forward**.
6. Manifest nowej wersji zapisuje datę rzeczywistego fitu, SHA kodu/kontraktu/modelu/źródeł/selekcji, parametry, nazwy i klasy. Loader wymaga znanego SHA manifestu i identycznego CBM. Model version `KB3_CATBOOST_SHARED_ASOF_87_RESEARCH_V3`. Zapis do nowego katalogu; zakaz nadpisywania.
7. Shadow działa jedynie na NOWEJ migawce z rzeczywistym cutoff i zegarem, <kickoff−90min i <=45min po cutoff. Zwraca kandydata bez poświadczenia; exact output musi dostać niezależne archiwum przed kickoff−90min. Evaluator HOLDOUT czyta wyłącznie takie stare zamrożone bajty, nie wykonuje `predict_proba` wstecz. Osobny adapter włącza przyszłe prawdziwe v3 do wspólnego porównania. Nie podłączono niczego do harmonogramu M0.

## Potwierdzone źródła i blokada treningu

Odtworzono istniejącą kompresję historycznej bazy zgodnie z oryginalnym manifestem, bez zmiany `.gz`. SQLite raw SHA `ccf7bce286323b0c4b6cd37b6c2547549b90750a5508ab9fea22cb9d99e22d69`, integralność ok. Tabele: **8710** finished fixture index, **4401** observations, **4401** rolling feature cache. **4401/4401** obserwacji i **8710/8710** listingów zapisano po kickoff celu, provider first-published **0/4401**. Późniejszy odczyt nadal może zasilać przyszły mecz, ale nie dowodzi starych danych przedmeczowych.

Dopuszczonych dostarczonych kompletów dowodowych nowego v3: **0**. Nie wykonano nowego fitu na tych realnych danych. Same syntetyczne fit/shadow w testach nie są modelem badawczym do oceny jakości ani nowymi rzeczywistymi prognozami. Nie uzupełniono historii wynikami symulowanymi.

Dalsze dane: autentyczne, archiwizowane przed cutoff wejście as-of v2 i natywne response bytes, rozliczenia po meczach, oddzielne TRAIN/VALIDATION oraz przyszły HOLDOUT. **Nie ma ogólnego progu 150 gwarantującego poprawny fit 87 cech**. Potrzebna liczność i zróżnicowanie lig/tygodni zależą od krzywych uczenia i niepewności; nie obniżono istniejących warunków 100 par / 8 tygodni ani niezależnego procesu kalibracji 100+50.

## Rzeczywiste porównanie na wspólnych meczach

Źródło: run [42547104765](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/42547104765), artifact **13643613735**, server-created **2026-11-09T01:45:39Z**. Pobranie przez GitHub plugin; SHA całego ZIP niezależnie wyliczone i zgodne z metadanymi GitHub: `668e06146599dd8bb25256776ba15704f1b94d7288169a5240bc07c77adc6482`. Wyodrębniono tylko eight-league DB, nie TEST.

Oryginalna SQLite SHA `cd0a203ff1bf1ea39b035c18c4dc94b86ef436154d93c66d67bd73061583e447`: 149 M0 forecast, 147 settlements, 152 challenger rows/proofs, **23 Six rows i 23 Six proofs**. `integrity_check=ok`, `foreign_key_check=[]`. Sprawdzono hashe prognoz/rozliczeń/poświadczeń, powiązania rodziców i granice czasu. Adapter korzysta z zachowanych audytów host-original-bytes; nie ogłasza nowej certyfikacji pierwszej publikacji dostawcy.

**Poniżej dokładnie te same 23 spotkania dla czterech modeli**, identyczny cutoff źródłowy. Nie zestawiamy z nimi marginalnego wyniku 147 M0 lub 74 M1-R/Elo-only.

| Model / osobna wersja | N wspólnych | Trafienia / accuracy | Brier sum3 ↓ | Log loss ↓ | Top1 ECE10 ↓ |
|---|---:|---:|---:|---:|---:|
| M0 720TRAIN V1 | 23 | 14/23 = 60.87% | 0.5621912012 | 0.9516386707 | 0.1755385582 |
| Elo-only TRAIN720 DRAW V1 | 23 | 14/23 = 60.87% | 0.5472110380 | 0.9313427674 | 0.0996410302 |
| CatBoost M1-R 85 TRAIN720 V1 | 23 | 15/23 = 65.22% | 0.5405967812 | 0.9132796791 | 0.1488946316 |
| CatBoost Shadow Six V1 | 23 | 15/23 = 65.22% | 0.5599529955 | 0.9449020152 | 0.1976834490 |
| Nowy CatBoost as-of87 v3 | 0 | NOT_TRAINED | — | — | — |

Shadow Six−M0: accuracy **+4.35 pp**, Brier **−0.0022382058**, log loss **−0.0067366554**, ECE **+0.0221448908** (gorsza kalibracja top1). To wyniki opisowe; mała przewaga loss nie jest dowodem poprawy.

Wszystkie 23 i odrębna para 74 należą do **jednego ISO-tygodnia**. Istniejący paired whole-week bootstrap zachowuje zależne spotkania w bloku i oblicza CI dopiero przy >=8 tygodniach. Obecnie **CI95=null, INSUFFICIENT_INDEPENDENT_WEEKS**. Nie zastąpiono tego fałszywie wąskim bootstrapem IID. Także 8 tygodni nie gwarantuje niezależności między tygodniami/drużynami. Nie wybieramy Championa ani zwycięzcy nowego modelu.

[Raport JSON](../reports/KB3_CATBOOST_V3_FORWARD_COMPARISON_2026-11-09.json) zawiera każde przecięcie parami, osobne SHA kohort, różnice trzech metryk, niezależne liczniki pokrycia, wyniki wszystkich lig i kalibrację top1 oraz każdej klasy. Zakres wspólnych lig: BEL3, ESP4, FRA5, GER2, ITA2, NED3, POL2, TUR2. Wszystkie 5 modeli: wspólnych 0; cztery dostępne: 23. Dołączenie nowego wymaga rzeczywistego fitu i nowych zamrożeń; brak generowania zaległych prognoz.

## Uruchomienie i rollback

```bash
python -m scripts.kb3_catboost_research_v3 readiness
python -m scripts.kb3_catboost_research_v3 fit --samples admitted-train-validation.json --plan split-plan.json --output NEW_MODEL_DIR
python -m scripts.kb3_catboost_research_v3 shadow --samples NEW_SAMPLE.json --model-dir NEW_MODEL_DIR --manifest-sha256 PINNED_SHA --output NEW_CANDIDATE.json
python -m scripts.kb3_catboost_research_v3 holdout --samples FROZEN_HOLDOUT.json --model-dir NEW_MODEL_DIR --manifest-sha256 PINNED_SHA --output NEW_REVIEW.json
python -m scripts.kb3_compare_frozen_models_v3 --db OFFLINE_EIGHT_LEAGUE_SNAPSHOT.sqlite --output NEW_REPORT.json
```

Oprócz readiness wymagany jest istniejący `GITHUB_TOKEN` do odczytu dowodów. Nigdy token dostawcy. `--samples` fit to lista obiektów: `input` (dokładne argumenty `build_shared_features` bez purpose), `input_archive`, `source_archives` (mapa source_sha256→ref), osobne `label`. Ref: `{artifact_id, member, sha256}`. Label: `{outcome_1x2, observed_utc, archive}` z natywną odpowiedzią `matches`. Shadow przyjmuje jeden taki obiekt (bez potrzeby etykiety). HOLDOUT: lista `{target, forecast_archive, label}`; źródłowy forecast musi już istnieć w hostowanym archiwum sprzed meczu. Plan: `train_end_utc`, `validation_start_utc`, `validation_end_utc`, `holdout_start_utc`, UTC Z, odstępy >=7 dni. Przykład struktury i negatywne scenariusze w `tests/test_kb3_catboost_research_v3.py` są wyłącznie syntetyczne.

CLI comparison obsługuje opcjonalnie `--v3-frozen-samples`, `--v3-model-dir`, `--v3-manifest-sha256`, sprawdzając oryginalne bajty prognozy i jej host clock przed dołączeniem do raportu. Żaden evaluator nie tworzy zaległej prognozy.

Wdrożenie jest odwracalne: osobna gałąź, osobny katalog wyjściowy, zero migracji lub zmian danych M0; usunięcie/wycofanie nowego kodu nie zmienia istniejącego modelu i ledgeru. Nie ma automatycznego uruchomienia fitu, live czy produkcji. Nowy workflow to offline testy, bez sekretów/provider APIs, Python3.11/3.12; jego rzeczywisty wynik CI jest zapisywany osobno po odczycie.

## Walidacja i rejestr zadań

Wyniki, commity i dalsze blokady są dopisywane do istniejącego [ZMIANY](ZMIANY.md) i centralnego Google Docs. Pierwsza próba testów: 1283, FAIL (brak lokalnego CatBoost i nierozpakowana baza gzip); po instalacji przypiętego CatBoost1.2.8 oraz odtworzeniu oryginalnego SHA bazy istniejące 1296: PASS, 2 skip. Pełny run po naprawach: 1320 PASS, 2 skip; po ostatnim teście aliasów i zmianach adaptera finalny wynik oraz commit w rejestrze. Nie sumować nakładających się zestawów.

[Audyt SQLite](../reports/KB3_CATBOOST_V3_SQLITE_IMMUTABILITY_2026-11-09.json): na jednorazowej kopii odrzucono **14/14 UPDATE/DELETE** siedmiu zamrożonych tabel, w tym Six/proofs; oryginał SHA bez zmian. Dodatkowo porównano **1240 istniejących plików** data/models/assets/configured workflows oraz M0/Step11 z SHA sprzed prac — bez zmian. [Inwentaryzacja historii](../reports/KB3_CATBOOST_V3_SOURCE_INVENTORY_2026-11-09.json).

Ocena końcowa jakości nowego CatBoost: **NIE USTALONO POPRAWY — brak dopuszczonego rzeczywistego fitu i prospektywnych prognoz v3**. GATE16/GATE17 PENDING, formalne 15/29 bez zmiany.

### Odczyt końcowy

Końcowy kod: `d73ecb7c23ac4c13f84881d957fa089692416456`, poprawka offline CI `cff070729eb997ee690e052135aa6bf9fe85a2f0`; [DRAFT PR167](https://github.com/karolbarankiewicz1984-ui/kb-score-3/pull/167). Ostateczny pełny run: **1340/1340 PASS, bez skip**, 72.633s, z istniejącym pinned Shadow Six. Nowy plik [protokołu walidacji](../reports/KB3_CATBOOST_V3_VALIDATION_2026-11-09.json) wiąże liczności, log SHA, kod i Actions.

GitHub Actions na cff0707: v3 [42563988180](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/42563988180), shared v2 [42563988104](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/42563988104), history [42563988092](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/42563988092), derived read-only [42563988068](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/42563988068) — **wszystkie SUCCESS**. Pierwszy history run42563837258 FAIL z powodu braku raw SQLite został naprawiony przez odtworzenie oryginalnego gzip z kontrolą raw/compressed SHA, wielkości i integralności; nowy helper `scripts/kb3_restore_history_snapshot.py` oraz 3 testy nie zmieniają historii ani harmonogramu. Do samodzielnego odtworzenia pełnego lokalnego testu najpierw: `python -m scripts.kb3_restore_history_snapshot --source data/research/historical_multistat/observations.sqlite.gz`, potem ustawienie `KB3_SHADOW_SIX_MODEL_DIR=assets/research/kb3_shadow_six_v1` i `python -m unittest discover -s tests`.

Ostateczna kontrola 1240 wcześniej zahashowanych plików: **1239 identycznych**; zamierzony wyjątek to `.github/workflows/kb3-p1-historical-eligibility-v2-offline.yml` (naprawa offline CI). Żaden produkcyjny workflow M0, dane, modele lub parametry nie zmieniły się. Stan modelu v3 nadal **NOT_TRAINED**, brak twierdzenia o poprawie jakości.


## Kontynuacja — kwalifikacja danych historycznych (2026-11-09)

Przeprowadzono przegląd zapisanej inwentaryzacji historycznej SQLite i ograniczeń nowego v3. Zidentyfikowano istotne rozróżnienie: **obserwacja historycznego spotkania po jego własnym kickoff może być prawidłowym źródłem cechy dla późniejszego meczu, o ile istnieje niezależny dowód jej dostępności przed cutoff tego późniejszego meczu**. Dlatego 4401 późnych względem własnego meczu obserwacji nie wolno ani automatycznie dopuścić, ani bezwarunkowo odrzucić jako potencjalnych poprzedników.

Zapisano `scripts/kb3_catboost_v3_eligibility_triage.py` (commit `7188e05`) i cztery testy `tests/test_kb3_catboost_v3_eligibility_triage.py` (commit `6c8f84c`). Raport diagnostyczny wskazuje brak formalnie dopuszczonych zestawów v3, wymagane dowody per docelowy mecz, i pozostawia realny trening zablokowany. Dopuszczono jedynie opisowe, odizolowane eksperymenty offline bez uznawania ich za rzeczywisty PIT, wyniki forward lub gotowy model.

**Status:** kod i testy zapisane na gałęzi `research/catboost-contract-v3`; CI tych nowych testów jeszcze niepotwierdzone. Nie uruchomiono fitu, nie stworzono fałszywych próbek, nie zmieniono M0 ani harmonogramów. Następny krok: zestawić istniejące host-archived obserwacje i natywne odpowiedzi źródłowe względem cutoff konkretnych późniejszych meczów; dopiero rzeczywiste dowody pozwalają zwiększyć formalne admitted rows. Osobny eksperyment offline może porównywać metodologię, ale nie może udawać zweryfikowanej skuteczności prospektywnej.


## Kontynuacja — rzeczywiste metadane archiwów GitHub (2026-11-09)

Sprawdzono przez GitHub Actions API rzeczywiste artefakty: historyczny PitchAPI run42528150426 artifact13635728620, server-created 2026-11-08T22:08:22Z, 55,971,610 bytes; M0 eight-league run42547104765 artifact13643613735, created 2026-11-09T01:45:39Z, 3,218,260 bytes; eligibility audit run42566663555 artifact13651572943, created 2026-11-09T05:20:12Z, 66,591 bytes. Wszystkie raportowane jako not expired. **Są to dowody istnienia archiwów, nie potwierdzenie dostępności każdej statystyki dla wcześniejszego historycznego target cutoff.**

Nowy read-only `scripts/kb3_catboost_v3_archive_cutoff_audit.py` (commit e8d3aaf) umożliwia filtrowanie metadanych archiwum per target fixture/cutoff; odrzuca artefakty późniejsze od cutoff lub wygasłe, ale nawet starszych NIE dopuszcza do formalnego treningu bez walidacji oryginalnych bajtów i zegarów. Cztery testy w `tests/test_kb3_catboost_v3_archive_cutoff_audit.py` (commit 9d271cc). Brak nowych API dostawcy i brak zmian w M0.

**Granica wykonania:** nie pobrano w tym etapie pełnych ZIP/native payload do mapowania na konkretne późniejsze mecze. Dlatego nie zgłoszono ani jednej nowej dopuszczonej próbki; nie przeprowadzono fitu. Testy nowego modułu zapisane, CI po tych commitach jeszcze niepotwierdzone. Dalszy krok to wyciągnięcie rzeczywistych `fixture_id`, cutoff, ZIP/member SHA i native provider observed/captured timestamps z artefaktów, a następnie wywołanie weryfikatora v3 na parach (target, archived source); dopiero pozytywne pary można kwalifikować. Oddzielnie utrzymać izolowany eksperyment retrospektywny jako NIE-CERTYFIKOWANY PIT.


## Weryfikacja oryginalnych ZIP i SQLite — 2026-11-09

Pobrano rzeczywiste ZIP `13635728620` (historyczny) i `13643613735` (M0) i odczytano źródłowe SQLite. Wynik: **4401** historycznych obserwacji, **149** zamrożonych prognoz, **74** prognozy z co najmniej jednym poprzednikiem tej samej ligi zaobserwowanym przed cutoff i dojrzałym +3h; **10858** potencjalnych par (nie 10858 próbek TRAIN). ZIP historyczny utworzono dopiero po wszystkich badanych cutoff, dlatego **0** nowych formalnie dopuszczonych rekordów v3. Dokładne SHA, zakresy i przykłady: [raport rzeczywistych archiwów](../reports/KB3_CATBOOST_V3_REAL_ARCHIVE_OBSERVATION_AUDIT_2026-11-09.md), commit `4975323`. Następny krok: starsze niezależnie datowane ZIP/native response, team-specific last5 i pełna walidacja źródła. Bez treningu i zmian M0.
