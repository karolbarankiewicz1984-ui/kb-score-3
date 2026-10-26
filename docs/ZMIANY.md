# KB Score 3.0 — ZMIANY I DECYZJE

**Typ dokumentu:** append-only dziennik zmian, decyzji, ryzyk i bramek odbioru. Nie usuwać zapisów historycznych ani wpisów FAIL; ewentualną korektę opisać nowym wpisem. **Źródło prawdy dla statusów:** [Google Docs — Plan główny](https://docs.google.com/document/d/10wjHL3r3OAuxtezwcIeWztxS8lwjhYon5GM3BLhI0xE/edit). **Kopia 29 etapów:** [PLAN.md](PLAN.md). Dokumenty techniczne: [DANE.md](DANE.md), [MODEL.md](MODEL.md).

## Reguły wpisów

Każdy odbiór zawiera: identyfikator kroku, datę i godzinę (z podaną strefą lub UTC), stan przed/po, wynik PASS/FAIL, link do dowodu, metadane testu, znane ograniczenia, osobę/automat dokonujący weryfikacji oraz następny krok. Samo uruchomienie testu **nie oznacza** PASS. Przed wpisaniem ZALICZONO należy ponownie odczytać dowody. Nowa wersja modelu, nowa opłata lub uruchomienie produkcji wymaga osobnej zgody właściciela.

**Stan po odbiorze kroku 08 (25.10.2026):** 8/29 odebranych (01–08); kroki 09–29 nieodebrane. W razie późniejszych zmian decyduje aktualny dziennik Google Docs. Dziennik Google Docs może zawierać późniejsze wpisy — w razie rozbieżności **odczytujemy oryginał Google Docs**.

## Rejestr decyzji projektowych

| ID | Data | Ustalenie | Stan / warunek zmiany | Dowód |
|---|---|---|---|---|
| DEC-001 | 2026-10-24 | Całkowicie nowy KB Score 3.0, nie nowa nazwa KB2.1 | ZATWIERDZONE jako kierunek; rewizja z uzasadnieniem | Plan główny Google Docs |
| DEC-002 | 2026-10-24 | KB2.1, API Market, MultiModel = benchmarki, nie automatyczny silnik KB3.0 | ZATWIERDZONE | Plan główny Google Docs |
| DEC-003 | 2026-10-24 | Każdy z 29 kroków ma bramkę PASS i dowód w dzienniku | ZATWIERDZONE | Plan główny v1.1 |
| DEC-004 | 2026-10-25 | Nowe repozytorium prywatne `kb-score-3`, odrębne od starego | ZATWIERDZONE, krok 02 PASS | [Commit struktury](https://github.com/karolbarankiewicz1984-ui/kb-score-3/commit/7c6cee2be18b3a771d0d94ccd3f6841f7f6d83a6) |
| DEC-005 | 2026-10-25 | Klucze API tylko w GitHub Secrets; bez nowych zakupów na starcie | ZATWIERDZONE, krok 03 PASS | [Test](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40203074557) |
| DEC-006 | 2026-10-25 | API-Football jako podstawowe źródło, PitchAPI jako uzupełnienie | ZAŁOŻENIE PROJEKTOWE; dokładne pokrycie dopiero po 05–06 | [DANE.md](DANE.md) |
| DEC-007 | 2026-10-25 | ELO+Poisson jako baseline, CatBoost jako kandydat ML, bez domyślnie narzuconej przewagi | ZAŁOŻENIE PROJEKTOWE; rozstrzygnięcie testami 13–18 | [MODEL.md](MODEL.md) |
| DEC-008 | 2026-10-25 | Rozdzielić wynik sportowy P i cenę/EV; oddzielne archiwum kursów, no lookahead i freeze | ZAŁOŻENIE PROJEKTOWE; dopracowanie 19–22 | [DANE.md](DANE.md), [MODEL.md](MODEL.md) |
| DEC-009 | 2026-10-25 | Docelowo 3 PDF o 09:30 Europe/Warsaw | PREFERENCJA, nie uruchomione; zatwierdzenie 23–25 | [PLAN.md](PLAN.md) |
| DEC-010 | 2026-10-25 | Bez auto-obstawiania, bez samoczynnego awansu nowej wersji produkcyjnej | ZATWIERDZONE jako zasada bezpieczeństwa | [MODEL.md](MODEL.md) |

## Dziennik bramek — zakończone kroki

### GATE 01 — PASS / ZALICZONO (24.10.2026)

- **Temat:** inwentaryzacja kont, usług, dostępów, kosztów, limitów.
- **Dowody:** protokół i screenshoty w [głównym planie Google Docs](https://docs.google.com/document/d/10wjHL3r3OAuxtezwcIeWztxS8lwjhYon5GM3BLhI0xE/edit).
- **Ograniczenia:** limity i dostępne minuty są historycznym stanem w chwili odczytu, nie gwarancją zasobów obecnie.

### GATE 02 — PASS / ZALICZONO (25.10.2026)

- **Temat:** utworzenie prywatnego repo GitHub, README, pierwszy commit i katalogi.
- **Dowód:** [struktura repo — commit](https://github.com/karolbarankiewicz1984-ui/kb-score-3/commit/7c6cee2be18b3a771d0d94ccd3f6841f7f6d83a6), URL https://github.com/karolbarankiewicz1984-ui/kb-score-3.
- **Kontrola:** private=true, main, osiem katalogów; brak zmian w starym repo w toku tego kroku.

### GATE 03 — PASS / ZALICZONO (25.10.2026)

- **Temat:** dwa działające klucze API w nowym repo, test oraz budżet i alerty.
- **Dowody:** [Actions run 40203074557](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40203074557), [checklista bezpieczeństwa](STEP_03_SECURITY_CHECKLIST.md).
- **Wynik:** API-Football PASS HTTP_200_JSON i PitchAPI PASS HTTP_200_JSON, kontrola wzorców wycieku w 12 plikach i logu: 0 trafień. To nie dowodzi niemożliwości innych wycieków.
- **Wydatki:** ekran GitHub Budgets & alerts z 25.10 pokazał Actions 0 USD i alerty On. Nie oznacza to samoistnie twardego stopu ani potwierdzenia aktualnych minut.

## GATE 04 — PASS / ZALICZONO (25.10.2026)

**Cel:** przygotować 4 pliki [PLAN.md](PLAN.md), [DANE.md](DANE.md), [MODEL.md](MODEL.md), [ZMIANY.md](ZMIANY.md) i linki między nimi oraz do Google Docs; skontrolować 29/29 kryteriów odbioru, brak fałszywych zaliczeń i zgodność źródła prawdy. 

**Dowody wykonania:** [protokół odbioru i wyniki QA](STEP_04_ACCEPTANCE.md), [plan 29 bramek](PLAN.md), [aktualizowany dziennik Google Docs](https://docs.google.com/document/d/10wjHL3r3OAuxtezwcIeWztxS8lwjhYon5GM3BLhI0xE/edit). Komplet dokumentacji: [DANE](DANE.md), [MODEL](MODEL.md), [ZMIANY](ZMIANY.md). 

**Decyzja odbioru:** PASS — 29/29 bramek, 29/29 wymaganych dowodów i zależności, zero błędnych odnośników w sprawdzonych dokumentach oraz zero przedwcześnie oznaczonych ukończeń kroków 05–29. Zatwierdzenie techniczne: odczyt GitHub i aktualizacja planu Google Docs. Następny KROK 05 — audyt API-Football.

### Wpis odbioru GATE 04 — 2026-10-25

- **Co wykonano:** cztery specyfikacje, indeks repo i decyzje.
- **Kontrola:** odczyt wszystkich plików i 29 etapów z ich warunkami PASS, porównanie odnośników i statusu z Google Docs.
- **Wynik:** PASS; [raport techniczny](STEP_04_ACCEPTANCE.md); [commit synchronizacji PLAN](https://github.com/karolbarankiewicz1984-ui/kb-score-3/commit/c0dcac77b32dacc20afe1723660dc4187347723d).
- **Ryzyka:** brak jeszcze audytu danych/pełnej metodologii produkcyjnej; nie uruchomiono ML.
- **Następny krok:** KROK 05 — API-Football.


## GATE 05 — PASS / ZALICZONO (25.10.2026)

- **Cel:** udokumentować realne pokrycie API-Football dla 5 lig i 2021–2026; liczebności, limity, statystyki i braki danych.
- **Raport:** [GATE 05 — protokół odbioru](STEP_05_ACCEPTANCE.md), [audyt liga×sezon](audits/API_FOOTBALL_STEP05_2026-10-25.md), [zagregowane dane](../data/audits/API_FOOTBALL_STEP05_2026-10-25.json).
- **Test główny:** [GitHub Actions #40218310521](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40218310521); 30/30 kombinacji, 10 679 rekordów terminarza, 60/60 próbek statystyk, 112 zapytań, 0 błędów, 6 testów PASS.
- **Niezależna kontrola:** [GitHub Actions #40218180472](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40218180472); 25/25 liczebności zgodnych, 131 zapytań, 0 błędów, 5 testów PASS.
- **Nie stwierdzono pełnego pokrycia wszystkich meczów:** pojedyncze braki danych, ograniczona dostępność historycznych kursów, brak pomiaru rzeczywistych opóźnień. Przenieść do 09–10 i 19.
- **Status:** PASS; nie rozpoczęto nowego modelu ML ani kroku 06. Bez nowych opłat.


## GATE 06 — BLOKADA / DO POPRAWY (25.10.2026)

- **Cel:** sprawdzenie zakresu historycznych xG strzałów w PitchAPI i próbek dopasowań do API-Football.
- **Wykonano:** przygotowano [audyt](../scripts/pitchapi_step06_audit.py), [testy](../tests/test_pitchapi_step06.py) i [workflow](../.github/workflows/kb3-step06-pitchapi-audit.yml). Testy offline **7/7 PASS**.
- **Dowody FAIL:** [uruchomienie HTTPS #40220277718](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40220277718), [SDK #40220451559](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40220451559), [rozróżnienie HTTP #40220569321](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40220569321). PitchAPI `SDK_AuthError`, HTTP 401, zero katalogów/meczów/xG, bez ujawnienia klucza.
- **Wynik GATE:** **NIEZALICZONY**, wymagane sprawdzenie aktywności i ewentualna aktualizacja `PITCHAPI_API_KEY` w nowym repo. [Pełny raport blokady](STEP_06_BLOCKER.md).
- **Postęp:** nadal **5/29**. Bez nowych zakupów; bez zmian w historycznym KB2.1. Krok 07 jeszcze nierozpoczęty.

## Szablon następnego wpisu

```text
Data i strefa:
Krok / GATE:
Status poprzedni -> nowy:
Zakres:
Działania właściciela i asystenta:
Test (dokładny scenariusz):
Wynik PASS / FAIL + liczebności:
Dowody (konkretne URL i SHA):
Ryzyka / braki:
Odbiór techniczny / potwierdzenie właściciela:
Następny krok:
```

**Przypomnienie:** jeśli w kolejnym wątku brakuje kontekstu, najpierw przeczytać Google Docs i ostatnie dowody GitHub, nie zgadywać aktualnego stanu projektu.

## GATE 06 — rozwiązanie blokady i PASS / ZALICZONO (25.10.2026)

- Po zmianie klucza w GitHub Secrets ponowiono run #40220569321 (attempt 2). Job collect SUCCESS, 7/7 testów offline PASS, 0 błędów dostawców.
- Z 30 kombinacji liga×sezon 24 są dostępne, 6 (La Liga) nie zostały odnalezione w katalogu. Z 7301 rozegranych meczów wybrano 48 próbek; **48/48 z pełnym xG**. 14 dopasowań API-Football jednoznacznych, 6 jedynie kandydatów aliasowych.
- 73 wywołania PitchAPI, 24 API-Football; nowe zakupy 0 zł. Braki nie były zastępowane zerami. Odczyty xG po meczu nie są prognozami przedmeczowymi.
- Całe Actions run zakończyło się failure **wyłącznie z powodu odrzuconego git push non-fast-forward w jobie publikacji**, a nie z powodu błędu API lub testu danych. Oryginalne ZIP danych i Markdown zapisano na [Google Drive](https://drive.google.com/file/d/1y3z4EdkkNJHb0oiuyFLU5elFVTiJoa_k/view).
- [Protokół GATE 06](STEP_06_ACCEPTANCE.md), [run testów](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40220569321), [poprzednia blokada](STEP_06_BLOCKER.md). Krok 07 — niezależne mapowanie ID jeszcze nie rozpoczęte.

## GATE 07 — PASS / ZALICZONO (25.10.2026)

- **Zakres:** identyfikacja par tego samego meczu w API-Football i PitchAPI; walidacja próbki 60 spotkań/30 sezonów na podstawie danych obu źródeł, brak automatycznego dopasowywania niepewnych aliasów.
- **Pierwsza próba:** [Actions #40236350417](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40236350417) — FAIL celowo wykrywający godzinne przesunięcie przy Lyon–Auxerre, które wcześniejsza kontrola uznała za EXACT. Nie usuwano nieudanego testu.
- **Poprawiona wersja:** [Actions #40236615477](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40236615477) — SUCCESS, 17/17 testów, 30 odczytów, 38 STRICT, 22 REVIEW, 0 duplikatów, 0 realnych sprzeczności z poprzednimi ID.
- **Trwałe archiwum:** [Actions #40236771701](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40236771701) — PASS; [crosswalk JSON](../data/audits/STEP07_MATCH_CROSSWALK_2026-10-25.json) i [raport z kolejką 22](audits/STEP07_MATCH_CROSSWALK_2026-10-25.md) w `main`.
- **Odbiór:** [STEP_07_ACCEPTANCE.md](STEP_07_ACCEPTANCE.md) + [Plan i dziennik Google Docs](https://docs.google.com/document/d/10wjHL3r3OAuxtezwcIeWztxS8lwjhYon5GM3BLhI0xE/edit). GATE07 PASS oznacza bezpieczny mechanizm i audyt próbki, **nie 100% sparowania całej historii**.
- **Cechy przyszłej bazy:** jeden wewnętrzny fixture_id, zewnętrzne identyfikatory i status REVIEW; nieuprawnione dopasowanie blokować. Historię snapshotów przedmeczowych zachowywać oddzielnie.
- **Koszty:** 0 zł nowych zakupów; w kroku 07 wykorzystano 60 zapytań API-Football w dwóch testach (30+30). Nie było nowego pobierania PitchAPI xG.
- **Następny krok:** 08 — projekt bazy danych i archiwizacji, NIE ROZPOCZĘTY.

## GATE 08 — PASS / ZALICZONO (25.10.2026)

- Temat: migracje SQLite, mapowanie dostawców, unikalność meczów, prognozy immutable, backup+restore.
- [Schemat v1](../migrations/001_initial_schema.sql), [silnik backup/restore](../src/kb3_storage.py), [protokół GATE 08](STEP_08_ACCEPTANCE.md).
- Testy: [Actions 40241295913](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40241295913) PASS 9/9; [Actions 40241611841](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40241611841) PASS 9/9 po wymuszeniu syntetycznego trybu niezaszyfrowanego backupu.
- Kopia w [Google Drive](https://drive.google.com/file/d/1DkaIfH24qf7z_KDuwbMzRuUd_iORbFxb/view), backup ID 20261025T224033196429Z-95353b524e, SHA-256 ae76048deebd45bc0d97f21b189859fec0ae42f5e69ca51eb197c7b0ad6fe80f. Po ponownym pobraniu z Drive: CRC OK, SHA OK, SQLite integrity ok, restore 1 syntetycznego meczu. [Manifest](../data/audits/STEP08_BACKUP_MANIFEST_2026-10-25.json).
- Ograniczenia: backup zawiera wyłącznie fikcyjne dane. Szyfrowanie i automatyzacja produkcyjnej archiwizacji oraz retencja wymagają kolejnych odbiorów; 22 niepewne pary pozostają REVIEW.
- Zero nowych opłat, bez importu realnych meczów i bez modelu ML. Plan główny [Google Docs](https://docs.google.com/document/d/10wjHL3r3OAuxtezwcIeWztxS8lwjhYon5GM3BLhI0xE/edit). Następny krok 09 — NIE ROZPOCZĘTO.


## GATE 09 — START / W REALIZACJI (26.10.2026)

- **Stan wyjściowy:** GATE 01–08 PASS; 8/29 zaliczonych. Odczytano aktualny plan Google Docs i protokół GATE08 przed rozpoczęciem.
- **Zakres pilota:** Premier League, API-Football liga 39, sezon startowy 2024 (2024/25), według [Issue #1](https://github.com/karolbarankiewicz1984-ui/kb-score-3/issues/1).
- **Punkt odniesienia:** audyt GATE05 wskazał 380 meczów w 2024/25; potwierdzenie aktualnym importem pozostaje do wykonania.
- **Kryteria:** realny odczyt i zapis do SQLite v1, manifest z checksumami i stanami, uzgodnienie liczebności, drugi import bez duplikatów, wznowienie po przerwaniu. Odmienione lub sprzeczne identyfikatory kierować do REVIEW. Realne dane nie mogą trafiać do niezaszyfrowanego backupu testowego.
- **Status:** W REALIZACJI, GATE09 **PENDING**. Utworzono zadanie i rozpoczęto przygotowanie; **nie wykonano jeszcze importu**, dlatego nie wolno oznaczać PASS.
- **Koszt:** 0 zł nowych zakupów; brak zmian KB Score 2.1, brak uruchomienia ML i raportów produkcyjnych.

## GATE 09 — PASS TECHNICZNY / ZALICZONO (26.10.2026)

- **Próba:** Premier League 2024/25 (API-Football ID 39), 380/380 spotkań, 380 zakończonych, 380 unikatowych identyfikatorów źródłowych. [Run #40277192712](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40277192712) — SUCCESS.
- **Test odbioru:** 10/10 testów nowego importu + 9/9 regresji bazy (19/19 PASS); pierwszy import 380 nowych, powtórny 0 nowych/380 rozpoznanych; przerwanie po 17, następnie 363 dodane/17 rozpoznanych. Tabele SQLite 380 meczów i 380 map API-Football. Dane tylko RETROSPECTIVE.
- **Dowód trwałości:** zaszyfrowana AES-256-GCM baza w [prywatnym Google Drive](https://drive.google.com/file/d/1S1blIbulStO8TZBvwu8JgVERPU-WsdDU/view). Ponownie pobrano plik z Drive, sprawdzono identyczny hash bajtów, odszyfrowano, uzyskano SHA-256 oryginalnego SQLite, integrity_check=ok, foreign_key_check=0, odczytano 380 meczów. [Manifest](../data/audits/STEP09_IMPORT_2026-10-26.json), [GATE09 protokół](STEP_09_ACCEPTANCE.md).
- **Ograniczenia:** punktowy pilot 1 liga/1 sezon; zero ML, brak kursów, xG i statystyk drużyn; odzyskiwanie wymaga oddzielnego klucza przekazanego użytkownikowi jako osobny plik, którego bezpieczne zachowanie nie jest jeszcze potwierdzone. Szyfrowane backupy cykliczne i rotacja kluczy nie są uruchomione. Nierozstrzygniętych 22 par PitchAPI nie zatwierdzano.
- **Odbiór:** PASS techniczny zgodnie z bramką kroku 09; **postęp 9/29**. Nowe zakupy 0 zł. Następny krok 10 — dane: jakość i chronologia, **NIE ROZPOCZĘTO**.


## GATE 10 — START / W REALIZACJI — 26.10.2026

- **Zależność:** GATE09 odebrany, istnieje pełny pilotażowy sezon Premier League 2024/25; trening KB3 nadal nieuruchomiony.
- **Utworzono:** [audyt](../scripts/step10_quality_audit.py), [16 testów](../tests/test_step10_quality_audit.py), [workflow](../.github/workflows/kb3-step10-quality-gate.yml), [Issue #2](https://github.com/karolbarankiewicz1984-ui/kb-score-3/issues/2).
- **Test na rzeczywistych danych:** [Actions #40278994874](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40278994874) — SUCCESS. 35/35 unit+regression PASS (16+10+9), cztery błędy w kopiach prawdziwej bazy rozpoznane i zablokowane, 380/380 meczów, 20 zespołów, bez naruszeń chronologii terminarza i unikatowych identyfikatorów.
- **Wynik:** `PASS_WITH_COVERAGE_WARNINGS` dla jednego sezonu. Krytyczne błędy: 0. Brak zaimportowanych statystyk, kursów, zdarzeń i potwierdzonych snapshotów sprzed meczu. Trening: `training_allowed=false`. [Raport](STEP_10_PROGRESS.md), [QA JSON](../data/audits/STEP10_QUALITY_2026-10-26.json), [próby negatywne](../data/audits/STEP10_NEGATIVE_TESTS_2026-10-26.json).
- **Decyzja:** **GATE10 NADAL W REALIZACJI**, bo pierwszy audyt nie potwierdza całego docelowego zakresu lig ani jakości pozostałych źródeł. Nie udajemy PASS produkcyjnego. **Postęp: 9/29**, bez zakupów i modyfikacji KB2.1. Kolejne prace: zakres lig, pokrycie pól oraz weryfikacja chronologii dla danych używanych w przyszłych cechach.


## GATE 10 — ODBIÓR KOŃCOWY / PASS — 26.10.2026

- [Pełny protokół](STEP_10_ACCEPTANCE.md) i [manifest](../data/audits/STEP10_FINAL_2026-10-26.json) zastępują wcześniejszy status W REALIZACJI dla tego samego etapu (zachowując historyczny zapis startu).
- [Actions #40280361413](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40280361413): audyt wszystkich pięciu lig i 30 kombinacji sezonów (2021–2026), 10 679 rekordów terminarza / źródła, bez krytycznych błędów API. Audyt 5 bieżących sezonów 2026/27 nie oznacza, że mecze są już zakończone.
- [Actions #40280931156](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40280931156): **54/54 testów PASS**, 10/10 historycznych anomalii sklasyfikowanych po realnej fazie rozgrywek (regular season, relegation round/final). **19** baraży i spotkań rozstrzygających wyodrębniono, zamiast usuwać jako duplikaty; **1** przyznany wynik `AWD` w Ligue1 2025/26 (API-F ID **1388000**) pozostaje w kwarantannie normalnych etykiet.
- W 25 zakończonych sezonach źródło raportuje **8908** wpisów rundy zasadniczej, z czego **8907** to zwykłe wyniki będące potencjalnymi etykietami dopiero po przyszłym kontrolowanym imporcie. Jedyna faktycznie zaimportowana do SQLite historia w KB3 to wciąż **380 meczów Premier League 2024/25**.
- Negatywne przypadki dowodzą blokad: brak dowodu czasu zakończenia meczu źródłowego, informacja po cutoff, wynik badanego spotkania w jego własnej cesze, błędne daty, brak wyniku i uszkodzone mapowanie. Prematch xG/stats/odds brak w aktualnej bazie; **trening_allowed=false, brak ML i typów KB3**.
- Raporty pełne: [prywatne Drive – 30 sezonów](https://drive.google.com/file/d/1duA2TFr00dggF0zCcOVLAHlF2RpJjJIH/view) i [prywatne Drive – wykluczenia faz](https://drive.google.com/file/d/1Lu44F_j8fNugCIJICx12nJpxtkK4ZoEN/view).
- **GATE10 = PASS. Postęp 10/29. Krok 11 — NIE ROZPOCZĘTO. Nowe zakupy 0 zł.** Projekt KB2.1/API Market/MultiModel nietknięty.

## GATE 11 — START / W REALIZACJI (26.10.2026)

- **Zakres:** cechy przedmeczowe ELO, forma 5/10/15, home/away, siła przeciwnika, gole, opcjonalne rzeczywiste xG; jawne timestampy, lineage i maski NULL.
- **Implementacja:** [src/kb3_features.py](../src/kb3_features.py), [testy](../tests/test_step11_features.py), [pilot](../scripts/step11_features_audit.py), [katalog](STEP_11_PROGRESS.md).
- **Test CI:** [Actions #40283222459](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40283222459) — SUCCESS; 11/11 nowego modułu + 39/39 regresyjnych = **50/50 PASS**. Rzeczywisty import kontrolny: 380/380 meczów PL 2024/25.
- **Audyt:** 371/380 meczów miało wcześniejszą historię przy *retrospektywnym replay*; **0** historycznych obserwacji spełniło pełny wymóg publikacji/przechwycenia przed dawnym meczem. System nie oznacza retrospektywnej historii jako certyfikowanego prematch.
- **Klasyfikacja:** GATE 11 **PENDING / W REALIZACJI**, postęp **10/29**. Parametry ELO tylko robocze; brak ML, źródłowych historycznych snapshotów xG, nowych zakupów i zmian KB2.1/API Market/MultiModel. Dalszy niezależny odbiór dowodów i akceptacja katalogu przed PASS.

## GATE 11 — DODATKOWY PROGRES ELO I DWÓCH SEZONÓW (26.10.2026)

- [Actions #40289840095](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40289840095) potwierdza **58/58 testów PASS**, osobne pilotaże **380/380 i 760/760** oraz brak podniesienia klasy historycznych danych do `VERIFIED_PREMATCH`.
- ELO przechodzi między sezonami **tej samej ligi**, z jawnie prowizorycznym `season_retention=0.85` i parametrami K=20, H=65, scale=400, initial=1500; brak optymalizacji. Odrębne ligi i przyszłe sezony są odrzucane.
- Dwa zakończone sezony Premier League zaimportowano w **tymczasowym jobie CI**, 23 kluby, idempotentnie, w obu przypadkach 380 spotkań. To **nie jest trwałe powiększenie dotychczasowego archiwum**.
- `GATE11 = PENDING`, postęp **10/29**. Brakuje oryginalnego dowodu dostępności historycznej przed cutoff, rzeczywistych xG i trwałego zaszyfrowanego archiwum szerszego zestawu. Trening zablokowany, bez zakupów.

## GATE11 — kontrola pochodzenia xG i wyników (26.10.2026)

- [Actions #40292159243](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40292159243) — **66/66 PASS** (27 testów Step11 + 39 regresyjnych). Sprawdzono rozdzielenie dostawców wyniku i xG, zakaz użycia REVIEW/PENDING oraz niezgodnych snapshotów, odmowę zaufania staremu snapshotowi po zmianie wiersza wyniku.
- [Actions #40291895443](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40291895443) — **PitchAPI 12/12** kompletne xG obu drużyn w małej, celowej próbce PL 2023/24 i 2024/25; **8/12** dokładnych zgodnych par API-Football; **4/12** niezatwierdzone; 15 zapytań PitchAPI i 2 API-Football, 0 nowych zakupów.
- Kontrola wykonana bez publikowania surowych xG, pełnej bazy, wyników pojedynczych spotkań czy kluczy. Nie posiadamy dowodu row-hash oraz historycznego czasu publikacji xG; **0/12** z certyfikacją historycznego PIT. Odczyt tych wartości teraz nie może zostać uznany za przeszły snapshot.
- **GATE11 PENDING, 10/29**, brak treningu, historyczny zbiór 760 wyłącznie tymczasowy; starsze modele nietknięte.

## GATE11 — ARCHIWUM 760: OFFSITE RESTORE PASS (26.10.2026)

- [Actions #40293935946](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40293935946): 6/6 testów szyfrowania i odtwarzania PASS, 760 rzeczywistych fixture w 2 sezonach, zaszyfrowane `KB3ENC2` + RSA-OAEP-SHA256/AES-256-GCM. Brak surowej bazy w artefaktach i logach; klucz prywatny przechowywany oddzielnie poza GitHub i Drive.
- [Zaszyfrowane archiwum Google Drive](https://drive.google.com/file/d/1lA1Z2qNSWyGxn_6OcyFl3ZmK147BWsn-/view?usp=drivesdk) **pobrano ponownie z Drive**, niezależnie odszyfrowano i sprawdzono: zgodny SHA-256, `integrity_check=ok`, `foreign_key_check=0`, 760 map, 380+380 wyników. Manifest [SHA i ID](../data/audits/STEP11_760_OFFSITE_RESTORE_2026-10-26.json), [protokół](STEP_11_OFFSITE_ARCHIVE.md).
- **GATE11 nadal PENDING, 10/29.** To trwała, poprawnie odtwarzana historia wyników, nie historyczne archiwum przedmeczowych obserwacji ani pełne xG. Rzeczywista dostępność dawnych wyników przed dawnymi meczami nadal nie jest certyfikowana. Nowych zakupów brak, ML zablokowany, starsze modele nietknięte.

## GATE11 — PIERWSZY RZECZYWISTY SNAPSHOT OBSERVED-AT — 26.10.2026

- Wpisanie źródłowego API-Football PL 2026/27 do odrębnego, niezmienialnego hash-chain (pełna odpowiedź i 380 rekordów); zapis czasu pobrania **09:01:49 UTC**, 80 rezultatów końcowych i 300 wydarzeń jeszcze przyszłych. [Test realny #40296430026](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40296430026) SUCCESS. Tego znacznika NIE wolno cofać do daty meczu; provider `published_at` pozostaje NULL.
- [Zaszyfrowany backup obserwacji](https://drive.google.com/file/d/1wvFMLiSQHUP06-r95iNwp9nyBfYbsBoP/view?usp=drivesdk) przesłano do prywatnego Google Drive i pobrano ponownie. Dekryptacja tym samym kluczem użytkownika i walidacja 380 rekordów, SHA, SQLite oraz kluczy obcych zakończone sukcesem. [Manifest](../data/audits/STEP11_PIT_LIVE_CAPTURE_2026-10-26.json).
- [CI offline #40296978637](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40296978637) **82/82 PASS**. Usunięto możliwość podłożenia starego wyniku FT w miejscu nowszej korekty; nowa rzeczywista sesja API wymaga osobnego ręcznego uruchomienia. Nie ma automatycznego harmonogramu API.
- **GATE11 PENDING / 10/29**, brak ML i typów, starsze modele bez zmian. [Opis](STEP_11_PIT_OBSERVATION.md).

## GATE11 — DWIE OBSERWACJE I xG W KWARANTANNIE (26.10.2026)

- Dwa odczyty `API-Football fixtures?league=39&season=2026`: **380/380** tych samych meczów, 0 zmienionych hashy rekordów między 09:01:49 UTC i 09:20:47 UTC. Oba odrębne zaszyfrowane archiwa pobrane z Google Drive, odszyfrowane dotychczasowym kluczem prywatnym, SQLite integrity=ok / FK=0. [Manifest](../data/audits/STEP11_TWO_PIT_XG_2026-10-26.json).
- W drugim snapshotcie **3/3** kompletne feedy xG PitchAPI, ale **0/3** dokładnych par, z czego 2 AMBIGUOUS_OR_UNMATCHED, 1 ALIAS_CANDIDATE_UNVERIFIED. Kwarantanna, bez ręcznego przypisania lub imputowania zera.
- [91/91 offline PASS](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40298663945). [Rzeczywisty drugi zapis](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40298805124). [Protokół](STEP_11_TWO_PIT_XG.md).
- `GATE11 PENDING`, 10/29; `training_allowed=false`; brak nowego abonamentu i zmian w starszych modelach.

## GATE11 — 3/3 XG IDENTITY REVIEW (26.10.2026)

- [Realny audyt źródłowy #40301238526](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40301238526): brak błędów dostawcy, 3/3 feedy xG kompletne; po inspekcji hashy, czasu, wyników i ID obu drużyn zdefiniowano **3 konkretne powiązania** w [zamrożonym manifeście](../config/step11_reviewed_pitch_fixture_crosswalk_20261026.json), z zakazem promowania ogólnych aliasów.
- Dziennik źródłowy pozostał w kwarantannie i bez modyfikacji. Dopiero oddzielna audytowalna warstwa pochodna `kb3_reviewed_xg` dała **3/3 zatwierdzone mapowania historycznej obserwacji** na rzeczywistym odszyfrowanym archiwum Drive, bez przyszłych przecieków. [Protokół](STEP_11_XG_IDENTITY_REVIEW.md), [dowód](../data/audits/STEP11_XG_MATCHBOUND_REVIEW_2026-10-26.json).
- [111/111 testów PASS](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40302235918). Pierwotny `published_at` dostawcy nadal nieznany, pełne pokrycie brak, `GATE11 PENDING`, 10/29, ML/trening/typy zablokowane; brak zmian w starych modelach i nowych zakupów.

## GATE11 — OBSERVED-AT PRZECHODZI DO ELO/FORMY, 125 TESTÓW (26.10.2026)

- `src/kb3_features.py` v0.4 ma jeden wspólny kalkulator ELO/formy i trzy źródła: `replay`, `verified`, nowy `observed`. `src/kb3_observed_features.py` pobiera tylko źródło faktycznie zarejestrowane przed cutoff; historia targetu jest wyłączona. Rozliczenie xG po osobno potwierdzonej dacie GitHub review commit 09:53:09 UTC.
- [CI #40306542175](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40306542175) 125/125 PASS (86 Step11 + 39 regresja).
- Niezależne sprawdzenie realnej odszyfrowanej bazy 380 źródłowych spotkań z Drive i finalnego kodu [#40306671705](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40306671705): 80 prawidłowo dostępnych wcześniejszych wyników dla przyszłego Bournemouth–Leeds, reviewed xG Leeds 1 w oknie 5 **dopiero po** zatwierdzeniu powiązania, 0 przed; bez review również 0. [Protokół](STEP_11_OBSERVED_FEATURES.md), [manifest](../data/audits/STEP11_OBSERVED_BUILDER_REAL_DRIVE_2026-10-26.json).
- Nadal **GATE11 PENDING, 10/29, training_allowed=false**. ELO K/H bez treningu, starsze modele bez zmian.

## GATE11 — 10 dodatkowych prawdziwych xG + bezpieczne drugie archiwum (26.10.2026)

- Audyt [#40308346204](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40308346204): 10 meczów / 10 dat, kompletność xG 10/10, **5** ścisłych par, **5** w kwarantannie (4 × alias, 1 × mismatch), 12 PitchAPI + 1 API-Football, 0 błędów, 0 nowych zakupów.
- Encrypted ZIP [Drive](https://drive.google.com/file/d/1l0Ng06QDIqM1h8IUH9m3Z8aER4f_COdC/view?usp=drivesdk) z niezależnym odtworzeniem 380 rezultatów/10 xG i SQL integrity=ok/FK=0. Nowy `kb3_external_xg_asof.py` umożliwia bezpieczny odczyt xG z drugiej osobno hashowanej bazy przy zgodności source SHA i strict cutoff. Test na realnych dwóch archiwach: 80 historii + 1 nowe xG dla przyszłego meczu; przed capture i bez drugiego źródła xG 0.
- [140/140 CI PASS](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40309316442). [Raport](STEP_11_XG10_STRATIFIED.md), [manifest dowodów](../data/audits/STEP11_XG10_STRATIFIED_REAL_2026-10-26.json). **GATE11 PENDING 10/29**, brak historycznego PIT publikacji, `training_allowed=false`, stare modele bez zmian.

## GATE11 — ZMIANA KIERUNKU NA JEDNO ŹRÓDŁO PITCHAPI (26.10.2026)

- Usunięto przyczynę złożoności w **nowym torze testowym**: (PitchAPI native `m_ID` spina mecz, wynik i xG; bez łączenia do API-Football). 5 historycznych niezweryfikowanych aliasów nadal jest w kwarantannie, lecz nie wymaga dopasowania w nowej architekturze.
- [Pilot 1140 meczów + 5 xG #40312167476](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40312167476) PASS; [UEFA + faule/kartki #40312704445](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40312704445) PASS. 14 wywołań PitchAPI łącznie, 0 API-Football. Katalog 77 lig; szczegółowa pokrywalność xG innych lig nadal niepotwierdzona.
- [160/160 testów #40313071652](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40313071652) PASS, w tym nowy `shadow_native` ELO/formy/xG bez lookahead. `config/STEP11_PROVIDER_POLICY.json` ustala PitchAPI jako preferowanego kandydata, bez produkcyjnej migracji danych i bez opłat.
- [Protokół](STEP_11_SINGLE_PROVIDER_DECISION.md). **GATE11 PENDING 10/29**, brak treningu i zmian wcześniejszych modeli; retro PIT nie poświadczony.

## KROK11 — NATYWNY REJESTR PitchAPI, HASH CHAIN + OFFSITE RESTORE (26.10.2026)

- [Rzeczywisty run #40315374235](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40315374235): pełny sezon PL 2026/27 (380 fixture), 5 xG, sześć sesji PIT, 385 niezmiennych rekordów, 7 zapytań PitchAPI, **zero API-Football**.
- Zaszyfrowany backup w [prywatnym Google Drive](https://drive.google.com/file/d/18AeQOY7it5F58S4EqHKk8GDpqOD_TtUg/view), pobrany ponownie i odszyfrowany dotychczasowym kluczem prywatnym: 385/385 hashy i pełny łańcuch sesji, SQLite integrity=ok, FK=0. Klucz nie trafił do GitHub.
- Natywny append-only ledger, osobne RSA+AES archiwum i odczyt as-of do wspólnego ELO/formy/xG. [175/175 PASS](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40316210520). [Raport](STEP_11_PITCH_NATIVE_PIT_ARCHIVE.md).
- **GATE11 PENDING, 10/29**, brak certyfikowanego historycznego PIT, brak treningu i produkcyjnego przełączenia.

## GATE11 — 12/12 xG PitchAPI UEFA i bezpieczne zaszyfrowane dowody (26.10.2026)

- [15-call realny audyt #40318301119](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40318301119): **6/6** Liga Europy i **6/6** Liga Konferencji 2026/27, kompletne xG tylko z natywnych meczów PitchAPI, zero API-Football. Próbki są rozłożone odpowiednio na 4/2 daty, nie poświadczają pełnego pokrycia ligi.
- 15 pełnych odpowiedzi + rzeczywiste czasy + SHA-chain zaszyfrowano. [Kopia na Google Drive](https://drive.google.com/file/d/1LdmMRLmtaObUK7gs9r55D6950jTMCwxF/view) została pobrana drugi raz; SHA ZIP i szyfrogramu PASS. **Odtworzenie prywatnym kluczem jeszcze nie wykonane**.
- [187/187 PASS](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40318219204). [Pełny protokół](STEP_11_UEFA_NATIVE_XG_COVERAGE.md). **GATE11 PENDING 10/29**, brak autoryzacji treningu i zmiany produkcji.

## GATE11 — INDEPENDENT RESTORE UEFA ZAMKNIĘTY, KONTROLA REWIZJI PITCHAPI (26.10.2026)

- Ponownie pobrana [zaszyfrowana kopia UEFA na Google Drive](https://drive.google.com/file/d/1LdmMRLmtaObUK7gs9r55D6950jTMCwxF/view) została **rzeczywiście odtworzona** posiadanym kluczem właściciela poza GitHubem. SHA ZIP i szyfrogramu, fingerprint odbiorcy, RSA-OAEP, uwierzytelnianie AES-GCM, SHA rozpakowanej treści, **15/15** oryginalnych SHA odpowiedzi oraz pełny hash-chain **PASS**.
- Dodano `kb3_pitch_native_drift.py`, `step11_pitch_native_drift_audit.py`: dwa zweryfikowane snapshoty PitchAPI można odtwarzać i porównywać po dokładnym provider-native ID, oddzielnie licząc zmiany dat/statusu/wyniku/nazwy. Identyfikatory drużyn i pełen skład ligi są chronione przed milczącą podmianą. Skrypt nie wywołuje API i nie udostępnia nazw/ID w raporcie.
- [199/199 testów CI](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40320084066) PASS. **Drugi autentyczny odczyt nie został wykonany, wielodniowy diff pozostaje PENDING**; nie generowano fikcyjnych snapshotów. [Raport](STEP_11_UEFA_NATIVE_XG_COVERAGE.md).
- GATE11 **PENDING, 10/29**, trening i produkcja pozostają zablokowane.

## GATE11 — DWIE NIEZALEŻNE AUTENTYCZNE OBSERWACJE PITCHAPI W JEDNYM DNIU (26.10.2026)

- [Drugi realny run #40321588543](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40321588543): 380 mecze PL 2026/27 i 5 shot xG; kolejna osobna hash-chained kopia z rzeczywistym timestampem 12:19 UTC, pierwsza 11:29 UTC. Siedem kontrolowanych zapytań PitchAPI, zero API-Football.
- [Nowy szyfrowany backup Google Drive](https://drive.google.com/file/d/1X27ol04hWczbRCKin_pcKeiyVcLeF_x7/view) niezależnie ponownie pobrany, odtworzony prywatnym kluczem właściciela poza GitHubem, 385/385 SHA, pełny chain i integralność SQL PASS.
- Porównanie 380 źródłowych meczów oraz pięciu powtórzonych xG: **zero różnic** w datach, wynikach, statusach, team ID i payloadach xG. SHA całych odpowiedzi fixture identyczny. [Szczegóły](STEP_11_NATIVE_SECOND_REAL_CAPTURE.md).
- **Nie nazywać wyniku audytem wielodniowym.** GATE11 PENDING 10/29, bez produkcyjnego przełączenia i treningu, starsze modele bez zmian.

## GATE11 — naprawa read-only i bezpieczne otwieranie dwóch szyfrowanych źródeł (26.10.2026)

- `kb3_pitch_native_ledger.verify` nie wykonuje już DDL na otwartym `mode=ro`, co zapobiega fałszywemu błędowi podczas sprawdzania niezależnie odszyfrowanych archiwów. `step11_pitch_native_compare_offsite_zip.py` wykonuje lokalny restore dwóch szyfrogramów i porównanie po natywnych PitchAPI ID, z kontrolą whitelist ZIP i bez drukowania klucza prywatnego.
- [206/206 testów offline PASS](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40322588669): 167 Step11 +39 regresyjnych, w tym 7 nowych przypadków ZIP/readonly. Prawdziwy drugi odczyt i brak zmian w 380 meczach dokumentowano wcześniej w [raporcie](STEP_11_NATIVE_SECOND_REAL_CAPTURE.md). GATE11 wciąż PENDING, 10/29, bez treningu.

## GATE11 — WERSJA CECH 0.5, SZCZEGÓŁOWY ZEGAR DOSTĘPNOŚCI KAŻDEGO POLA (26.10.2026)

- `src/kb3_step11_field_audit.py` + wspólny `_compose_features`: dla wszystkich cech `observed` i flag missingness zapisuje konserwatywny, oryginalnie zaobserwowany czas danych, zakres i hash źródła; sprawdza wszystkie rezultaty, xG i approval przed cutoff. Retrospektywne `replay` ma `feature_availability=null`, nie certyfikację.
- [217/217 CI PASS](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40325431132), 11 nowych testów czasu / odrzucania leak i 39 wcześniejszych regresji. [Katalog pola-po-polu](STEP_11_FIELD_PROVENANCE_GATE.md).
- Ograniczenie: `PitchAPI-native` obecnie liczy ELO tylko z sezonu 2026/27, nie z importu sezonów wcześniejszych; potrzebne jest jawne rozszerzenie, bez udawania historycznego PIT. GATE11 nadal PENDING, 10/29. Produkcja, trening, starsze modele bez zmian.

## GATE11 — API-Football HISTORYCZNE PILOTY TYLKO RĘCZNIE (26.10.2026)

- Po scaleniu zmian do głównego kalkulatora stary workflow ponownie pobierał dane API-Football dla pilotów 380 i 760, choć nowy system ma korzystać z samego PitchAPI. Zmieniono `.github/workflows/kb3-step11-features.yml`: joby `pilot-380` i `pilot-760` mają teraz warunek **wyłącznie `github.event_name == 'workflow_dispatch'`**. Historyczne testy zostają zachowane do świadomego uruchomienia; na push/PR działają tylko testy offline.
- [Rzeczywisty CI #40326752798](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40326752798): **220/220 testów offline PASS**, oba zadania wymagające API-Football **SKIPPED**. Dodano 3 testy zabezpieczające taką politykę na przyszłość.
- Bez nowego abonamentu, bez zakupów, bez produkcyjnej migracji i treningu. GATE11 **PENDING 10/29**.

## KROK11 — PRAWDZIWE WIELOSEZONOWE ELO PITCHAPI 2023/24–2026/27 (26.10.2026)

- [Jednorazowe PitchAPI #40329303189](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40329303189): 3 kompletne poprzednie sezony 3×380=1140 meczów, 20 drużyn/sezon, 17 stabilnych ID między sezonami; 4 zapytania PitchAPI, zero API-Football.
- Backup [Google Drive](https://drive.google.com/file/d/1_wLVJtOSwjwQwHhjBa54-3f0-aCzhyqJ/view) pobrany ponownie, AES+RSA i SHA-chain 4 źródeł odtworzone lokalnie PASS. Brak prywatnego klucza lub surowych statystyk w repozytorium. Zapis 26.10.2026 jest RETROSPECTIVE i nie udaje wcześniejszych timestampów publikacji.
- Wielosezonowe ELO w `src/kb3_pitch_native_observed_features.py`: 1140 historycznych +80 bieżących prawdziwych wyników, 121 cech i 159 zweryfikowanych znaczników czasu. xG historii bez feedów pozostaje `null`, parametry ELO prowizoryczne. [231/231 CI PASS](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40330403055), [protokół](STEP_11_PITCH_MULTISEASON_ELO.md). **GATE11 PENDING 10/29**, bez treningu i modyfikacji starszych modeli.

## GATE11 — PITCHAPI XG 30/30 Z TRZECH LIG, OFFSITE RESTORE (26.10.2026)

- [Rzeczywisty odczyt #40334387182](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40334387182): PL 10/10, Liga Europy 10/10, Liga Konferencji 10/10 kompletnych strzałowych xG, **0 API-Football**. 34 odpowiedzi źródłowe zaszyfrowane RSA+AES, zapisane na [Google Drive](https://drive.google.com/file/d/1ddByW04Sw3bDLxq-h2P-HyvwRtuBI423/view), ponownie pobrane i niezależnie odszyfrowane z SHA/chain/source fixture/team ID **PASS**. Po odjęciu powtórzonych UEFA łącznie 38 unikalnych próbek kompletnego xG z trzech lig (10 PL + 14 LE + 14 LK).
- Pierwszy identyczny zakres (34 zapytania) nie zachował archiwum z powodu zbyt ścisłego wymogu co najmniej trzech dat Ligi Konferencji, gdy było ich tylko dwie. Poprawiono walidację, zabezpieczono upload przy nieudanym końcowym teście; łącznie **68 wywołań PitchAPI**, bez zakupów.
- [Szczegóły](STEP_11_THREE_LEAGUES_XG30_COVERAGE.md), [bezpieczny manifest](../data/audits/STEP11_THREE_LEAGUES_XG30_OFFSITE_2026-10-26.json). **GATE11 PENDING (10/29)**, 241/241 planowanych testów offline, nie certyfikowano kompletności całego sezonu ani oryginalnego momentu publikacji danych.

## 26.10.2026 — GATE11 PASS: pierwotny kontrakt cech przedmeczowych spełniony (11/29)

- Zamknięto krok 11 na podstawie trzech oryginalnych wymagań: opis/znacznik czasu każdej cechy i missingness, brak lookahead oraz `xG=null` zamiast sztucznego zera. [Protokół i zakres](STEP_11_GATE_ACCEPTANCE_2026-10-26.md) zawiera dowody i odstępstwa dotyczące przyszłych obserwacji między dniami.
- Pięć nowych testów egzekwuje oryginalne kryteria i zakaz treningu; [CI #40339012432](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40339012432) **246/246 PASS**, brak nowych odczytów API.
- Krok 12 gotowy do rozpoczęcia, GATE12 **NIEZALICZONY**; `training_allowed=false`, nie wolno mylić danych historycznych pobranych 26.10.2026 z rzeczywistymi historycznymi timestampami prematch. Stare modele nienaruszone, bez dodatkowych opłat.

## KROK12 — START: CHRONOLOGICZNY SPLIT I KONTROLA PIT (26.10.2026)

- **Stan przed:** 11/29 GATE11 PASS; STEP12 NIE ROZPOCZĘTO. **Stan po:** 11/29 PASS; STEP12 **W REALIZACJI / GATE12 PENDING**.
- Pierwszy kod `src/kb3_split.py` buduje deterministyczne, hashowane manifesty TRAIN (2023/24–2024/25), VALIDATION (2025/26), TEST (2026/27), cztery okna walk-forward oraz wstrzymanie nadpisywania zamrożonej wersji. 90-minutowe wyniki nie są ujawniane w manifeście. Chronologia oparta na rzeczywistym `kickoff_utc`, odczytach cech i datach zaobserwowania etykiet.
- Historyczne dane pobrane 26.10.2026 (`RETROSPECTIVE`) pozostają w **kwarantannie** i nie otrzymują statusu przeszłych autentycznych prognoz. Dopiero rzeczywisty `PROSPECTIVE_OBSERVED_AT` z pełnym katalogiem znaczników może przejść warstwę sprawdzającą; niezależny odbiór GATE12 nadal konieczny.
- Testy syntetyczne `tests/test_step12_split.py`, workflow `.github/workflows/kb3-step12-split.yml`. Wczesne uruchomienie wykazało błędny oczekiwany komunikat w jednym teście negatywnym (już skorygowany); ostateczny status i link CI wymagają potwierdzenia.
- [Opis i ograniczenia](STEP_12_PROGRESS.md). Nie użyto sekretów, nie wywołano dostawców API, nie uruchomiono treningu, brak nowego abonamentu i zmian starszych modeli.

## KROK12 — RZECZYWISTY SPLIT 1520 + KOPIA DRIVE (26.10.2026)

- [PitchAPI one-time GitHub Actions #40345911294](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40345911294) **PASS**. Pięć odczytów istniejącego PitchAPI (0 API-Football), Premier League cztery sezony po 380: 760 TRAIN, 380 VALIDATION, 380 TEST. W sezonie 2026/27: 80 zakończonych i 300 przyszłych; 1520 unikalnych natywnych fixture IDs.
- SHA splitu `da387303645a9bb9476351044944e5465d178ddff689c96b579093c4fb4fce3a`, [manifest](../data/splits/STEP12_NATIVE_REAL_SPLIT_2026-10-26.json), [źródłowy audyt](../data/audits/STEP12_NATIVE_REAL_AUDIT_2026-10-26.json); rzeczywiste historyczne odczyty RETROSPECTIVE, brak iluzji historycznej informacji prematch.
- [Pakiet RSA+AES w folderze Google Drive](https://drive.google.com/file/d/1j56rqRA8SnVYi1g65dbfwPaXHH96GzhB/view): pobrany ponownie, ZIP 115137 B, SHA ZIP `191554843271756b0f472432719c00477c6a14bea255f403b25d17c6cfb9dbce`. Zgodność ciphertext SHA / wewnętrznego manifestu / manifestu splitu oraz 1520 IDs [PASS](../data/audits/STEP12_OFFSITE_CIPHERTEXT_READBACK_2026-10-26.json); surowy RSA restore **NIE** wykonywany bez prywatnego klucza.
- **Stan po:** nadal **11/29**, krok 12 **W REALIZACJI / GATE12 PENDING**, ponieważ **0** rekordów spełnia historyczne kryteria PIT dla treningu. Nie uruchomiono ELO/Poissona/ML, nie było żadnego zakupu ani zmian innych modeli.

## Krok 12 — 26.10.2026, niezależna ocena oryginalnych wymagań

- Przeczytano raz jeszcze plan Google Docs i GitHub: odbiór dotyczy podziału i walk-forward, integralności oraz separacji wyników; pełna historyczna dostępność xG NIE jest dopisana do pierwotnej bramki kroku 12.
- Oryginalny plik metadanych zachowany, wykryty weń hash zależny od wyników: wyłącznie do audytu. [Zamrożony bezpieczny widok modelu](../data/splits/STEP12_SAFE_MODEL_VIEW_2026-10-26.json) nie ujawnia wyników ani tych hashy, [kontrola wersji](../data/audits/STEP12_INDEPENDENT_METHODOLOGY_2026-10-26.json).
- Rzeczywiste 1520 meczów w 3 częściach 760/380/380, 4 foldy 60/126/123/71 (razem 380 walidacyjnych), brak TEST w train/validation. [Protokół dla właściciela](STEP_12_METHOD_DECISION.md).
- **Stan:** metodologia przygotowana do akceptacji, brak zgody właściciela -> GATE12 PENDING, brak PIT -> `training_allowed=false`, wciąż 11/29. Starsze modele nietknięte.

## KROK12 — DWA PORÓWNYWALNE OKNA, 26.10.2026

- Po ponownym omówieniu planu wprowadzono porównanie EXPANDING (pełna starsza historia) vs ROLLING (ostatnie 24 miesiące) na tych samych rzeczywistych meczach VALIDATION. Kwartały: 60,126,123,71 meczów. Kandydaci po samych datach EXPANDING: 760,820,946,1069; ROLLING: 760,753,750,776.
- [Metodologia i dowód](STEP_12_DUAL_WINDOWS.md), [niezmienny manifest SHA 25242ed4a626aba2669ea86605b31664cb17bf10a6a74e4e3548470954c81198](../data/splits/STEP12_DUAL_WINDOWS_REAL_2026-10-26.json), [odrębny audyt](../data/audits/STEP12_DUAL_WINDOWS_AUDIT_2026-10-26.json), [CI testy PASS](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40353630051).
- 380 TEST nigdy nie trafia do treningu/walidacji. Wybór metody historii tylko na VALIDATION po dopuszczeniu danych i metryk. Nie wykonano treningu lub modelowych prognoz; źródło pozostaje 0/1520 gotowych próbek PIT, `training_allowed=false` i GATE12 PENDING do formalnego zamknięcia.

## 26.10.2026 — KOŃCOWY ODBIÓR METODYKI KROKU 12

**GATE12 PASS wyłącznie dla metodologii TRAIN/VALIDATION/TEST i porównania EXPANDING vs ROLLING.** [Samodzielny, zamrożony protokół odbioru](../data/audits/STEP12_METHOD_GATE_PASS_2026-10-26.json), rekord SHA `0332edf73cd893f9848ffb23ea7821a09f5c183e6add77fc7cfdd7378959c5be`. [Raport rzeczywistych blokad danych](../data/audits/STEP12_REAL_PIT_GAP_REPORT_2026-10-26.json): `1220` historycznych odczytów RETROSPECTIVE i `300` nadchodzących meczów z niezatwierdzonymi cechami; łącznie **0** dopuszczonych do treningu. Wcześniejsze wzmianki „PENDING” są zapisem stanu sprzed odbioru. Po potwierdzeniu przez użytkownika kontynuacji obu metod porównania i zaliczeniu testów programu protokół metody ma PASS, natomiast **`training_allowed=false`** i osobna bramka PIT pozostają w mocy. Krok 13 nie jest jeszcze rozpoczęty; dopasowywanie modeli, publikowanie prognoz lub fałszywe backtesty są zabronione.

## 26.10.2026 — Rozpoczęcie KROKU13 ELO + Poisson M0

Nowy niezależny moduł [src/kb3_step13_baseline.py](../src/kb3_step13_baseline.py) udostępnia standardowy oczekiwany wynik Elo, matematyczną aktualizację Elo po meczu i prognozę 1X2/Over/BTTS ze wspólnej niezależnej macierzy Poissona. Parametry nie są wyuczone, przykłady i [raport](../data/audits/STEP13_M0_REFERENCE_2026-10-26.json) są jawnie SYNTHETIC_ONLY, hash 38e08689a8d7ca81b96c9b4a8fa4ed8c6e75d5eef617f3f421bb839711c989ff. [Zasady i status](STEP_13_PROGRESS.md). Weryfikacja matematyczna w CI PASS, test realnego backtestu BLOCKED na niedopuszczonych danych Step12. Historyczne Brier, log-loss i kalibracja nie zostały policzone ani sfabrykowane. Krok13 NIEZALICZONY, GATE13 PENDING, 12/29.

## 26.10.2026 — KROK13 v0.2, fold replay bez przecieku wyniku

Wdrożono [replay_synthetic_fold](../src/kb3_step13_fold_replay.py) i [testy](../tests/test_step13_fold_replay.py) dla obu metod TRAIN z kroku12. Elo aktualizuje się tylko wynikami historii znanej PRZED początkiem folda i po 48h embargo, wszystkie mecze walidacyjne otrzymują prognozy z zamrożonych ratingów, a etykiety są odczytywane do metryk dopiero potem. Test podmiany wyniku 2:0 na 0:7 nie zmienia P(1/X/2), zmienia jedynie sztuczny wynik oceny. Wydzielona realna kontrola [1520 fixture bez etykiet](../data/audits/STEP13_REAL_FOLD_READINESS_2026-10-26.json) SHA 814b58950a387ec206673203c51a494b1b82a3a199ab1f9b28f77dac4e84e29b potwierdziła 0 próbek dopuszczonych do treningu/realnego backtestu. [CI PASS](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40377868431). Dokument: [krok13 replay](STEP_13_REPLAY_CONTRACT.md). **Stan: GATE13 PENDING, training_allowed=false, 12/29.**

## 26.10.2026 — Dodatkowa kontrola prequential w kroku13, bez zmiany protokołu

W celu sprawdzenia subtelnych przecieków w walidacji dopisano osobny, niedopuszczony do produkcji moduł syntetycznej symulacji, w którym zakończone spotkania mogą aktualizować ELO dopiero po faktycznym `result_observed_at` i przed cutoff następnej prognozy. Odmiennie od oficjalnego kwartalnego, zamrożonego folda Step13 v0.2, wariant prequential jest **osobnym eksperymentem**, nie zmienia żadnego źródła, podziału ani warunków GATE13. 14 testów i niezmienny raport [STEP13_M0_SYNTHETIC_REPLAY_2026-10-26.json](../data/audits/STEP13_M0_SYNTHETIC_REPLAY_2026-10-26.json), SHA 68849afe0389e994b51e7ee2f55927fe9e875ca69d3e0d9433a3a8f232ec6d2e, [CI PASS](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40387731556). W raportowanym porównaniu **2 sztuczne mecze, 0 prawdziwych**. GATE13 PENDING; 12/29.

## 26.10.2026 — Krok13 v0.3: train-only dopasowywanie Poissona

Wdrożono funkcję optymalizacji bramek Poissona z profilowym analitycznym MLE średnich goli oraz siatką elastyczności ratingu Elo bez korzystania z VALIDATION i TEST. [Kod](../src/kb3_step13_poisson_train.py), [testy](../tests/test_step13_poisson_train.py), [raport 12 S Z T U C Z N Y C H meczów](../data/audits/STEP13_SYNTHETIC_POISSON_FIT_V03_2026-10-26.json), SHA256 55c28c220c140c00be0b3272c87053e2be13a580d3c58740e8fd506c9e9d3523, [CI PASS](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40395088065). Wykazano zdolność matematycznego dopasowania stawek rozkładu Poissona, bez zaglądania do etykiet walidacji i TEST. Dane rzeczywiste 1520 z kroku12: 0 dopuszczonych do fit, 0 rzeczywistych metryk. Prawdziwe szkolenie pozostaje niedozwolone; GATE13 PENDING, 12/29.
