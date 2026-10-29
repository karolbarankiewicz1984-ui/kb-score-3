# KB Score 3.0 — rejestr ustaleń: prognozy bieżące, dane przedmeczowe, kalibracja i trwałe archiwum

**ADR-2026-10-29-01 | status: PRZYJĘTE ZAŁOŻENIA I PLAN WDROŻENIA | data: 29.10.2026 | projekt: KB Score 3.0**

> **Obowiązkowy dokument referencyjny** przed planowaniem kolejnych prac z M0/M1, PitchAPI, prognozami, przechowywaniem danych, kalibracją, historią PIT lub harmonogramem 29 kroków. Nowe decyzje dopisywać z datą do rejestru zmian; nie usuwać starych ustaleń ani nie przedstawiać projektu jako wdrożonego, jeśli nie ma testu produkcyjnego.

**Źródło prawdy formalnego 29-krokowego planu:** [Google Docs — plan główny v1.1](https://docs.google.com/document/d/10wjHL3r3OAuxtezwcIeWztxS8lwjhYon5GM3BLhI0xE/edit). **Operacyjna kopia:** [PLAN.md](PLAN.md). Ten ADR jest doprecyzowaniem **równoległego pilotażu badawczego**, a nie milczącą zmianą zakresu etapów, zasady TEST ani odbioru GATE14. Konflikt rozstrzygać przez odniesienie do zatwierdzonego planu i jawne odnotowanie nowej decyzji.

## A. Jednoznaczny podział: co ustalone, co dopiero proponowane, co faktycznie działa

| ID | Zapis decyzji | Klasyfikacja | Stan wykonania na 29.10.2026 |
|---|---|---|---|
| D01 | Uruchamiamy **badawczy** strumień prognoz M0 (Elo+Poisson), bez czekania na pełne historyczne xG M1; **nie zastępuje oryginalnego CatBoost M1** | KIERUNEK UZGODNIONY | Matematyka M0 istnieje; pełne cykliczne typowanie i wynikowy backend M0 jeszcze **NIEWDROŻONE** |
| D02 | Istniejące 29 formalnych punktów pozostaje; etap 14 **GATE14 PENDING**, formalne 13/29; późniejsze etapy można przygotowywać równolegle, ale nie zaliczać wcześniej | ZASADA TWARDA | Obowiązuje; oficjalny historyczny M1 **NIEWYTRENOWANY** |
| D03 | Pełne cechy: **121 numeric + 38 missing flags**, w tym **73 bez xG i 48 związanych z xG/xGA**; braki to `null + powód/maska`, nigdy podstawione zero | KONTRAKT ORYGINALNY | Schemat cech istnieje; pełne bieżące pobieranie i budowa dla wszystkich meczów **NIEWDROŻONE** |
| D04 | Każda prognoza i wejściowa migawka powstają **przed kickoff**, mają własne rzeczywiste znaczniki czasu, wersję i niezmienny hash; po meczu dopisywany jest osobny wynik | ZASADA TWARDA | Triggery immutable SQLite i funkcje czysto matematyczne istnieją; autentyczne zewnętrzne publikacje prognoz **NIEZINTEGROWANE** |
| D05 | Badawczy strumień z **lig spoza zamrożonego TEST** służy do dobierania przyszłej kalibracji; Premier League 2026/27 nadal stanowi wydzielony TEST oryginalnego M1 | ZASADA TWARDA | Separacja TEST obowiązuje; pilotaż innych lig **NIEWDROŻONY** |
| D06 | Diagnostyka od ~**20–30** meczów; pierwsza propozycja temperatury po **>=100** rzeczywistych, zamrożonych i rozliczonych prognozach z tej samej wersji; ocena wyłącznie na **>=50 kolejnych, niezależnych** meczach; brak autowdrożenia | PRZYJĘTA POLITYKA BADAWCZA | Funkcje i testy matematyki istnieją; proces produkcyjny **NIEWDROŻONY** |
| D07 | Główna ewidencja **SQLite**, większe tablice do treningu **Parquet**; GitHub kod/manifesty/zaszyfrowane dowody; niezależna zaszyfrowana kopia **Google Drive** | ARCHITEKTURA PRZYJĘTA | SQLite schema i syntetyczny restore ukończone; **produkcyjna replikacja SQLite/Parquet na Drive NIEWDROŻONA** |
| D08 | Wykorzystywać istniejące sekrety GitHub/ustalone RSA; nie żądać wielokrotnych czynności użytkownika, kluczy i PEM; nie obniżać kontroli PIT i integralności | ZASADA TWARDA | [Reguły obsługi dostępów](WORKFLOW_NO_REPEATED_OWNER_AUTH_AND_MODEL_INTEGRITY.md) |
| D09 | **T-24 h** i **T-60–90 min** to dwa *proponowane* punkty freeze, nie dwa niezależne mecze; jedna zatwierdzona faza/wersja do danego eksperymentu | PROJEKT HARMONOGRAMU, NIE WDROŻENIE | Nie jest skonfigurowany |
| D10 | Pilotaż na **trzech ligach poza chronionym TEST**, po sprawdzeniu zakresu PitchAPI i kosztów, bez kupowania nowych usług bez zgody | REKOMENDACJA, NIE OSTATECZNA LISTA LIG | Nie wybrano lig, nie uruchomiono odrębnego pobierania |
| D11 | Uruchomiony dzienny prawdziwy archiwizator PitchAPI do **6 zapytań/dzień, tylko PL 2026/27**, przechowujący w tym trybie najwyżej 4 nadchodzące terminarze i 2 wcześniejsze kompletne mecze shots/stats | FAKTYCZNIE WDROŻONE — WĄSKI ZAKRES | [C rzeczywisty przebieg i kod](STEP14_C_DAILY_REAL_PITCHAPI_ASOF_ARCHIVE_2026-10-28.md); **nie jest** to pełny system 121+38 dla kilku lig |
| D12 | Nie kupować płatnych API tylko na podstawie obecnych retrospektywnych wyników; wymagać próbki i dowodu historycznego `published_at`/wersji, kosztu i licencji | ZASADA ZAKUPOWA / REKOMENDACJA | Żadnego zakupu autoryzowanego |
| D13 | Kalibracja prawdopodobieństw i uczenie modelu cech z xG to **oddzielne procesy**; same wyniki i xG po meczu nie „douczą” wag M1 przez temperature scaling | ZASADA METODOLOGICZNA | Warstwa kalibracji matematycznej istnieje; właściwy trening M1 nadal zablokowany |

## B. Definicja jednej rzeczywistej próbki

Dla każdego rzeczywistego spotkania i konkretnej wersji modelu utrwalać **powiązane, nieredagowalne rekordy**; różne horyzonty czasowe to *oddzielne pomiary tego samego meczu*, nie niezależne obserwacje:

1. **`source_snapshot` i statystyki poprzednich spotkań**: `provider`, `source_fixture_id/team_id`, zmapowane kanoniczne ID i źródłowa definicja statystyki, `captured_started_utc`, `captured_completed_utc`, ewentualne autentyczne `provider_published_at_utc` (w przeciwnym razie **null**), SHA256 surowej odpowiedzi, wersja API, status pełności/missing reason, wariant metody.
2. **`feature_snapshot` przed meczem**: dokładny identyfikator celu i kickoff UTC, model/variant `M0_BASELINE` lub późniejszy M1, cechy Elo, wyniki/formy 5/10/15, gole, różne okna home/away, historyczne xG/xGA poprzednich spotkań, odstępy czasowe, liczność próby, **121+38 zgodnie z kontraktem, jeśli dana wersja tego kontraktu wymaga**, znacznik cut-off oraz SHA256 wejściowej migawki. Nie wolno dopisać po starcie meczu nawet „korekty źródła” do starego snapshotu.
3. **`prediction` + `prediction_publication`**: `forecast_id`, `fixture_id`, model version, faza `EARLY`/`FINAL_PREMATCH`, `generated_utc`, **rzeczywista niezależnie poświadczona** `frozen/published_at_utc < kickoff_utc`, `feature_snapshot_sha`, prawdopodobieństwa w **kolejności 1/X/2** i suma 1; ewentualne prognostyczne gole, BTTS i poszczególne rynki osobno. Czas samodzielnie zapisany w polu JSON i hash nie wystarczają jako dowód publikacji.
4. **`settlement` (po meczu)**: faktyczne FT 90 min, `result_1x2`, wiarygodne źródło i serwerowy czas uzyskania wyniku; ewentualne końcowe xG, strzały, kartki, rożne; korekta wyłącznie dopisana jako nowe zdarzenie. Nie zmieniać wcześniejszej prognozy ani cech.
5. **`quality_audit` / `calibration_candidate`**: odwołania do zamrożonych prognoz, rzeczywiste etykiety i daty; log loss, wieloklasowy **Brier sum3** (suma błędów dla trzech klas, bez /3), ECE/reliability, trafność, podział po wersji i fazie, osobne cutoff/embargo, nowa wersja temperatury i metryki na **nieużytej do fit** próbie.

**Ważne:** nie przechowywać w jednym „finalnym arkuszu” prognoz i późniejszych wyników jako nadpisywanych kolumn danych treningowych. Dane z dawnych miesięcy pobrane dzisiaj są **dopuszczalne do prognoz jutra**, ale nie świadczą o ich dostępności przed historycznym meczem sprzed pobrania.

## C. Proces end-to-end i kryteria bezpieczeństwa

`Pobierz przedmeczowe sources → sprawdź team/fixture/UTC/kontrakt → immutable feature snapshot → wykonaj M0 prognozę → uzyskaj niezależny serwerowy dowód freeze < kickoff → mecz → pobierz zakończony wynik → settlement append-only → log loss/Brier/ECE → rozważ kalibrację / osobny challenger → dopuszczaj przyszłe wersje tylko po dowodzie przewagi.`

- **Target leakage:** bez wyników, statystyk i aktualizacji wydarzenia docelowego dostępnych po oryginalnym cutoff; bez „pierwotnego PitchAPI published_at” wymyślanego na podstawie bieżącego odczytu; każda próbka jest kwalifikowana dopiero po sprawdzeniu cutoff.
- **TRAIN / VALIDATION / TEST oryginalnego planu:** 2023/24 + 2024/25 = **760 TRAIN**; 2025/26 = **380 VALIDATION**; 2026/27 Premier League = **380 TEST**. Rozdział i oryginalny kontrakt 121+38 pozostają bez zmiany. **Wyniki z TEST 2026/27 nie mogą służyć do dostrajania M0/M1 ani kalibratora, który będzie następnie oceniany na tym TEST**. Dopuszczalne zachowawcze prognozy `SHADOW` / blind freeze, bez użycia wyniku do wyboru/uczenia systemu przed końcową ewaluacją.
- **Inne ligi jako osobny pilotaż kalibracyjny:** odrębny dataset, liga+sezon+skala czasu, wersja modelu, niezależne kolejne spotkania. Nie przenosić automatycznie temperatury między ligami, jeżeli brak dowodu stabilności. Nie włączać innych lig do oryginalnego TEST ani treningu M1 bez formalnej decyzji o zmianie kontraktu.
- **Prowadzenie badań na bieżąco ≠ oficjalny odbiór kolejnego kroku:** równoległe przygotowywanie 15–16, 21–22, 24, 26–27 nie zmienia stanów do czasu spełnienia kryteriów z PLAN.
- **Wersjonowanie:** `M0_{code_sha}_{config_sha}`, `model_version + variant + phase + league_scope`; każda zmiana reguł/formatu danych/modelu odrębnie wersjonowana. Nie mieszać prognoz różnych modeli jako jednej próbki 100/50. Jeśli model wejściowy się zmienił — budować nowy odpowiedni eksperyment kalibracji.
- **Warunki eksperymentu:** jeżeli wektor M0 nie jest obliczalny z autentycznych danych dostępnych na cutoff, oznaczyć `NOT_ELIGIBLE`, nie wytwarzać fikcyjnej prognozy; nie kopiować historycznych wyników z kolejnego dnia do poprzedniej migawki.

## D. Kiedy i jak następuje kalibracja

**Pełny opis istniejącej matematyki:** [Krok 14 — M1 math/calibration](STEP_14_CATBOOST_M1_MATH_XG_CALIBRATION_2026-10-27.md), kod `src/kb3_step14_m1_math_calibration.py`, funkcje `freeze_forecast`, `audit_frozen_settlements`, `prepare_future_calibration_candidate`, `fit_temperature`, `evaluate_calibrated_holdout`.

| Moment | Co wolno | Czego nie wolno |
|---|---|---|
| 20–30 zamrożonych i rozliczonych meczów | Zbadać problemy źródła danych, rozkład prawdopodobieństw, obserwowane błędy, brakujących pól | Przyjmować na tej podstawie „najlepszą” produkcyjną temperaturę |
| **min. 100** dla jednego `model_version + variant + phase` i porównywalnego zakresu lig | Wybrać **kandydata** temperatury na wyłącznie wcześniejszych prognozach oraz zakończonych przed zamrożonym kalibracyjnym cutoff wynikach | Zajrzeć do kolejnych spotkań, podmienić starych prognoz, dopasować każdej małej lidze/rynkowi temperaturę z małej próby |
| **min. 50 następnych** odrębnych meczów, bez udziału ich etykiet w wyborze temperatury | Osobna ewaluacja parami: wersja surowa vs skalibrowana na tych samych meczach; `log loss`, `Brier sum3`, `ECE`, liczność i wpływ okresu/ligi; rozważyć niezależny przedział niepewności | Automatycznie aktywować korektę po jednostkowej poprawie lub uznać 150 za statystyczną gwarancję |
| Wynik jest dodatni, stabilny i przeszedł audyt | Jawna decyzja o nowym kalibratorze stosowanym wyłącznie do **przyszłych** prognoz | Nadpisywać dawnych wyników, zmieniać wersji bez logu |

**Temperature scaling:** `softmax(log(P)/T)`, dla `T>0`; `T=1` bez zmiany, `T>1` zwykle łagodzi pewność. Obecna bezpieczna siatka: `0.7, 0.85, 1.0, 1.15, 1.4, 1.8, 2.2`. Nie jest to ponowne uczenie wag Elo/CatBoost; nie zmienia rankingu 1/X/2 przy dodatniej T.

**Nowy M1 uczony na xG to odrębna gałąź:** do treningu 121 cech zwykle potrzeba znacznie więcej niż 150 niezależnych spotkań i właściwej chronologicznej walidacji. Do czasu udowodnienia pochodzenia oryginalnego zbioru PIT z 2023–2025 wciąż: **13/29; GATE14 PENDING; certyfikowany oryginalny TRAIN=0/760, VALIDATION=0/380, oficjalny CatBoost M1 niewytrenowany**.

## E. Miejsce i sposób przechowywania — istniejąca architektura, nie fikcyjny backend

1. **SQLite**: główne tabele `source_snapshots`, `match_stat_observations`, `feature_snapshots`, `model_versions`, `predictions`, `prediction_publications`, `settlements`, `quality_audits` itd. [migracja 001](../migrations/001_initial_schema.sql) z zakazami UPDATE/DELETE frozen predictions/publications/settlements. **Obecnie wdrożony schemat i test restore syntetyczny — nie pełny produkcyjny ewidencjonowany live forecast ledger**.
2. **Parquet**: planowany format większych prawidłowo wyodrębnionych tabel treningowych/kalibracyjnych; nie twierdzić, że gotowy proces eksportu i zarządzania wersjami już działa.
3. **GitHub (prywatne `kb-score-3`)**: kod, audyty, małe manifesty, autentyczne zamrożone SHA i ewentualnie zaszyfrowane źródła. Już działa [bardzo ograniczony, rzeczywisty PitchAPI daily `as-observed`](STEP14_C_DAILY_REAL_PITCHAPI_ASOF_ARCHIVE_2026-10-28.md), cron **04:42 UTC**, 6 call/d, do 4 celów + 2 zakończonych poprzedników, **Premier League 2026/27 wyłącznie**. Dzienny `.enc` AES-GCM/RSA-public, `.manifest.json`, `RECEIPT.json` w `data/pit_sidecar/step14_pitchapi_native/YYYY-MM-DD/`. **To NIE pełna archiwizacja 3 lig ani 5/10/15 poprzedników.**
4. **Google Drive backup**: [KB Score 3.0 — Kopie zapasowe](https://drive.google.com/drive/folders/17NvQFKNkFd4eHZSqa-bNU0nFFSmHKTKo), test syntetycznego backup/restore istnieje w [Step 08](STEP_08_ACCEPTANCE.md). **Produkcyjny replikator bazy/archiwów na Drive nie jest jeszcze wdrożony.** Artifact GitHub Actions ma ograniczoną retencję (np. 30–90 dni w zależności od workflow), dlatego nie stanowi jedynego magazynu.
5. **Ochrona**: RSA prywatny PEM zostaje po stronie właściciela; GitHub Secrets zawierają API; repo nie może zawierać klucza jawnego ani odszyfrowanych źródeł. Reużywać już raz potwierdzonych SHA/dowodów; nie prosić o niepotrzebne kolejne logowania. Bez zakupów API bez wyraźnej zgody.

## F. Plan wykonawczy względem harmonogramu 29 punktów

| Etap planu | Co wolno robić wcześniej jako pilotaż | Co pozostaje kryterium formalnym |
|---|---|---|
| **13 (zaliczony)** | M0 Elo+Poisson jako bazowy silnik eksperymentalnego SHADOW | Nie zmieniać oryginalnego zaliczenia |
| **14 (otwarty)** | Równoległy forward freeze / historyczne source lineage / izolowane testy M1 bez retrospektywnego oszustwa | Oryginalny M1 wymaga historycznego TRAIN PIT; żadnych zmian GATE14 |
| **15** | Przygotować obliczenia goli/BTTS/O-U | Odbiór dopiero zgodnie z PLAN |
| **16** | Założyć ledger i przygotować kandydatów temp po 100 + niezależnych 50 | Nie ogłaszać pełnej kalibracji bez prawdziwych zamrożonych prognoz i testu |
| **17–18** | Porównywać badawczo shadow i Challenger, nie zatwierdzać Championa | Champion tylko po osobnym formalnym odbiorze |
| **21–22** | Pilotaż freeze/settlement append-only i kontroli źródeł | Status „zaliczone” wyłącznie po próbie realnego odtworzenia i jakości |
| **24** | GitHub Actions jako platforma harmonogramu i alertów | Nie twierdzić, że pełny daily forecasting/reporting już działa |
| **26–27** | Przygotować dziennik zmian, wersje modelu i monitoring drift | Nie wdrażać samozmiennych wag bez oddzielnej walidacji |

**Kolejność przyszłej pracy** (jeszcze nie oznacza, że wykonano): (1) sprawdzić licencję/limity PitchAPI i wybrać ligi poza TEST; (2) powiększyć źródłowe as-observed dla poprawnych form 5/10/15 obu drużyn; (3) uruchomić produkcyjne SQLite + niezależny signed server freeze + backup/restore; (4) zamrażać rzeczywiste shadow M0; (5) settlement i audyt 1X2; (6) po 100/50 ewentualnie dobrać/ocenić temperaturę; (7) osobno przygotować Challenger M1, nie dotykając TEST.

## G. Niepomylenie statusów i reguła powrotu do ustaleń

Każdy następny wątek o KB Score 3.0 zaczyna się od odczytu **tego ADR + oryginalnego PLAN + ZMIANY**. Odpowiedź lub PR mają wskazywać konkretnie: (a) decyzje zachowywane, (b) to, co faktycznie uruchomiono i przechodzi test, (c) to, co pozostaje propozycją oraz (d) czy dotknięto ochrony TEST, GATE14 lub prawdziwej daty publikacji. Nie oznaczać projektu jako pełnoprawnie skalibrowanego / samouczącego się bez rzeczywistych próbek, wersji, audytu i niezależnej ewaluacji.

**Zmiana niniejszego ADR:** dodać nowy wpis z datą do [ZMIANY.md](ZMIANY.md) i nowy ADR lub jawny aneks z argumentacją; nie usuwać historycznego wpisu. Przy konflikcie proponowane rozwiązanie uzgodnić przed zmianą formalnych reguł modelu.

## H. Materiały źródłowe wewnątrz repo

- [Oryginalny kontrakt i stan kroku 14](PLAN.md)
- [Historyczne źródła PIT i realna rekonstrukcja](STEP14_COMPREHENSIVE_HISTORIC_PREMATCH_RECONSTRUCTION_2026-10-28.md)
- [Matematyka M1 1X2 i bezpieczna przyszła kalibracja](STEP_14_CATBOOST_M1_MATH_XG_CALIBRATION_2026-10-27.md)
- [Step 08 — schema, synthetic backup, przyszła replikacja](STEP_08_ACCEPTANCE.md)
- [Step 14 C — istniejący wąski PitchAPI daily](STEP14_C_DAILY_REAL_PITCHAPI_ASOF_ARCHIVE_2026-10-28.md)
- [Stała zasada ograniczenia ręcznej autoryzacji i PIT](WORKFLOW_NO_REPEATED_OWNER_AUTH_AND_MODEL_INTEGRITY.md)

## Aneks 29.10.2026 — wykonany audyt przygotowania trzech lig

**Zmiana statusu D10/D11 tylko w zakresie źródeł:** Hiszpania LaLiga, Włochy Serie A, Niemcy Bundesliga zostały rzeczywiście zweryfikowane przez istniejący klucz PitchAPI i osobne testowe działanie inkrementalnego kolektora: [szczegółowy raport](STEP14_PITCHAPI_THREE_LEAGUE_LIVE_AUDIT_AND_CAPTURE_2026-10-29.md). Audyt: 13 rzeczywistych wywołań SDK, 3/3 lig dostępne dla sezonów 2026/27 i 2025/26, trzy rzeczywiste shot+xG i team stats; następnie kolektor 43 wywołania i 18/18 wcześniejszych spotkań z xG. Konfiguracja cykliczna `06:17 UTC`, maks. 6 wcześniej niesprawdzonych spotkań na ligę i dobę, zaszyfrowany zapis surowych danych i dzienny bezpieczny raport. **Prawdziwy cykliczny produkcyjny zapis w main należy oznaczyć za wdrożony dopiero po udanym przebiegu na main i odczycie dowodu.** Nie oznacza to uruchomienia M0, pełnej macierzy cech, SQLite ani kalibracji; `GATE14=PENDING`, TEST Premier League 2026/27 nietknięty.

**Potwierdzenie po merge, 29.10.2026:** rzeczywisty [audyt na main](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40831753337) oraz [kolektor na main](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40831753344) oba **SUCCESS**. Zewnętrzny odczyt repo potwierdził obecność `data/pit_sidecar/pitchapi_three_league_daily/2026-10-29/THREE_LEAGUE_DAILY_SOURCE.enc`, manifestu i raportu z 43 prawdziwymi source receipts i 18 poprawnymi xG poprzedników. **D10 jest wykonany w zakresie wyboru/audytu 3 lig, D11 rozszerzony o rzeczywisty przyrostowy kolektor 3 lig** (obok wcześniejszego osobnego PL), ale nie o kompletny bieżący M0, full 121+38, produkcyjny SQLite ani dostosowanie/walidację temperatury. `GATE14=PENDING`.

### Aneks 29.10.2026 — powiązanie PitchAPI z SQLite i rzeczywistymi future `feature_snapshots`

Przygotowano i przetestowano produkcyjny zapis wejściowych cech (bez prognoz): [raport i specyfikacja](STEP14_LIVE_M0_SQLITE_121_38_FORWARD_FREEZE_2026-10-29.md), oryginalna migracja 001 plus `migrations/002_forward_m0_observed_freeze.sql`, adapter z oryginalnym algorytmem Elo/form kroku 11 oraz SHA/cutoff dla każdego z 159 pól i nienadpisywalny SQLite `data/forward_m0/kb3_forward_m0.sqlite`. **Status pierwszej rzeczywistej migawki potwierdzić wyłącznie po udanym main Actions i istnieniu pliku w repo.** Zero automatycznych prognoz/treningu M0/M1, kalibracji; 2026/27 PL TEST i `GATE14` bez zmian.


### Potwierdzenie main, 29.10.2026: rzeczywista relacyjna SQLite z 12 zamrożonymi wektorami M0

**Weryfikacja kompletna:** [Actions #40834611730](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40834611730) **SUCCESS**, 43 rzeczywiste PitchAPI requests + 7/7 testów SQLite + 7/7 testów inkrementacji; na main bezpośrednio sprawdzono rzeczywisty plik [`data/forward_m0/kb3_forward_m0.sqlite`](../data/forward_m0/kb3_forward_m0.sqlite) (**2 891 776 B**), [źródłowy `THREE_LEAGUE_DAILY_RECEIPT.json`](../data/pit_sidecar/pitchapi_three_league_forward_initial/2026-10-29/THREE_LEAGUE_DAILY_RECEIPT.json), a także zaszyfrowany oryginał `.enc` i manifest. SQLite zawiera 12 oryginalnych obserwowanych przed kickoff zestawów cech (po cztery na ESP/ITA/GER, minimum 90 min marginesu), każdy z **121 numeric/nullable + 38 missing flags oraz 159 sprawdzonymi czasami dostępności**. Zero prognoz, zero dopuszczonego oficjalnego M1; brakujące xG nie imputowane. Proces ciągły z tym samym źródłem dodaje nowe dzienne migawki do tej samej prywatnej bazy; niezależny backup Google Drive nadal planowany. D01 pozostaje NIEWDROŻONE w zakresie wystawiania M0 forecasts, natomiast D04/D07 częściowo WYKONANE w zakresie rzeczywistego capture→features→frozen SQLite. Szczegóły i granice [raport](STEP14_LIVE_M0_SQLITE_121_38_FORWARD_FREEZE_2026-10-29.md). Oryginalne TEST PL 2026/27, GATE14, 13/29 bez zmian.


### Potwierdzone na main 29.10.2026 — 12 rzeczywistych 1/X/2 SHADOW dla M0 Elo+Poisson

Zaimplementowano [`migrations/003_m0_1x2_shadow_freeze.sql`](../migrations/003_m0_1x2_shadow_freeze.sql) z oddzielnym immutable `m0_shadow_1x2_forecasts`, nie zmieniając formalnego `predictions` i jego wymogu historycznej certyfikacji; `src/kb3_m0_shadow_1x2_live_freeze.py` korzysta bez zmian z matematyki `src/kb3_step13_baseline.py::forecast` i rzeczywistego `home_elo/away_elo` z 121+38 cech zapisanych na main. [Realne Actions #40836191816](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40836191816) **SUCCESS**, 6/6 testów, 12/12 konkretnych prawdopodobieństw 1/X/2 w [trwałym raporcie](../data/forecasts/m0_shadow_1x2/2026-10-29/FROZEN_M0_SHADOW_1X2.json) i SQLite; rzeczywisty freeze 29.10.2026 ok. 07:33:48 UTC, wszystkie mecze przyszłe z >=90min marginesu. `SHA256` oryginalnego raportu `67ce451834039f1c4334e213621734c2906aba9c8321fd3035c1879bda7aadf2`. Parametry Poissona nadal są **ILLUSTRATIVE UNFITTED, NIE prognostycznie ocenione**, `calibration_status=NONE`; żadne wyniki TEST PL nie zostały pobrane. Codzienne podłączenie do istniejącego trójligowego collectora: [dokument techniczny](STEP14_M0_REAL_PREMATCH_1X2_SHADOW_2026-10-29.md). **Nadal niezrealizowane**: rozliczanie wyników, metryki, kalibracja 100/50, backup Google Drive, oryginalny CatBoost M1. Zachowano 13/29; `GATE14=PENDING`.
