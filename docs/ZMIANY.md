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

## 26.10.2026 — Dalsza praca w obrębie istniejącego KROKU 13 (bez rozszerzania 29 kroków)

Zaimplementowano czterofoldowy historyczny eksperyment offline dla ELO+Poisson, wyłącznie jako `RECONSTRUCTED_EVENT_TIME_RESEARCH_NOT_VERIFIED_PIT`, i w pełni odseparowano go od prawdziwego stanu dostępności źródeł. Osobny lokalny program z kontrolą oryginalnych SHA ZIP/cipher/chain weryfikuje 1140 historycznych wyników i przypięty bezpieczny podział 760 TRAIN/380 VALIDATION, bez odczytu TEST. 48h to wyłącznie hipotetyczny czas wyników; odczyt źródła w 2026 r. pozostaje faktyczną datą zaobserwowania materiału. Offline CI testuje jedynie wymyślone źródło i fałszywe archiwum; brak klucza prywatnego w GitHub oznacza brak prawdziwych metryk do dziś. [Szczegóły](STEP_13_PROGRESS.md), [kod](../src/kb3_step13_retrospective.py), [program lokalny](../scripts/step13_pitch_retrospective_local.py). Nadal 12/29, KROK13 PENDING, no API cost, bez dopisywania zadań czy przebudowy kroków14–29.

## 26.10.2026 — Oryginalne archiwum PitchAPI niezależnie sprawdzone, nadal KROK13

Z pobranego ponownie z Google Drive rzeczywistego ZIP 31 907 bajtów, SHA 301bae69251d19a0192e12c2c033636b3f2822a15dcea2c4beaca28f4b45de2e, wyciągnięto jedynie zaszyfrowaną zawartość i manifest źródła. Szyfrogram 30 168 bajtów i SHA e5e14a2320e65f945a2709c4cd8dfb49ed38d45ccca3502b3e5ba7c21f84d343, proof-chain SHA 33c750f2db89a0df5faeba9348652a451f33548959839ff7bb0ca49210c2b367, trzy sezony po 380 rekordów deklarowanych — wszystko zgodne. [Weryfikator](../src/kb3_step13_archive_preflight.py) i [zamrożony realny no-decrypt raport](../data/audits/STEP13_ORIGINAL_SEALED_ZIP_PREFLIGHT_2026-10-26.json), SHA aa810e1afa293f103b8f50cbb00f46fca4eff7beacdb425ade16d469b5170e48. Przeprowadzono lokalnie 9 kontroli technicznych PASS. GitHub Actions nie daje teraz potwierdzenia CI, ponieważ właściciel otrzymał powiadomienie o wyczerpaniu 100% miesięcznych 2000 minut Actions; ostatnie uruchomienie FAILURE nie wytworzyło logów z kroków. Z uwagi na brak klucza nie odszyfrowano archiwum ani nie wyliczono prawdziwych metryk. GATE13 PENDING, 12/29, bez nowych pozycji w harmonogramie.

## 26.10.2026 — Przywrócone wykonywanie CI kroku 13 po aktualizacji konta GitHub

Ponowiono cztery nieudane przebiegi wynikające z wyczerpania limitu GitHub Actions. Ich druga próba na tym samym commitcie main (PR #34, 72e08315...) zakończyła się **SUCCESS**: [Retrospective Research](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40402095894), [Poisson TRAIN-only](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40402094465), [ELO+Poisson M0](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40402094411), [Fold Replay](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40402094393). Testy sprawdzają kod, archiwum ZIP *bez odszyfrowania* i izolację danych, nie sportową jakość na prawdziwych wynikach. Prywatny klucz pozostaje poza GitHubem, 1140 historycznych wyników niewczytanych, 0 realnych metryk, GATE13 PENDING. Nadal 12/29 kroków bez zmiany harmonogramu.

## 27.10.2026 — pierwszy rzeczywisty eksperyment retrospektywny KROKU13

Uruchomienie [GitHub Actions #40422326740](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40422326740) PASS: trzy bezpłatne odczyty PitchAPI; natywne parowanie 1140 meczów 2023/24–2025/26 z zamrożonym Step12 (760 TRAIN/380 VALIDATION; TEST 380 nieczytany). EXPANDING log loss 1.0326367404, Brier sum3 0.6185368951, ECE 0.0739533904; ROLLING 24 mies. odpowiednio 1.0343803886, 0.6196881659, ECE 0.0733160087. Brier i log loss z prawdziwych wyników, ale odtworzone po fakcie, bez dowodu dostępu do historycznie dostępnych przedmeczowych danych. [Zarchiwizowany wynik wyłącznie agregatowy](../data/audits/STEP13_REAL_RETROSPECTIVE_PITCHAPI_2026-10-27.json), SHA 3d950fff30b57c94a6f71462c7521cfda2cb0b27c666d59d09d274261efca803, [archiwizacja z tego samego przebiegu](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40422560884) PASS bez nowych wywołań API. GATE13 PENDING, training_allowed=false, 12/29, plan bez nowych kroków, klucz RSA pozostał u właściciela.

## 27.10.2026 — Diagnostyka zmienności kalibracji ELO+Poisson w KROKU13

Bez nowych danych ani zapytań API odczytano niezmienny [realny raport retrospektywny](../data/audits/STEP13_REAL_RETROSPECTIVE_PITCHAPI_2026-10-27.json) i przeliczono w kodzie [audytu stabilności](../src/kb3_step13_stability_audit.py) trafności maksymalnej klasy 1X2, kalibrację kwartalną i ECE. W I–III 2026 było **48/123 trafień = 39.0%** dla obu wariantów przy P top1 **49.7% EXP / 48.8% ROLL**. Pooled ECE 5-bin **0.01693/0.01033** maskuje niejednorodność kwartałów; fold-weighted ECE **0.07395/0.07332**. Expanding w sumie 185/380 trafień top1, Rolling 184/380; 8/8 dopasowań na górnej granicy siatki elastyczności Elo 0.6. [Raport dowodowy](../data/audits/STEP13_REAL_RETROSPECTIVE_STABILITY_2026-10-27.json), SHA256 10e75ea0a247ca3d446379238ac4f97aab6be90f8ee55aac6796cf7d83bdeb8e, [CI PASS](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40423988185). Metryki retrospektywne, nie rzeczywisty forward-PIT; nie dostrajano parametrów po wyniku walidacji, TEST nietknięty. Nadal krok13, GATE13 PENDING, 12/29, bez nowych etapów.

## 27.10.2026 — Kontrola elastyczności ELO tylko na TRAIN (krok13)

Uruchomiono badanie rzeczywistych wyników 760 meczów TRAIN na PitchAPI (2 sezony, 2 odczyty), bez VAL i TEST. Nowa siatka wyłącznie diagnostyczna 0.0–1.2 Poisson NLL daje minimum 1.0 na całym TRAIN (3.055322 na mecz), gdy pierwotna 0.0–0.6 daje minimum 0.6 (3.071748). Sezonowe minima diagnostyczne: 1.2 na brzegu oraz 0.9. Nie jest to poprawa log loss 1X2 na walidacji. Bez zmian produkcji, harmonogramu, parametrów, dopuszczenia treningu i kroku14. [Agregat](../data/audits/STEP13_TRAIN_760_ELO_ELASTICITY_DIAGNOSTIC_2026-10-27.json), SHA256 abaeaa142a6ab75301e964973724ce6f20cbf3efe137bd0b6c38e78a3412e846, [CI PASS](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40425365353). GATE13 PENDING, 12/29.

## 27.10.2026 — Sparowane przedziały niepewności ELO+Poisson, w oryginalnym kroku13

[GitHub Actions #40457581450 PASS](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40457581450), 3 bezpłatne historyczne odczyty PitchAPI, kontrola odtworzenia zamrożonych czterech foldów 380 meczów. Z identycznych per-match strat obu metod policzono jedynie sumaryczne różnice i deterministyczny bootstrap 3000 prób z 38 klastrami tygodniowymi. **Delta ROLL−EXP logloss=+0.0017436482, 95% [−0.0003789226,+0.0038354903]; delta Brier=+0.0011512708, 95% [−0.0004956491,+0.0027241987].** Obie niepewności obejmują zero, nie stwierdzamy przewagi EXPANDING. Utrwalono tylko agregatowy [raport](../data/audits/STEP13_REAL_PAIRED_UNCERTAINTY_2026-10-27.json), SHA e1a1694da3b43f944696b456521448015b855f47da8d91d181ee5d547a9d47d4. Bez TEST, bez zmiany Elo/Poisson, bez dodatkowej pozycji w 29 krokach. Retrospektywny event-time nadal nie jest rzeczywistym historycznym PIT, GATE13 PENDING, training_allowed=false, 12/29.

## 27.10.2026 — pierwsze rzeczywiście przedmeczowe prognozy (ciągle KROK13)

[GitHub Actions #40459673538 SUCCESS](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40459673538): 10 przyszłych meczów PL 2026/27 (31.10–02.11), źródło odczytano 2026-10-27T06:12:08.686916Z, prognozy zamrożono 2026-10-27T06:12:08.707287Z, więc przed kickoffem. Parametry M0 Poisson i Elo z przypiętego TRAIN 760, bez odczytu wyników VALIDATION i TEST. Z TEST wyłącznie przyszłe fixture ID i kickoff z `status=upcoming` oraz `score=None`. [Raport 10 prawdopodobieństw 1X2](../data/forecasts/STEP13_FIRST_PROSPECTIVE_PREMATCH_2026-10-27.json), SHA `9c346f79b1868fd1cb0d4d4ffa066f6f1629e09bbc6ce0454c5c8901e7645389`. Pierwszy test offline odrzucił niespójne sztuczne nazwy drużyn przed API, poprawiono fixture testowy. Brak zmian modelu, nowych kroków, bukmacherskich rekomendacji lub wiedzy o przyszłych wynikach. Ratingi kończą się na TRAIN 2024/25; celowo brak aktualizacji sezonu bieżącego (istotne ograniczenie). Weryfikacja trafności dopiero po rozegraniu meczów i odrębnym bezpiecznym odczycie wyników. **GATE13 PENDING, 12/29**.

## 27.10.2026 — Zamrożony przyszły protokół oceny pierwszych 10 prognoz, w kroku13

Przed kickoffem 31.10.2026 przygotowano [kontrakt oceny](STEP_13_FORWARD_SCORING_CONTRACT.md), implementację [`src/kb3_step13_forward_score.py`](../src/kb3_step13_forward_score.py) i tylko syntetyczne [testy](../tests/test_step13_forward_score.py). Podpis referencyjnych prognoz przypięto do SHA `9c346f79b1868fd1cb0d4d4ffa066f6f1629e09bbc6ce0454c5c8901e7645389`. Ocena może być wykonana dopiero po 2 listopada 23:00 UTC, po niezależnej autentycznej weryfikacji wszystkich 10 zakończonych meczów. Miary ustalone Z GÓRY (top1, log loss, Brier sum3, ECE opisowe, Poisson NLL/MAE), brak dopuszczenia innych 370 TEST, brak API dziś, brak zmiany dotychczasowych prognoz i parametrów ELO/Poisson. Jeżeli po rozliczeniu 10 wyników zostaną one ujawnione, nie mogą służyć do nowego strojenia modelu. GATE13 PENDING, 12/29; harmonogram i krok14 bez zmian.

## 27.10.2026 — Cztery kontrole żądane przez właściciela (po kolei w kroku13)

Niezależny audit 25 sztucznych par Elo i 10 zamrożonych prematch ELO+Poisson: [matematyka PASS](../data/audits/STEP13_MATH_INDEPENDENT_2026-10-27.json), CI #40465862824. Kontrola kodu źródłowego `played` tylko TRAIN, `upcoming` tylko TEST i nienaruszalności historycznie zamrożonych 10 prognoz: [leakage audit PASS](../data/audits/STEP13_LEAKAGE_INDEPENDENT_2026-10-27.json), nie certyfikuje starego PIT. Następnie [10 nowych realnie przedmeczowych prognoz na 6–8 XI 2026](../data/forecasts/STEP13_SECOND_PROSPECTIVE_PREMATCH_2026-10-27.json), SHA bca520ffd20021cf984189c6aa5a15eda078b5a501f32345c87c334d6c3b045e, CI #40466272044 PASS; razem 20, nadal TEST wyników 0, model niezmieniony. Na końcu przygotowano ścisły przyszły odczyt dokładnie oryginalnej pierwszej dziesiątki po meczach przez `matches.get`, osobne dowodowe czasy i łańcuch SHA, szyfrowanie AES-GCM/RSA i tylko agregatowe metryki, [offline test](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40466814515) PASS. Przyszły workflow jest RĘCZNY, żaden prawdziwy wynik nie był dziś pobrany. Nadal krok13, GATE13 PENDING, 12/29, brak strojenia i nowych kosztów.

## 27.10.2026 — Decyzja właściciela i GATE13_ORIGINAL_SCOPE PASS — krok 13 ZALICZONO

Wybrano opcję 1 z krótkim audytem z opcji 2: zgodnie z pierwotnym brzmieniem PLAN.md zakończono budowę baseline ELO+Poisson i testy historyczne w wyraźnie retrospektywnym trybie. Raport odbioru [STEP13_ORIGINAL_BASELINE_ACCEPTANCE_2026-10-27.json](../data/audits/STEP13_ORIGINAL_BASELINE_ACCEPTANCE_2026-10-27.json) SHA a4d26dc96bf75bf2073007e66c4445f61adcaed22611f5fa21c31d74a36e4718, [jednorazowy niezależny audyt Actions #40472267733](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40472267733) PASS. Zaliczenie **pierwotnego etapu technicznego**, a NIE dowód historycznego PIT, przewagi stabilnej, przydatności bukmacherskiej czy przepustka do treningu na źródłach z flagą `training_allowed=false`. Poprzednie raporty niezmienione. [Formalny protokół](STEP_13_FINAL_ACCEPTANCE_2026-10-27.md) opisuje 760 TRAIN / 380 VALIDATION, logloss/Brier/ECE, zaliczone kryteria i ograniczenia. Zmieniono licznik na **13/29**, krok14 **W REALIZACJI** w zakresie [samej specyfikacji i prób syntetycznych](STEP_14_KICKOFF.md); realny CatBoost jeszcze niewytrenowany, produkcja zabroniona, harmonogram 29 bez zmian. Zaplanowane przyszłe rozliczenie 20 prematch jest audytem pobocznym, nie dodatkową bramką zamknięcia kroku13.

## 27.10.2026 — Krok 14: techniczny CatBoost M1, komplet audytów offline PASS, nadal GATE14 PENDING

Zgodnie z pierwotnymi 29 etapami przygotowano izolowany szkielet CatBoost M1 1X2 (dwa syntetyczne warianty bez xG i z xG), potwierdzono deterministyczny zapis i ponowne wczytanie tymczasowego pliku .cbm oraz zgodność prognoz P(1/X/2). Odrębny inspektor `src/kb3_step14_bridge.py` odczytuje strukturę Step11 (121 cech, 38 flag braków, 159 dowodów dostępności) **bez przekazywania wartości ani etykiet do modelu**. Audyt `src/kb3_step14_readiness.py` sprawdza tylko trzy przypięte i podpisane źródłowe agregaty Step12/13: nie otwiera testowego holdoutu i nie pobiera żadnych danych od dostawców. Archiwalna kontrola z 26.10 zawiera 0 dopuszczonych przypadków historycznego TRAIN, co **nie jest nową certyfikacją dzisiejszego zbioru**. Żadna część nowego kodu nie może zmienić flagi `training_allowed=false` na true.

Źródło: [PR #45 scalony do main](https://github.com/karolbarankiewicz1984-ui/kb-score-3/pull/45), merge SHA `242dbb157e4d3ff21c7a088d9ab9e56c338706af`; [finalny GitHub Actions CI na commitcie PR (28/28 PASS)](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40479522446); [kontrakt i pełne ograniczenia](STEP_14_SYNTHETIC_CONTRACT.md). Zmiana wyłącznie w infrastrukturze, **bez** prawdziwego treningu CatBoost, wyboru Championa, aktualizacji M0, odczytu etykiet TEST, zakładów, dostawców płatnych i dodatkowego kroku planu. **Postęp 13/29; krok 14 W REALIZACJI; GATE14 PENDING**. Pozostaje oryginalny wymóg certyfikacji cech przed meczem i realnego odtwarzalnego fit + niezależnej ewaluacji.

## 27.10.2026 — Krok 14: rzeczywiste TRAIN i VALIDATION skontrolowane, trenowanie M1 świadomie zablokowane

Na żądanie dopuszczenia TRAIN, wytrenowania M1 i oceny bez przecieków wykonano rygorystyczną weryfikację autentycznych, niezmienionych manifestów Step12. Kontrola offline źródłowych sygnatur oraz samej chronologii i kluczy wykazała **760/760 TRAIN 2023–2025** i **380/380 VALIDATION 2025/26** z cechami nieudokumentowanymi jako istniejące przed meczem (`feature_cutoff_utc=null` w 1140/1140). Dotychczasowe dane mają `RETROSPECTIVE / QUARANTINE`, 0 rekordów faktycznie dopuszczonych, a obserwacja danych z 26.10.2026 nie dowodzi ich historycznego pierwszego terminu publikacji. Kontrola minimalnie dotknęła wyłącznie znaczników roli i metadanych chronologicznych, **bez odczytu wyników i cech TEST**. Rzeczywistego M1 **nie wytrenowano**, więc prawdziwy log loss/Brier/kalibracja M1 **nie istnieją** — nie wytwarzano fikcyjnych metryk.

[PR #47](https://github.com/karolbarankiewicz1984-ui/kb-score-3/pull/47) scalony do `main` (commit `dfe144de8e3bfe59be4fd8381fe4bd64f8eea386`). Nowe narzędzia [read-only gate](../src/kb3_step14_real_pit_gate.py), [negatywne testy](../tests/test_step14_real_pit_gate.py), [raport i konkretne wymagania do odblokowania](STEP_14_REAL_PIT_ADMISSION_2026-10-27.md). GitHub Actions #40481434168 **9/9 PASS**: https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40481434168 . Przy braku autentycznych przedmeczowych receiptów prawdziwe dopuszczenie nie jest możliwe; starych hashów nie wolno podmieniać. Oryginalny GATE14 PENDING i status **13/29** pozostają bez zmian. Żadnych nowych wydatków, zmian Elo+Poisson M0, naruszeń TEST ani promocji modelu.

## 27.10.2026 — Krok 14: rekomendacja A+B+C wykonana, badawcze M1 realnie policzone

W tej samej (nierozszerzonej) fazie 14 przeprowadzono **trzy niezależne, równoległe tory**: A pilot 40+20 historycznych snapshotów z oryginalnego SAFE MODEL VIEW, B rzeczywisty *retrospektywny eksperyment CatBoost* na zewnętrznym CC0 OpenFootball, C nowy przyszły append-only kontrolny rejestr terminów. [PR #49](https://github.com/karolbarankiewicz1984-ui/kb-score-3/pull/49), [dokument A+B+C](STEP_14_ABC_EXECUTION_2026-10-27.md).

**A (40 TRAIN + 20 VALIDATION, 60 bez wyników):** najbliższy starszy niż kickoff-48h publiczny wpis commita dostępny dla odpowiednio 0/20 (2023/24), 19/20 (2024/25) i 20/20 (2025/26); razem **39 MECZÓW z kandydatem w metadanych**, a **0/60** z niezależnym dowodem daty publikacji i dopasowania tożsamości PitchAPI. Sam Git commit timestamp nie certyfikuje PIT. Zamrożony realny TRAIN Step12 nadal ma **0/760** kwalifikujących się.

**B (osobna badawcza seria na prawdziwych wynikach):** Python CatBoost 1.2.8, pięć bezpiecznych kolumn Elo/forma 5/liczba spotkań, stałe `iterations=150, depth=4, learning_rate=0.045, seed=141027`, konserwatywna retrospektywna zwłoka 3 dni; 760 TRAIN 2023/24–2024/25 i 380 chronologicznie późniejszych VALIDATION 2025/26, bez sezonu 2026/27 TEST, bez xG, bukmacherów i PitchAPI. **Miary tylko retrospektywne:** accuracy 50.00% (referencyjna stała częstość TRAIN 42.63%), logloss 1.03921945 (ref 1.08517423), Brier sum3 0.62628833 (ref 0.65656163), top1 ECE 0.07793496 (ref 0.00789474). Model badawczy CBM SHA256 `21fe9199ca6efeef74a488e10ec8720b67ccd704a30ff502c078ff34169900ec`, raport i tymczasowy CBM jako 14-dniowy prywatny artefakt CI [#40487391948](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40487391948), **10/10 testów PASS**. **Nie jest to formalny M1 trenowany na oficjalnych certyfikowanych rekordach; porównanie NIE DOTYCZY Elo+Poisson M0.**

**C:** osobny pomocniczy, darmowy [codzienny workflow o 05:35 UTC](../.github/workflows/kb3-step14-public-schedule-sidecar.yml) zapisuje tylko przyszłe metadane terminarza do prywatnego GitHub append-only, autentyczny zegar pobrania i receipt SHA, nie wynik i nie cechy M1, bez płatnego PitchAPI. [Pierwszy trwały zapis 27.10 z 300 przyszłymi meczami i `test_labels_read=false`](../data/pit_sidecar/step14_openfootball/2026-10-27.json) utworzony przez [GitHub Actions main #40487827162 SUCCESS](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40487827162). Jest to pomocniczy kontrolny terminarz, a nie zastąpienie pierwotnego źródła PitchAPI i nie certyfikacja przedmeczowej Elo/xG.

**Wnioski:** Wykonano badanie bez nowych kosztów i bez zmiany procedury produkcyjnej. A potwierdza trudność odtworzenia archiwów przedmeczowych, B daje wstępną ocenę potencjału CatBoost, C eliminuje brak archiwum harmonogramu w przyszłości. **Oryginalne TRAIN/VALIDATION Step12, M0 i 20 zamrożonych prognoz nietknięte; TEST bez odczytu wyników; krok 14 W REALIZACJI, GATE14 PENDING i licznik 13/29.**

## 27.10.2026 — Kontrola 25 rzeczywistych historycznych blobów i prowizoryczny crosswalk OpenFootball ↔ PitchAPI

Na 60 zamrożonych fixture_id (40 TRAIN, 20 VALIDATION, 0 TEST) odczytano **25 różnych rzeczywistych poprzednich plików sezonowych** OpenFootball przypiętych do SHA oryginalnych commitów, zapisano SHA256 plików i dla każdego spotkania sprawdzono datę i godzinę z konwersją **Europe/London BST/GMT → UTC**. Dotychczasowych 39 przypadków mających wcześniejszy commit nie uznano za 39 certyfikowanych źródeł! Dokładne statusy: **17 jednoznacznych kandydatów po samym kickoff, 17 niejednoznacznych, 5 braków dokładnego kickoff, 21 bez odpowiednio wczesnego commita**. W żadnym z 17 pojedynczych kandydatów nie było wyniku FT w sprawdzonym historycznym wpisie. Przykłady `m_3AMymS → Everton FC–Newcastle United FC` na 2024-10-05 16:30 UTC oraz `m_2IJhgL → Brighton & Hove Albion FC–Manchester City FC` na 2024-11-09 17:30 UTC są **PROWIZORYCZNYM sparowaniem po samej dacie**, nie zweryfikowanym natywnym ID obu drużyn.

Zewnętrzna niezależna próba daty poprzez CDX Wayback dla dwóch sezonów nie przyniosła migawki o porównanym payloadzie; starsze daty `committer.date` to pola commita, a nie niezależny potwierdzony zegar publicznej dostępności. Prawdziwe `home_team_id` i `away_team_id` historycznego PitchAPI pozostają w oryginalnym szyfrowanym archiwum, zatem nazwy dopasowane z OpenFootball **nie uzyskały certyfikacji tożsamości**. Obecny przejrzany crosswalk w repozytorium obejmuje tylko 3 mecze z października 2026, nie cały okres 2023–2026.

Wykonanie: [GitHub Actions 8/8 testów PASS](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40492184278), [pełna metodologia, wynik i ograniczenia](STEP_14_HISTORICAL_BLOB_IDENTITY_2026-10-27.md), [60 podpisanych audytowych propozycji powiązań](../data/audits/STEP14_HISTORICAL_BLOB_60_2026-10-27.json), [niezależna próba Wayback](../data/audits/STEP14_WAYBACK_PUBCLOCK_2026-10-27.json). **0/760 oficjalnie dopuszczonych do realnego M1**, brak formalnego treningu i oceny bez przecieków. 13/29 etapów, GATE14 PENDING. Nie otwierano TEST ani nie zmieniano pierwotnego M0, splitów, 20 zamrożonych prognoz ani kosztów PitchAPI.

## 27.10.2026 — Niezależne potwierdzenie czasu publicznych commitów przez GH Archive

Po porównaniu 25 dawnych blobów (17 prowizorycznych dopasowań kickoff) wykonano odrębny, zewnętrzny test historycznych serwerowych zdarzeń **GH Archive PushEvent**. W archiwum rzeczywistych eventów GitHub znaleziono dwa SHA w `refs/heads/master` publicznego repo `openfootball/football.json`:

- 2024-10-02 **13:52:44 UTC**, GHArchive event `42475053178`, commit `5f777dc6e2cd02cdafd1520e81b7e338284fb7a7`.
- 2025-07-30 **16:20:53 UTC**, GHArchive event `52743265113`, commit `fdca227e6fc8284865254f009e987ce7a70935a0`.

Oba czasy `created_at` są z niezależnego zewnętrznego zapisu publicznego `PushEvent`, a SHA są zgodne ze sprawdzonymi rzeczywistymi historycznymi blobami. Cztery kandydatury z samym dokładnym kickoff (NIE certyfikowane jako kompletna natywna tożsamość PitchAPI): `m_3AMymS → Everton–Newcastle`, `m_4AseJ9 → Leeds–Everton`, `m_0lzfjT → Liverpool–Arsenal`, `m_0JJdwI → Sunderland–Aston Villa`. Dwie pozostałe pozycje używające tych samych SHA nie mają pełnego dopasowania terminu. Dwa inne przeszukiwane godzinowe archiwa zwróciły HTTPError; brak odczytu nie oznacza, że ich push się nie odbył. Dla pozostałych commitów czas wciąż NIEPOTWIERDZONY.

[Raport niezależnego czasu](STEP_14_GHARCHIVE_PUBLIC_CLOCK_2026-10-27.md), [pełny JSON z serwerowymi event ID](../data/audits/STEP14_GHARCHIVE_SERVER_PUSHCLOCK_2026-10-27.json), [GitHub Actions #40493703798 — 4/4 PASS](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40493703798). Oryginalny materiał PitchAPI dla 2023–2026 jest zaszyfrowany, a target-free SAFE VIEW nie zawiera natywnych obu `team_id`, zatem żadnego z tych dopasowań nie wolno jeszcze nazywać pełnym, potwierdzonym crosswalkiem. Dowód daty publikacji harmonogramu nie dowodzi także historycznego czasu wszystkich cech Elo/xG przed cutoff. **TRAIN formalnie 0/760, GATE14 PENDING, 13/29; TEST nietknięty.** Zero płatnych wywołań sportowego API.

## 27.10.2026 — Krok 14: próba weryfikacji 2 natywnych team_id dla każdego z 4 meczów

Odpowiedziano na polecenie sprawdzenia autentycznych `PitchAPI.home_team.id` i `PitchAPI.away_team.id` dla czterech `fixture_id` z potwierdzonymi zdarzeniami publicznych GH Archive PushEvents: `m_3AMymS` (Everton–Newcastle, TRAIN), `m_4AseJ9` (Leeds–Everton, VALIDATION), `m_0lzfjT` (Liverpool–Arsenal, VALIDATION), `m_0JJdwI` (Sunderland–Aston Villa, VALIDATION). W całości przejrzano jawne Step06 i Step07: **żadne z czterech ID nie występuje w ich 60-sztukowych próbach/mapach**. STEP12 SAFE zawiera tylko natywny fixture ID, kickoff i rolę. Folder Drive 19 kopii zawiera wymagany original sealed zip `KB3_PITCH_PL_2023_2026_NATIVE_20261026.zip` SHA `301bae69251d19a0192e12c2c033636b3f2822a15dcea2c4beaca28f4b45de2e`, z potwierdzonymi 1140 meczami i podpisanym chain SHA `33c750f2db89a0df5faeba9348652a451f33548959839ff7bb0ca49210c2b367`. **Nie można odczytać jego prywatnej zawartości bez istniejącego właścicielskiego klucza prywatnego RSA**, którego zgodnie z polityką nie umieszczono w GitHub, Drive ani logach. Realnych dwóch identyfikatorów na tym etapie **nie uzyskano** i nie przypisano sztucznych `t_XXXXXX`.

Przygotowano bezpieczne rozwiązanie do bezpośredniego wykonania przez właściciela klucza na swoim komputerze: [kod kontrolny bez sieci](../src/kb3_step14_native_team_crosswalk.py), [samodzielny runner z odtworzeniem źródła po PINNED ZIP i SHA](../scripts/step14_native_pitch_teamids_local.py) i [gotowa instrukcja Windows/Linux](STEP_14_NATIVE_TEAM_IDS_LOCAL_2026-10-27.md). Algorytm porównuje dokładnie cztery oryginalne `m_...`, po dwa prawdziwe `t_...` i nazwy dom/wyjazd, kickoff UTC, sezon, podpisane wyniki źródłowej weryfikacji i serwerowe GH PushEvents; sprawdza, że nie ma przecieku z TEST, nie próbuje dopasowywać wynikami, a wyjście JSON z dokładnymi ID umieszcza **wyłącznie w nowym prywatnym pliku poza repozytorium**. Nigdy nie awansuje statusu PIT TRAIN na bazie samego uwierzytelnionego *retrospektywnego* archiwum.

Testy niezależne GitHub Actions na **sztucznych** rekordach: [10/10 PASS](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40497546091). **Żaden test nie odszyfrowywał prywatnego archiwum i nie wytworzył faktycznych identyfikatorów.** Do zakończenia potrzebny prawidłowy klucz RSA pozostający na komputerze właściciela. Brak nowych wywołań płatnego PitchAPI, TEST nietknięty, M0 i 20 oryginalnych prognoz bez zmian, 13/29, GATE14 PENDING.

## 27.10.2026 — Krok 14: rzeczywiste lokalne RSA restore (3/4) i korekta po oficjalnej zmianie daty Bournemouth–Newcastle

Właściciel klucza wykonał na komputerze lokalnym prywatny weryfikator, który odtworzył oryginalne zamrożone archiwum PitchAPI, **TOTAL 4, MATCHED 3, TRAIN 1, VALIDATION 2**. Wyświetlony prywatny wynik dla `m_0JJdwI`: PitchAPI `AFC Bournemouth–Newcastle United`, 21.09.2025 13:00 UTC, podczas gdy w **lipcowym historycznym** OpenFootball SHA `fdca227e6fc8284865254f009e987ce7a70935a0` przy tym samym terminie był `Sunderland AFC–Aston Villa`. Oryginalny algorytm **słusznie odmówił dopasowania**. To nie alias ani problem szyfrowania. Właściciel nie eksportował ośmiu prywatnych wartości `t_...` do repo ani czatu.

Odnaleziono dwa niezależne oficjalne komunikaty **opublikowane redakcyjnie 03.09.2025**: [Premier League o nowym terminarzu](https://www.premierleague.com/en/news/4406114) oraz [Newcastle United o zmianie Bournemouth–Newcastle](https://www.newcastleunited.com/en/news/new-date-and-kick-off-time-for-magpies-bournemouth-trip). Mecz Bournemouth–Newcastle został przeniesiony z soboty 20.09.2025 15:00 BST na niedzielę 21.09.2025 14:00 BST (13:00 UTC), czyli na **dokładny czas drugiego meczu Sunderland–Aston Villa**. Pierwotny publiczny blob OpenFootball z **30.07.2025** poprzedzał przeniesienie. Zatem jedyny mecz według dawnej wersji pliku i godziny NIE jest jednoznacznym identyfikatorem aktualnego fixture PitchAPI.

Kod [`kb3_step14_native_team_crosswalk.py`](../src/kb3_step14_native_team_crosswalk.py) otrzymał **jeden jawny i ograniczony dowód korekty** dla `m_0JJdwI`, z zachowaniem bez zmian starej wartości `Sunderland–Aston Villa` i jej SHA jako pierwotnego niezależnego dowodu z lipca. Weryfikacja natywnej pary dla tego fixture korzysta z opublikowanego wrześniowego oficjalnego komunikatu `Bournemouth–Newcastle`. Pozostałe trzy mapy i oryginalny podpisany split zachowano. Próba na syntetycznych mockach [12/12 GitHub Actions PASS](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40538194007), w tym odmowa akceptacji nieprawdziwej starej pary jako natywnej. **Nie ponowiono lokalnie realnego odczytu po zmianie kodu**, więc nadal mamy *faktycznie wykonane* 3/4, a nie nowe potwierdzone 4/4. Daty redakcyjne artykułów NIE są kryptograficznym dowodem pierwszej publikacji wszystkich modelowanych cech PIT. Wynik dokumentuje [raport metodologiczny](STEP_14_RESCHEDULE_NATIVE_CROSSWALK_2026-10-27.md). Oryginalny oficjalny TRAIN M1 = 0/760, status 13/29, GATE14 PENDING, bez zmiany M0/TEST i bez płatnych nowych zapytań.

## 27.10.2026 — Owner-local ponowna rzeczywista weryfikacja czterech oryginalnych ID PitchAPI: 4/4

Właściciel po pobraniu aktualnej wersji projektu wykonał na własnym komputerze Windows (Python + cryptography) `py -3 -m scripts.step14_native_pitch_teamids_local` z oryginalnym wcześniej przypiętym SHA zaszyfrowanym archiwum i swoim prywatnym kluczem RSA. W widocznym wyniku terminala uzyskano: **`PITCHAPI_NATIVE_TEAM_PAIR_LOCAL_CHECK TOTAL 4 MATCHED 4 TRAIN 1 VALIDATION 3 ... GATE14 PENDING`**, następnie `PRIVATE_REPORT_SAVED_OUTSIDE_REPOSITORY_NO_SECRET_PATHS_PRINTED`. Prywatny wynik zapisano w nowym lokalnym pliku o nazwie `KB3_STEP14_NATIVE_TEAM_IDS_PRIVATE_V2.json`, bez nadpisywania zachowanego raportu 3/4. Żadnych wartości `t_...`, PEM, treści pełnego JSON i oryginalnych wyników meczów nie przekazano do projektu lub połączonych źródeł.

Dokładnie cztery weryfikowane `fixture_id`: `m_3AMymS` (Everton–Newcastle, TRAIN), `m_4AseJ9` (Leeds–Everton, VALIDATION), `m_0lzfjT` (Liverpool–Arsenal, VALIDATION), `m_0JJdwI` (Bournemouth–Newcastle po oficjalnym przesunięciu z 3.09.2025, VALIDATION). Jest to **rzeczywisty wynik lokalnej weryfikacji użytkownika na autentycznym odszyfrowanym archiwum**, nie 12/12 próby na mockach. Wcześniejszy wykryty błąd nie został ukryty: raport 3/4 zachowany jako osobna migawka audytu, oryginalny lipcowy blob OpenFootball `Sunderland–Aston Villa` nie jest edytowany.

**Zakres PASS to wyłącznie tożsamość i sparowanie 4 meczów**; nie gwarantuje to PIT wszystkich cech na historyczny kickoff, nie otwiera GATE14, nie zwiększa `train_proven_pre_match_eligible=0/760` ani nie oznacza formalnego fit CatBoost M1. Nie odczytano TEST, nie zmieniano M0, pierwotnych 20 zamrożonych prognoz ani oryginalnych splitów. Postęp planu nadal 13/29, **GATE14 PENDING**.

## 27.10.2026 — Krok 14: rzeczywisty audyt danych PIT dla pełnych 1140 TRAIN/VALIDATION, rozszerzony weryfikator tożsamości i referencja 1140 meczów

**Wykonane BEZ prywatnego RSA w CI:** na rzeczywistym podpisanym i niezmienionym Step12 analizowano dokładnie 760 historycznych TRAIN + 380 VALIDATION, 0 TEST. Każdy z 1140 ma brak źródłowego `feature_cutoff_utc` i pełnych as-of receipts. Zweryfikowany wynik: **0/760 TRAIN i 0/380 VALIDATION** dopuszczone do rzeczywistego modelu M1. Przegląd oryginalnego kontraktu Step11: 121 liczbowych/nullable cech (17 Elo/rywala, 36 forma/gole, 48 xG/xGA, 20 liczności/historii) plus 38 znaczników braku (0 Elo, 12 forma/historia, 24 xG/xGA, 2 kompletność), **łącznie 159 dowodów dostępności danych na rekord**. Nie należy przeliczać dat wstecz na podstawie dostawcy: realnie PitchAPI zapisano dopiero 26.10.2026.

**Rzeczywista niezależna referencja tożsamości:** bez płatnego API pobrano z otwartego OpenFootball Premier League trzy ukończone sezony po 380 spotkań; zapisano tylko datę, brytyjski czas lokalny, nazwy obu drużyn, oryginalne SHA256 źródeł. Zamrożona **1140-wierszowa referencja bez score/odds/xG** ma SHA `fa924730da71e3ba24e89a3095f7d4d92de5e71dd252b893bd86cc2e4db53678`, [plik](../data/research/STEP14_OPENFOOTBALL_1140_TARGETFREE_2026-10-27.json). Jest ona **retrospektywna z 27 października**, a więc nie zastępuje historycznego źródła `as-of`. Dla 60 dawnych pilotażowych fixtures nadal osobne oryginalne historyczne bloby i GH Archive (2 server-PushEvent) z poprzednich audytów.

**Nowy bezpieczny odczyt właściciela:** rozszerzono weryfikator historycznego oryginalnego, zaszyfrowanego PitchAPI ZIP z 4 do **pełnych 1140 meczów bez TEST**. Kontroluje `fixture_id, kickoff, TRAIN/VALIDATION, home_team.id/away_team.id`, niezmienność team IDs/nazw, 20 klubów × 380 meczów w każdym sezonie; porównuje dodatkowo z każdym wierszem niezależnego publicznego 1140 terminarza po obu nazwach i UTC (uwzględnienie UK BST/GMT), a nie tylko kickoff. Rozróżnia dokładne pary, inne godziny (przeniesienia), nierozpoznane aliasy/zespoły oraz dodatkową niezależną próbę 60 dawnych migawkowych zapisów z GH Archive. **Wynik będzie wyłącznie prywatnym zestawieniem sumarycznym, bez `t_...`, score, odds, RSA, TEST.** Kod [audyt](../src/kb3_step14_full_identity_pit_audit.py), [runner na komputerze użytkownika](../scripts/step14_full_native_identity_pit_local.py), [instrukcja](STEP_14_FULL_1140_IDENTITY_PREMATCH_PIT_2026-10-27.md).

[GitHub Actions #40543896275](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40543896275) **SUCCESS, 12/12 + 6/6 testów** na sztucznych parach i publicznych próbnych źródłach plus **realny** wynik PIT na podpisanym indeksie i **rzeczywiste** publiczne 1140 reference. Własnego klucza RSA nie przechowywano i **nie wykonano w CI odszyfrowania realnych 1140 team IDs**. Wcześniejsza autentyczna lokalna kontrola właściciela 4/4 jest osobno udokumentowana. Nowy pełny przebieg 1140 ma status `READY_FOR_OWNER_LOCAL_EXECUTION`, nie wolno raportować `1140 MATCHED` zanim rzeczywiście zostanie uruchomiony.

**Sfera wyników modelu:** nadal brak autentycznych pre-match PIT dla historycznych cech Elo/formy/xG w Step12. Jedynie chronologicznie odtwarzalne wyniki nadają się do osobnego, jawnie retrospektywnego badania, którego nie wolno oznaczać jako produkcyjny CatBoost M1. GATE14 PENDING, 13/29, zamrożony TEST, M0 i 20 prognoz bez zmian, zero nowych płatnych zapytań.

## 27.10.2026 — Krok14: pierwszy rzeczywisty częściowy PIT publicznych wyników (bez awansu całego modelu)

Dla dwóch autentycznych poprzednio potwierdzonych historycznych `GH Archive PushEvent` pobrano dokładne archiwalne JSON OpenFootball o w pełni sprawdzonych SHA256 i **sprawdzono ich ówczesną treść**. Publiczna wersja z **2024-10-02 13:52:44Z** zawierała już wyniki 60 ukończonych spotkań Premier League 2024/25, po 6 wcześniejszych wyników Evertonu i Newcastle przed planowanym spotkaniem Everton–Newcastle 05.10.2024. Jest to rzeczywisty dowód publicznej wcześniejszej dostępności **części danych wejściowych do 5-meczowej formy/goli**, nie tylko daty lub harmonogramu. Wersja 2025/26 publicznie wypchnięta **30.07.2025** zawierała **0** wcześniejszych wyników nowego sezonu (wczesny terminarz, nie historia rozegranych spotkań), zatem nie potwierdza podobnej formy w tej samej migawce dla Leeds–Everton ani Liverpool–Arsenal. Lipcowy konflikt `m_0JJdwI` Sunderland–Aston Villa vs Bournemouth–Newcastle po zmianie wrześniowej pozostał jednoznacznie **wykluczony** z pozytywnego przypisania tego starego bloba do natywnego fixture.

Niezależny algorytm odmawia odczytu wyniku docelowego w historycznej migawce i nie przyjmuje wyników z datą nie wcześniejszą niż `PushEvent`. [GitHub Actions #40546191857 — 7/7 testów PASS, REALNE dwa pinned historyczne źródła](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40546191857). [Raport niezależny](STEP_14_VERIFIED_PUBLIC_PREMATCH_RESULTS_2026-10-27.md), [aggregaty tylko liczników i SHA](../data/audits/STEP14_EARLY_PUBLIC_PREMATCH_FT_2026-10-27.json). **Publiczne historyczne FT ≠ podpisane oryginalne snapshoty 121 cech PitchAPI**, nie poświadcza Elo, xG, 159 pełnych dowodów ani dostępności danych od głównego dostawcy. **Formalny TRAIN PIT nadal 0/760 i VALIDATION 0/380, GATE14 PENDING, 13/29, TEST i M0 nietknięte, bez płatnego sportowego API.**

## 27.10.2026 — Krok 14, prace bez dostępu do Windows: ryzyko 647 wspólnych terminów + kontrola integralności źródła i trwały GATE PIT

Na polecenie właściciela kontynuowano budowę modelu w **samym GitHub**, bez lokalnego klucza RSA, płatnego sportowego API i bez jakiejkolwiek zmiany TEST/M0/zamrożonych 20 prognoz. Na **oryginalnych dwóch podpisanych i zamrożonych źródłach**: Step12 SAFE `3b8da84b...` i publicznej bezwynikowej referencji 1140 OpenFootball `fa924730...` wykryto rzeczywiste ryzyko dopasowania wydarzeń po samej godzinie w obrębie sezonu: **647/1140 ma więcej niż jednego kandydata** o tej samej godzinie, **492/1140 ma tylko jednego** (ale nie jest to dowód zgodności zespołów), **1/1140 ma zero** publicznych kandydatów o tej godzinie. Wszystkie liczby są stanami **źródła terminarzy, NIE udowodnionymi błędami natywnych ID**. [Dane raportu](../data/audits/STEP14_REAL_1140_KICKOFF_AMBIGUITY_2026-10-27.json), [kod audytu](../src/kb3_step14_calendar_collision_audit.py). Rzeczywisty GitHub Actions [#40576598573 SUCCESS](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40576598573) potwierdził 1140, 760/380 i 0 TEST, z sumą statusów 647+492+1.

W wykrytej rzeczywistej **słabości wiązania audytowej referencji z źródłem** dawny algorytm uznawał ponownie samopodpisaną zmodyfikowaną publiczną referencję (SHA mógł zostać przeliczony po zmianie nazw). Wprowadzono **sztywne porównanie do zamrożonego oryginalnego SHA projekcji i trzech dokładnych SHA surowych publicznych sezonów** oraz dodatkowe odmowy, gdy referencja przechodzi na xG/wyniki/test lub zezwala na trening. Nowa struktura testów obejmuje powtórnie przeliczone oszukańcze SHA i prawdziwą niezmienioną referencję. Oryginalnego pliku nie nadpisywano.

Przygotowano [osobny bezkluczowy odbiór przyszłego raportu 1140 natywnych meczów](../src/kb3_step14_full_owner_report_review.py): sprawdza jedynie sumy i oryginalne SHA, 1140/760/380, 20 klubów na sezon, 60 historycznych blobów, rozbieżności, specjalny błędny lipcowy Sunderland–Aston Villa / właściwy przeniesiony Bournemouth–Newcastle i **przymusowy brak awansu GATE14**. Testy 9/9 PASS, żadnej autentycznej prywatnej sesji RSA nie wykonywano. Dla pierwotnego realnego [workflow PIT](../.github/workflows/kb3-step14-real-pit-audit.yml) dodano ciągłe działanie na `main`, po zmianach kodu i podpisanych danych Step12 oraz ręczny audyt; [9/9 testów rzeczywistego PIT odmowy PASS](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40575868016). Dwa zbiory wyników: 12 testów full ID, 8 testów public reference, 5 real calendar oraz 9 testów właścicielskiego raportu, wszystkie PASS w [40576598573](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40576598573). Dokumentacja [szczegółowa](STEP_14_PREWINDOWS_AUDIT_2026-10-27.md).

**Ważne:** realne potwierdzenie oryginalnych 1140 natywnych `team_id` nadal wymaga jednego lokalnego wykonania, którego w tej sesji bez RSA **nie wykonano**. Pełny historyczny source PIT nadal 0/760 TRAIN, 0/380 VALIDATION, `GATE14 PENDING`, 13/29 formalnych etapów. Zmiany dotyczyły wyłącznie kontroli jakości procesu, bez treningu/wdrożenia M1.

## 27.10.2026 — Krok 14: matematyka CatBoost 1/X/2, dwa warianty xG i techniczny mechanizm późniejszej kalibracji

Na polecenie właściciela, bez komputera Windows i dostępu do prywatnego RSA, zaimplementowano [czysto matematyczny moduł 1/X/2](../src/kb3_step14_m1_math_calibration.py) i rzeczywisty [CatBoost CPU 1.2.8 porównujący dwa warianty WYŁĄCZNIE NA WYTOWRZONYCH W KODZIE FIKCYJNYCH 90 TRAIN / 30 VALIDATION](../src/kb3_step14_m1_xg_comparison.py). Zbadano restrykcyjne mapowanie classes_ do (1,X,2), sumowanie prawdopodobieństw, log loss, multiclass Brier sum3 bez dzielenia przez 3, top1 ECE/10 binów, maski xG i nullable xG (NaN w obliczeniach, a nie 0), deterministyczne parametry CatBoost, stały seed. Dla identycznych 30 fikcyjnych przykładów BEZ_XG (3 cechy) uzyskał **log loss 0,986583 / Brier sum3 0,596817 / accuracy 50%**, Z_XG+missing (7 cech) **0,825654 / 0,474751 / 60%**. NIGDY nie przedstawiać fikcyjnych wyników jako realnej przewagi xG. Istniejące niezależne wcześniejsze badanie RETROSPEKTYWNE na rzeczywistych FT OpenFootball 760/380, lecz bez PIT (PR #49), dotyczyło wyłącznie innej wersji bez xG i nie jest porównywalne z tą syntetyczną demonstracją.

Dla obu demonstracji podzielono 30 fikcyjnych prognoz chronologicznie na wcześniejsze 15 do dobrania skalara temperatury metodą logloss oraz późniejsze niezależne 15 do oceny Brier/logloss/ECE. Demo proponuje T=0,7 obu wariantów; na późniejszych 15 logloss BEZ_XG przed/po 1,023813/1,010868, Z_XG 0,833461/0,783386, BEZ produkcyjnej kalibracji. Kontrola sparowanych 15 logloss difference Z_XG minus BEZ_XG = -0,190351 dotyczy tylko tych 15 wymyślonych przykładów, niczego nie dowodzi na prawdziwych meczach.

Dodatkowo przygotowano **przyszły** interfejs freeze→settlement→kalibracja→niezależna ocena: `freeze_forecast` zapisuje probabilistyczną prognozę z SHA i lokalnym czasem, `audit_frozen_settlements` wymaga settlementów późniejszych niż kickoff i wcześniejszych niż cutoff, unika podwójnego rozliczenia i odmówi zmianie hash; `prepare_future_calibration_candidate` izoluje wersję modelu i wariant, wymaga min **100 zakończonych wcześniejszych, serwerowo uwierzytelnionych prognoz** oraz osobnych min **50 późniejszych** do oceny, embarguje przypadki przekraczające cutoff i ZAWSZE zabrania automatycznego wdrożenia. **Kod sam nie tworzy niezależnego serwerowego append-only ledgeru: lokalny SHA i podany czas nie dowodzą rzeczywistej przedmeczowej publikacji, więc przyszła integracja wymaga niezależnego dowodu freeze.** Dotychczasowe rzeczywiste 20 zamrożonych prognoz M0 nietknięte.

[GitHub Actions #40579198296](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40579198296) PASS: **16 testów** modułu matematyki, podpisów i przyszłej kalibracji (w tym 100+50 i no-future-outcomes) oraz **5 testów** rzeczywistego CPU CatBoost na fikcyjnych prognozach. [Pełny maszynowy raport](../data/audits/STEP14_SYNTHETIC_M1_NOXG_XG_CALIBRATION_2026-10-27.json), [szczegółowy raport metodologiczny](STEP_14_CATBOOST_M1_MATH_XG_CALIBRATION_2026-10-27.md). Nie czytano testu 2026/27 ani natywnych prywatnych ID, nie wykonywano nowych wywołań płatnego PitchAPI, nie wytrenowano prawdziwego modelu M1 i nie aktualizowano M0. **Krok 14 W REALIZACJI, GATE14 PENDING, 13/29, oficjalny realny TRAIN PIT 0/760.**
