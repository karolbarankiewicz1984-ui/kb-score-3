# KB Score 3.0 — wykonanie priorytetów 1–5 po odzyskaniu GitHub Actions (2026-11-01)

**Status audytu: częściowo wykonano, z jawnymi blokadami; formalnie 15/29, GATE16=PENDING, GATE17=PENDING.** Ten protokół nie jest akceptacją produkcji, scalenia gałęzi ani nowego fitu. Daty poniżej UTC; czas polski 01.11.2026 = UTC+1.

## P1 — GitHub Actions / niezmienny przedmeczowy M0 720-TRAIN

- Rzeczywiste, zakończone SUCCESS po miesięcznym resecie: [Step16 eight-league Actions #41260370277](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/41260370277) (2026-11-01 01:16 UTC, **mode=settle**) i [stary trzy-ligowy M0 postmatch #41261327143](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/41261327143) (01:29 UTC, **oddzielny strumień**). Oba realne joby uzyskały SUCCESS, w tym kroki GitHub runnera i zapisu źródeł.
- Ośmioligowy receipt: [2026-11-01/settle-011723723032/RECEIPT.json](../data/pit_sidecar/m0_720_eight/2026-11-01/settle-011723723032/RECEIPT.json). Stan: 73 **poświadczone** stare forecasty, 38 rozliczonych, 35 oczekujących, **0 nowych host proofs** i **brak nowego forecastu w tym konkretnym cyklu**. Wersja `M0_ELO_POISSON_RESEARCH_720TRAIN_V1`, parametry SHA256 `55310f0e1dd3842e6d876069ef21b1380901b3a6cc6884cf6ec6ea351a5812d1` nie zmieniły się. Raport: 9 wywołań provider w cyklu settle, bez TEST ENG.
- Oddzielny starszy M0 trzy-ligowy [2026-11-01 postmatch](../data/pit_sidecar/m0_postmatch/2026-11-01/run-013026824188/M0_POSTMATCH_AND_CALIBRATION_REVIEW.json): 12 rozliczeń; `server_first_publication_utc_independently_proven=false`, dlatego nie wolno dodawać ich do puli 38 ośmioligowego FIT100.
- Sam SUCCESS rozliczania nie dowodzi jeszcze nowej skutecznej sesji **forecast** po resecie. Harmonogram Step16 prognoz: 06:21 UTC, a Step17 xG: 06:41 UTC. Nowy przebieg i jego serwerowy timestamp należy sprawdzić oddzielnie po pojawieniu się w Actions. Dokładna pozostała pula miesięcznych minut Actions nie została odczytana — dwa SUCCESS potwierdzają możliwość wykonania jobów, nie całe billing.
- Nie retry'owano wcześniejszych historycznych live-jobów, by nie prowokować spóźnionego forecast lub wymuszonego kosztu API.

## P2 — kontrola napraw Step15 / Step16 bez merge

- PR [#122](https://github.com/karolbarankiewicz1984-ui/kb-score-3/pull/122): na izolowanej gałęzi `repair/step15-independent-poisson-offline-20261030` w commit `00b80cbf0e07655d247166fcb72da63eabef68ba` rozszerzono **read-only** workflow o wcześniej istniejące testy rynków bramkowych i `git diff --exit-code -- data/ models/`. Nie było zmian modeli czy prognoz.
- Po resecie ręcznie ponowiono **tylko** nieudany, bezsieciowy job `offline-step15` w [Actions #41104025484, attempt 2](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/41104025484) i uzyskano **SUCCESS**. **Ważne:** rerun GitHub wykonuje historyczny commit tej próby, a NIE nowe repo HEAD `00b80cb`; wynik potwierdza testowany historyczny wariant audytu, nie cały najnowszy PR. Aktualna gałąź wymaga odrębnego CI.
- PR [#123](https://github.com/karolbarankiewicz1984-ui/kb-score-3/pull/123): wykryto dwa wystąpienia `cache: 'pip'` umieszczone w **tym samym** kroku setup-python i brak cache w drugim jobie. W atomowym commit `62a5664f092b165b5f398d945018168da4c2c622` przyporządkowano **jedno** `cache: pip` i właściwy requirements każdemu z dwóch oddzielnych jobów, oraz rozszerzono test statyczny, by ten błąd wykrywał. Zachowano harmonogram, zależności, ograniczenia i sekrety. Najnowszy commit wymaga rzeczywistego CI na aktualnym SHA.
- **Brak merge** PR #122 i PR #123 do `main`; nie nazywać ich pełnymi PASS do odbioru, dopóki aktualne head SHA i wszystkie bramki nie przejdą testów.

## P3 — kontrolowana integracja Codex R1–R5

- [Issue #121](https://github.com/karolbarankiewicz1984-ui/kb-score-3/issues/121) i dokumentacyjny [DRAFT PR #124](https://github.com/karolbarankiewicz1984-ui/kb-score-3/pull/124) odczytano. PR #124 nadal zawiera wyłącznie dokument bramek, bez 57-plikowego źródła poprawki Codex, bez R5 i bez migracji.
- Źródłowy ZIP R5 (`KB_SCORE_3_CODEX_R5_011_012_REVIEW_2026-10-30.zip`, uprzednio udokumentowany SHA256 `d06446dd9f31ab056f2d45fc17bfaa701e1e38904ecb1aee55517002b7063a07`) **nie został odnaleziony jako dostępny plik** w bieżących dostępnych materiałach, repo `main`, wyszukiwaniu Library ani Drive; nie rekonstruować 57 plików z opisów ani nie podawać CI jako ukończonego.
- Nadal wymagane: pełny patch R1–R5 + fixtures; niezależne 197/108 częściowo pokrywających się regresji + 9 R5; kopia rzeczywistej SQLite i rollback; niezależne porównanie 73 starych hashy, zgodność V1 i blokady V2. Decyzja `MERGE_NO_GO`, bez zmiany `data/`, `models/`, no TEST access.

## P4 — zbieranie nowego PIT / natywnego xG

- Utrzymano istniejący harmonogram M0 ośmiu lig oraz niezależne xG, bez dodatkowej ręcznej płatnej sesji PitchAPI i bez nadpisywania.
- Ostatni dostępny, rzeczywisty [Step17 XG_READINESS_RECEIPT 2026-10-29](../data/pit_sidecar/step17_native_xg_eight/2026-10-29/XG_READINESS_RECEIPT.json): 7/8 poprawnych natywnych par shots/stats, **0/74** przyszłych spotkań z pełnym last5 obu zespołów. `CATBOOST_WITH_XG=NOT_TRAINED`.
- Obowiązuje brak imputowania xG zerem, pięć faktycznie ostatnich spotkań, źródła szyfrowane, tożsamość/period=All i porównanie shots vs stats. Późniejszego wywołania xG nie wolno uznać za sukces bez rzeczywistego nowego receipt i dowodu.

## P5 — odczytowy audyt matematyki i wspólnego porównania silników

- Niezależnie zsumowano metryki ośmiu lig, ważąc liczbą rzeczywiście rozliczonych: `n=38`, Brier sum3 `0.5793652008982196`, log loss `0.9748187123592499`, top1 `0.5526315789473685` — zgodne (z dokładnością zaokrągleń) z `pooled_scores` w zamrożonym raporcie. `eligible_settled_unique=38`, `missing_to_fit=62`, po pierwszym fit wymagane **50 nowo utworzonych** forecastów.
- Dla starszego trzy-ligowego M0 średnie arytmetyczne 12 zapisów meczowych: Brier `0.5862385506009001`, log loss `0.9858113029467689`; zgodne z agregatem, lecz nie stanowią pełnego niezależnego source clock proof.
- `step17_paired_same_fixture_readiness.full_five_common_fixtures=0`, para M0–ELO-only i M0–CatBoost no-xG też `common_n=0`; brak podstaw do wyliczenia rzeczywistego porównania w tym cyklu, dopuszczenia modelu z xG albo wyboru Championa.
- **Zakres tej kontroli:** niezależne przeliczenie agregatów zapisanych w receipts; to **nie** jest ponowne obliczenie każdego p(1/X/2) z surowych źródeł i nie certyfikuje jeszcze nowego forward forecast.

## Otwarte bramki i niezmienne zakazy

1. Pierwszy po resecie serwerowo poświadczony nowy `forecast` M0, a nie tylko `settle`.
2. Rzeczywiste testy CI aktualnych HEAD #122 i #123 i kontrola 100+50.
3. Autentyczna kompletna paczka Codex + migracja na kopii SQLite przed jakimkolwiek merge #124.
4. Kolejny rzeczywisty receipt native xG i pełny wspólny zbiór modeli przed GATE17.
5. **GATE16=PENDING, GATE17=PENDING, formalnie 15/29.** Nie naruszono 73 starych prognoz, SHA parametrów, budżetu, kluczy, chronionego TEST Premier League 2026/27; brak nowego model fit, automatycznej kalibracji czy promocji Championa.

**Dokumentacja operacyjna; nowe dowody dopisywać chronologicznie, nie przerabiać wcześniejszych statusów na PASS bez testu.**
