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
