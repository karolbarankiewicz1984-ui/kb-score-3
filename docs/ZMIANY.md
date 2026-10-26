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
