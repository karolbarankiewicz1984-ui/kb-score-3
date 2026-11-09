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


## Weryfikacja starszych archiwów 2–5 listopada

Odnaleziono sześć konkretnych starszych hostowanych artefaktów GitHub; rzeczywiście pobrano ZIP `13238225342` utworzony 2026-11-03T14:13:32Z. Potwierdzono SHA-256 **3/3** zaszyfrowanych źródeł 29.10, 01.11, 03.11 wobec ich manifestów. Archiwum zawiera także forward M0 SQLite i zamrożone JSON. Manifesty wprost stwierdzają `training_allowed=false`, `provider_publication_proven=false`, `offsite_restore_verified=false`; bez odszyfrowania i host-timing konkretnego cutoff nie certyfikować PIT. **0 nowych admitted v3**. Pełne IDs, SHA i blokady: [raport](../reports/KB3_CATBOOST_V3_EARLY_GITHUB_ARCHIVES_2026-11-09.md), commit `9e2aa97`. Żadnych zmian M0/Champion/TEST.


## Zamknięcie audytu starszego SQLite (2026-11-09)

Zakończono rzeczywisty odczyt `forward_m0/kb3_forward_m0.sqlite` z ZIP artifact13238225342, SHA ZIP i SQLite zweryfikowane, integralność OK. **27** prognoz ESP10/GER6/ITA11, **21** rozliczeń, **18/18** źródeł bez czasu pierwszej publikacji, **0/27** cech eligible for original M1, **18/18** snapshotów `NOT_VERIFIED`. Wszystkie 3 szyfrogramy SHA zgodne, ale manifesty `training_allowed=false`. Wobec braku natywnych odszyfrowanych danych i niezależnego PIT **0** nowych v3 TRAIN, `NOT_TRAINED`. [Końcowy audyt](../reports/KB3_CATBOOST_V3_EARLY_SQLITE_FINAL_AUDIT_2026-11-09.md), commit `e4f3948`. Dalsze przeliczanie tej samej niecertyfikowanej historii nie odblokuje formalnego treningu; kontynuować prospektywne archiwizowanie albo osobny jawnie retrospektywny eksperyment.


## Rzeczywisty trening eksperymentalny — 20 cech, NIE v3 87 (09.11)

Na prawdziwym historycznym SQLite z artifact13635728620 lokalnie wykonano `CatBoostClassifier.fit`: 2845 TRAIN / 747 chronologicznie odseparowanych VAL, embargo 7 dni, 20 cech last5, bez xG. Wynik: accuracy 0.4484605, Brier 0.6371830, log loss 1.0556964; baseline TRAIN-frequency odpowiednio 0.4457831 / 0.6466204 / 1.0694436. Faktyczny model CBM SHA256 `c0c85b5d19b0026ff65b341123c0b687a7f4737ee8ebbf36f01d1e35e5e3b64d` w lokalnym eksperymencie, bez wdrożenia i bez uploadu CBM do repo. **Nie jest to model kontraktu 87 cech, ani PIT; nie używać tych metryk do promocji Championa.** Szczegóły: [raport](../reports/KB3_CATBOOST_RETRO_20_REAL_FIT_2026-11-09.md), commit `6cce975`.


## Eksperymentalny retrospektywny fit 87 cech (2026-11-09)

Wykonano lokalny rzeczywisty fit CatBoost z 87 nazwami/oknami/semantyką kontraktu na 2845 TRAIN i 747 VAL. Sprawdzono **identyczność identyfikatorów** wszystkich spotkań względem poprzedniego modelu 20 cech: 2845/2845 TRAIN i 747/747 VAL, zero różnic. Wynik 87: top1 **48.8621%**, Brier **0.620123**, log loss **1.030482**; 20: 44.8461%, 0.637183, 1.055696. Uwaga: cechy 87 zostały odtworzone osobnym kodem retrospektywnym, **nie jest to oryginalny builder verified v3**, dane nie mają certyfikacji PIT, brak prospektywnych prognoz 87. Model CBM istnieje lokalnie, nie jest w produkcji. [Raport](../reports/KB3_CATBOOST_RETRO_87_REAL_FIT_2026-11-09.md), commit `c90030e`.


## Końcowy parowany audyt eksperymentu 20 vs 87 (09.11)

Rzeczywiście ponownie uruchomiono oba skrypty i zapisano prognozy na **747 identycznych** fixture+kickoff+league. Bootstrap 5000 losowań w 12 klastrach tygodniowych: poprawa 87 accuracy **+4.016 pp** (95% [2.351,5.452]), Brier reduction **0.01706** ([0.00343,0.02946]), log loss reduction **0.02521** ([0.00556,0.04301]). [Pełny raport](../reports/KB3_CATBOOST_RETRO_87_PAIRED_BOOTSTRAP_AUDIT_2026-11-09.md), commit `0947d84`. **Zamknięto etap retrospektywnego porównania**, nie formalny model v3. Wymagana jeszcze kontrola parity z oryginalnym builderem i rzeczywiste przyszłe zamrożone prognozy; Shadow nie jest uruchomiony. M0/Champion/TEST bez zmian.


## Oryginalny builder vs retrospektywny model oraz realne archiwum (09.11)

Oryginalny `build_shared_features` ma pozytywny **syntetyczny** test TRAIN/FORWARD z tym samym cutoff, run `42573117892` CI success. **Nie potwierdzono** jednak równości 87 wartości z osobnym `train_retro_87.py` — nie wywołuje oryginalnego buildera, brak źródłowych receiptów. **Nie promować** tego CBM do oficjalnego Shadow. Pobierając realny GitHub artifact `13619490089` (run `42484728241`, host-created `2026-11-08T13:23:56Z`) zweryfikowano **8 rzeczywistych rekordów M0** (ESP4 ITA2 GER2) host-archived ponad 90 min przed kickoff. Jest to prawdziwy niezależny przedmeczowy materiał, ale zaszyfrowany native payload i brak pierwszej publikacji blokują `verified_view` v3. Formalny v3 TRAIN 0, v3 Shadow 0. [Raport szczegółowy](../reports/KB3_V3_BUILDER_PARITY_AND_REAL_PREMATCH_ARCHIVE_2026-11-09.md), commit `7d73ff1`. Istniejące codzienne kolektory pozostawiono bez zmian i bez dodatkowych wywołań płatnego API.


## Uruchomiony audyt niezależnego archiwum 3 lig, bez nowych wywołań API (09.11)

**Wdrożone na branch badawczym:**
- `scripts/kb3_catboost_v3_three_league_archive_preflight.py`: fail-closed weryfikacja metadanych hosta GitHub, SHA-256 ZIP, szyfrogramu, łańcucha źródłowego, bazy SQLite, 87 pól kontraktu v3 i czasu dostępności każdego pola (commit `7eccb16`, poprawka rozmiaru rzeczywistej bazy `7b8414b`).
- `tests/test_kb3_catboost_v3_three_league_archive_preflight.py`: 5 testów syntetycznych (commit `0dbf38f`), offline CI `KB3 CatBoost v3 isolated contract and model audit` zielone Python 3.11 i 3.12.
- `.github/workflows/kb3-catboost-v3-three-league-evidence.yml`: osobny odczyt ostatniego rzeczywistego artefaktu **na serwerach GitHub**, bez PitchAPI, bez deszyfrowania i bez zmian M0/TEST (commit `4b6bdf0`). Sukces rzeczywistego run `42585396793`, wynik jako GitHub Actions artifact `13659340632` (`KB3_V3_THREE_LEAGUE_SOURCE_READINESS_NO_FIT`).

**Autentyczne wejście testowe:** source artifact `13619490089`, run `42484728241`, `2026-11-08T13:23:56Z`. GitHub API `digest=sha256:b2deda9f50c7a3244a6166303b00e91b38da57f08d350c08e8255955df9a497f` == obliczony SHA całego pobranego ZIP. Ciphertext SHA, chain SHA, sqlite SHA i 8 oryginalnych SHA zestawów cech: **wszystkie PASS**. Pełna kontrola nazw/wartości/typów oraz per-field zegarów **87/87 dla każdego z 8** rekordów (ESP 4, GER 2, ITA 2). GitHub host utworzył archive ponad 90 min przed każdym kickoff: **8/8**, minimum **111.067 min**.

**Kluczowa bariera:** GitHub host `created_at` **późniejszy niż zapisany feature_cutoff_utc** każdego z tych 8 zestawów: `0/8` spełnia ścisły wymóg `GithubArchives._archived(..., deadline=cutoff)` dla obecnych historycznych view. Nie przesuwamy starych cutoffów ani nie uznajemy tego za PIT. Raw native payload w `.enc`, bez niezależnego odszyfrowania oraz individual native response ZIP member SHA; ponadto `kb3-step11-v0.5` to **nie** oryginalny `kb3-p1-shared-train-forward-asof-v2`. Oficjalne v3 próbki i prognozy: nadal **0**.

**Decyzja i plan dopuszczania następnych danych:** przy bieżących przyszłych spotkaniach archiwum źródłowe musi powstać na serwerze GitHub **wcześniej niż cutoff prognozy**, z rzeczywistym buforem czasowym; później niezależna kontrola native `matches`, wyników poprzedników i ich timestamps z dokładnego źródła, bez wstecznego „certyfikowania” danych. Dopiero ta sama 87-cechowa ścieżka `verified_view` może dopuścić pojedynczy input. Monitoring dodany na **branch badawczy PR #167**: `pull_request` działa, `schedule: 10 8 * * *` uruchomi się cyklicznie **dopiero gdy osobny workflow znajdzie się na domyślnej gałęzi main**. W tej chwili nie twierdzić, że codzienny nowy monitor jest aktywny na main. Działające kolektory `main` bez zmian i bez dodatkowych wywołań/licencji.

[Run CI](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/42585396793) — [wynik 13659340632](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/42585396793#artifacts). Bez promocji produkcyjnej.


## Codzienny audyt archiwów uruchomiony na main — oddzielny PR #168 (09.11)

Dla uniknięcia wdrożenia wielkiego draft PR #167 do produkcji utworzono osobny, addytywny PR **#168** `research/kb3-v3-prematch-evidence-gate-20261109` → `main`, zawierający **wyłącznie** kontrakt 87 pól, czytający artefakty walidator, 5 testów syntetycznych i read-only GitHub workflow. Real-archive PR CI run **42585950797**: sukces. PR #168 merged przez `squash`, merge SHA **`5f16d8677e474b709a18afafde5ed608c7f53620`**. Harmonogram workflow na `main`: **08:10 UTC** codziennie (09:10 w Polsce zimą, 10:10 latem). Rzeczywisty pierwszy audyt wykonany przed merge: run **42585396793**, artifact report **13659340632**. Testował realne archiwum `13619490089` i dostał **8/8 87-cechowe pola+zegary**, **8/8 archive >90m przed kickoff**, **0/8 host-created <= oryginalny feature_cutoff**. Dotychczasowe kolektory PitchAPI pozostawiono bez zmian, bez dodatkowych provider API calls; testy nie odczytują private key. **Oficjalny v3 PIT TRAIN/SHADOW nadal 0**. Nie połączono archiwum `.enc` z `verified_view` oryginalnego buildera; tego nie wolno traktować jako ukończonego. [PR #168](https://github.com/karolbarankiewicz1984-ui/kb-score-3/pull/168), [CI](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/42585950797).

Następna potrzebna implementacja: rzeczywisty dwufazowy pipeline source-archive host proof **przed cutoff**, następnie deterministyczny `verified_view` z natywnymi bajtami źródeł w kontrolowanym środowisku (bez poświadczania zegara wstecz). Harmonogram monitoringu na `main` nie jest sam w sobie dowodem powstania nowych v3 PIT próbek.


## Realny dwufazowy zapis przed cutoff i 9 oryginalnych wektorów v3 — PASS (09.11)

**Zakończono brakującą implementację** source archive → niezależny GitHub host timestamp/digest → po prawdziwym cutoff oryginalny `verified_view` + `vector`. Na `main` wdrożono osobny workflow `.github/workflows/kb3-v3-native-two-phase.yml` przez [PR #169](https://github.com/karolbarankiewicz1984-ui/kb-score-3/pull/169) i poprawkę na przerwy ligowe [PR #170](https://github.com/karolbarankiewicz1984-ui/kb-score-3/pull/170). [Prawdziwy run #42594056216](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/42594056216) — **3/3 jobs success**. W 7 wywołaniach aktywnego PitchAPI utworzono 6 serializowanych natywnych odpowiedzi, GitHub source artifact **13661918237** host-created `2026-11-09T09:31:34Z`, ZIP SHA `784a4877479cf2513c131496b5894012da4c004d67420f81a23126827bc41ed6`. **Dokładny cutoff `2026-11-09T09:37:33.400068Z`, host przed cutoff o 359.4 s**. Verified builder wykonał się o `09:37:33.400727Z`: **9/9 wejść x 87/87 wartości**, ESP3, ITA3, GER3, przyszłe mecze 20–21.11, output artifact **13662304326**. Niezależny audyt natywnych wierszy potwierdził 4128/4128 zgodności fixture, wyniku, zegara i SHA. **Formal v3 TRAIN nadal 0**, gdyż to prematch input bez przyszłych etykiet i nie jest to dowód daty pierwszej publikacji przez dostawcę; **nie ma jeszcze oficjalnego fit, ani modelu Shadow**. M0/Champion/TEST bez zmian. Monitoring i realna archiwizacja zaplanowane na 05:10 UTC codziennie (maks. 7 dodatkowych provider calls, 90 dni retencji); kolejne próbki tego samego meczu nie mogą być liczone jako osobne mecze w treningu. [Raport końcowy](../reports/KB3_V3_REAL_TWO_PHASE_9_NATIVE_87_VECTORS_2026-11-09.md), commit `3c0e7f5`.
