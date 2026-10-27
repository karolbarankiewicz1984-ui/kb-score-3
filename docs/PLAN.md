# KB Score 3.0 — PLAN GŁÓWNY (kopia operacyjna GitHub)

**Wersja źródłowa:** v1.1, Google Docs (aktualizowane po odbiorach). **Stan po odbiorze 27.10.2026:** **13/29 kroków zaliczonych** (01–13). Krok 13 ELO+Poisson ZALICZONO **w jego oryginalnym zakresie technicznym** po niezależnym audycie dowodów; realne badanie retrospektywne nie jest certyfikowanym PIT. Krok 14 W REALIZACJI: syntetyczny CatBoost M1 oraz odczytowy audyt pochodzenia i bramki danych wdrożone na main (PR #45), niezależne CI 28/28 PASS; bez rzeczywistego treningu. **Trening na historycznych danych z niepotwierdzonym PIT i wdrożenie produkcyjne nadal ZABLOKOWANE**. Wcześniejsze raporty badawcze zachowują oryginalne flagi i ograniczenia. Statusy w tej kopii aktualizujemy po odbiorach, ale **źródłem prawdy pozostaje [oryginał na Dysku Google](https://docs.google.com/document/d/10wjHL3r3OAuxtezwcIeWztxS8lwjhYon5GM3BLhI0xE/edit)**.

**Pozostałe dokumenty:** [DANE.md](DANE.md), [MODEL.md](MODEL.md), [ZMIANY.md](ZMIANY.md), [instrukcja bezpieczeństwa kroku 03](STEP_03_SECURITY_CHECKLIST.md). **Repozytorium:** https://github.com/karolbarankiewicz1984-ui/kb-score-3.

## Zasady projektu

- Całkowicie niezależny KB Score 3.0; KB2.1, API Market i MultiModel tylko jako historyczne benchmarki, nie silnik treningowy ani podstawowy model.
- Nie piszemy ani nie uruchamiamy silnika prognoz w kroku 04 — to **dokumentacja**. Kod modelu powstaje dopiero w jego zaplanowanych etapach.
- Bez nowych zakupów bez wyraźnej zgody właściciela. Dodatkowy budżet API: do 100 zł/mies. jako pułap rozmowy, nie upoważnienie do zakupu.
- Klucze wyłącznie w GitHub Secrets; prognozy tworzone przed startem, nienadpisywalne; brak lookahead; oddzielne dane TRAIN/VALIDATION/TEST.
- Cel: wiarygodne prawdopodobieństwa 1X2, gole, BTTS, następnie kartki/rożne/faule po audycie; baseline ELO+Poisson, niezależny CatBoost; walk-forward, Brier, log loss, kalibracja, Champion–Challenger.
- Docelowa dostawa trzech PDF dzisiaj/jutro/pojutrze o 09:30 Europe/Warsaw **dopiero po odbiorze kroku 24**. Bez automatycznego obstawiania.

## Reguła bramki odbioru GATE

1. Każdy krok musi mieć **mierzalny rezultat i test PASS** (automatyczny lub kontrola ręczna), nie tylko kod lub deklarację.
2. Niezbędny jest **dowód**: link do commitu/testu, raport audytu, freeze ID lub plik rezultatów.
3. Zapisujemy datę, odpowiedzialność, wynik, URL, ryzyka i następny krok w [dzienniku Google Docs](https://docs.google.com/document/d/10wjHL3r3OAuxtezwcIeWztxS8lwjhYon5GM3BLhI0xE/edit) oraz [ZMIANY.md](ZMIANY.md).
4. Statusy: **NIE ROZPOCZĘTO → W REALIZACJI → DO ODBIORU → ZALICZONO**; awarie: **BLOKADA / DO POPRAWY**.
5. Zakupy, promocja nowego Championa, uruchomienie raportów produkcyjnych i potrzebne konta wymagają osobnej zgody użytkownika. Niezaliczone zależności blokują przejście do produkcji.
6. **Zapis `ZALICZONO` można wprowadzić dopiero po niezależnej kontroli dowodów.** Zmiana kryteriów wymaga wersji i wpisu z uzasadnieniem.

## Pełna mapa 29 etapów z kryteriami odbioru

### Etap A. Środowisko, dostęp i dokumentacja

#### Krok 01 — Kontrola posiadanych kont i uprawnień  [ZALICZONO]

- **CO ZROBIĘ:** Sprawdzić dostęp do GitHub, API-Football, PitchAPI, Dysku Google oraz usług wysyłkowych; nie odczytywać ani ujawniać sekretów.
- **CO ROBISZ TY:** Potwierdzić konta tylko gdy wymagają Twojego logowania; nie wysyłać haseł.
- **NARZĘDZIA I KOSZT:** GitHub, panele dostawców, Google Drive; 0 zł nowych zakupów.
- **BRAMKA ODBIORU / TEST PASS:** Odnotowano dla każdej usługi: dostęp TAK/NIE, plan, dostępny zakres, znane limity i brakujące uprawnienia. Wszystkie pozycje mają źródło lub wyraźny znak „niezweryfikowane”.
- **DOWÓD ZALICZENIA:** Karta dostępu z datą audytu i linkami do paneli, bez sekretów.
- **ZALEŻY OD:** Brak.
- **STATUS:** ZALICZONO | TEST: PASS — konto, usługi, koszty, limity, miejsce, ryzyka | DOWÓD: raport audytu 24.10.2026 na końcu dokumentu | DATA ODBIORU: 24.10.2026

#### Krok 02 — Nowe prywatne repozytorium kb-score-3  [ZALICZONO]

- **CO ZROBIĘ:** Utworzyć niezależne repozytorium, gałąź główną i katalogi projektu; nie kopiować silnika KB2.1 jako KB3.0.
- **CO ROBISZ TY:** Potwierdzić utworzenie repo i uprawnienia, jeżeli GitHub wymaga działania właściciela.
- **NARZĘDZIA I KOSZT:** GitHub; bez dodatkowych zakupów.
- **BRAMKA ODBIORU / TEST PASS:** Nowy adres repo działa; ustawienie private potwierdzone przez metadane; istnieje README; pliki starszego projektu nie zostały zmodyfikowane.
- **DOWÓD ZALICZENIA:** URL nowego repo, identyfikator pierwszego commitu i wynik kontroli widoczności.
- **ZALEŻY OD:** Krok 1.
- **STATUS:** ZALICZONO | TEST: PASS (repo private, README, pierwszy commit, 8 katalogów, niezmieniony stary projekt) | DOWÓD: https://github.com/karolbarankiewicz1984-ui/kb-score-3/commit/7c6cee2be18b3a771d0d94ccd3f6841f7f6d83a6 | DATA ODBIORU: 25.10.2026

#### Krok 03 — Sekrety, limity i budżet  [ZALICZONO]

- **CO ZROBIĘ:** Dodać klucze usług jako GitHub Secrets, sprawdzić ustawienia wydatków i minimalne uprawnienia workflow.
- **CO ROBISZ TY:** Gdy niezbędne, wkleić klucze wyłącznie do formularza GitHub Secrets; zatwierdzić ewentualne opłaty.
- **NARZĘDZIA I KOSZT:** GitHub Secrets/Billing; bez zakupów.
- **BRAMKA ODBIORU / TEST PASS:** Testowe wywołania API działają bez wypisywania klucza; skan repo i logów nie znajduje sekretów; udokumentowano limity i kontrolę kosztów.
- **DOWÓD ZALICZENIA:** Wynik zanonimizowanego testu API, stan zabezpieczeń i link do testu w Actions.
- **ZALEŻY OD:** Kroki 1–2.
- **STATUS:** ZALICZONO | TEST: PASS — API-Football i PitchAPI HTTP 200; brak wskazań sekretów w kontrolowanym skanie; budżet Actions 0 USD i alerty włączone | DOWÓD: https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40203074557 | DATA ODBIORU: 25.10.2026

#### Krok 04 — Dokumentacja projektu i repozytorium decyzji  [ZALICZONO]

- **CO ZROBIĘ:** Przenieść ten plan do docs w NOWYM repo po jego utworzeniu; przygotować PLAN.md, DANE.md, MODEL.md i ZMIANY.md; linkować do tego dokumentu na Dysku.
- **CO ROBISZ TY:** Zatwierdzić ogólne założenia przed pisaniem silnika.
- **NARZĘDZIA I KOSZT:** Google Docs oraz GitHub; 0 zł.
- **BRAMKA ODBIORU / TEST PASS:** Wszystkie cztery dokumenty są dostępne; każde określenie etapu ma warunki odbioru; plan GitHub i dokument główny odsyłają do siebie; żaden krok nie ma fałszywego DONE.
- **DOWÓD ZALICZENIA:** Linki do dokumentów, commit i wynik kontroli kompletności 29 kroków.
- **ZALEŻY OD:** Krok 2.
- **STATUS:** ZALICZONO | TEST: PASS (4 dokumenty; 29/29 bramek, dowodów i zależności; 0 zerwanych linków i przedwczesnych DONE) | DOWÓD: [STEP_04_ACCEPTANCE.md](STEP_04_ACCEPTANCE.md) | DATA ODBIORU: 25.10.2026

### Etap B. Źródła i historia

#### Krok 05 — Audyt API-Football  [ZALICZONO]

- **CO ZROBIĘ:** Sprawdzić sezony, top 5 lig, terminarze, wyniki, statystyki, kursy, opóźnienia i limity.
- **CO ROBISZ TY:** Potwierdzić aktywny plan API tylko jeśli nie da się odczytać go bezpiecznie.
- **NARZĘDZIA I KOSZT:** API-Football; obecny abonament, bez nowego zakupu.
- **BRAMKA ODBIORU / TEST PASS:** Powstała tabela liga×sezon×typ danych z liczebnościami; próbka pobrań powtarzalna; żaden brak nie jest ukrywany jako zero.
- **DOWÓD ZALICZENIA:** Raport pokrycia z datą, liczbami, odpowiedziami testowymi i kosztami zapytań.
- **ZALEŻY OD:** Krok 3.
- **STATUS:** ZALICZONO | TEST: PASS — 30/30 sezonów, próbki 60/60, 25/25 krzyżowych zgodności; 0 błędów API | DOWÓD: [STEP_05_ACCEPTANCE.md](STEP_05_ACCEPTANCE.md) i [raport liga×sezon](audits/API_FOOTBALL_STEP05_2026-10-25.md) | DATA ODBIORU: 25.10.2026

#### Krok 06 — Audyt PitchAPI  [ZALICZONO]

- **CO ZROBIĘ:** Sprawdzić legalnie dostępne ligi, sezony, rzeczywiste xG, statystyki strzałów i zgodność czasową.
- **CO ROBISZ TY:** W razie potrzeby potwierdzić konto/klucz w bezpieczny sposób.
- **NARZĘDZIA I KOSZT:** PitchAPI; bez nowego zakupu przed analizą.
- **BRAMKA ODBIORU / TEST PASS:** Porównano minimum reprezentatywną próbkę meczów z API-Football; opisano zakres i brak xG oraz ograniczenia historyczne.
- **DOWÓD ZALICZENIA:** Raport pokrycia xG z identyfikatorami przykładowych meczów i rezultatami zapytań.
- **ZALEŻY OD:** Krok 3.
- **STATUS:** ZALICZONO | TEST: PASS — 30/30 liga×sezon, 60/60 kompletnych próbek xG, 20 ścisłych par API-Football, 8/8 testów offline; LaLiga zidentyfikowana po korekcie nazwy | DOWÓD: [STEP_06_ACCEPTANCE.md](STEP_06_ACCEPTANCE.md), [pełny raport](audits/PITCHAPI_STEP06_2026-10-25.md), [test SUCCESS](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40235545588) | DATA ODBIORU: 25.10.2026

#### Krok 07 — Dopasowanie identyfikatorów meczów  [ZALICZONO]

- **CO ZROBIĘ:** Połączyć drużyny i mecze obu dostawców, obsłużyć zmiany nazw, przełożenia, strefy czasowe i duble.
- **CO ROBISZ TY:** Brak działań technicznych.
- **NARZĘDZIA I KOSZT:** Python, dane API, testy jednostkowe; 0 zł.
- **BRAMKA ODBIORU / TEST PASS:** Na ręcznie skontrolowanej próbie dopasowania są prawidłowe; przypadki niejednoznaczne trafiają do kolejki, a nie są zgadywane; brak duplikatów klucza wydarzenia.
- **DOWÓD ZALICZENIA:** Raport zgodności, liczba dopasowanych/niepewnych i wynik testów.
- **ZALEŻY OD:** Kroki 5–6.
- **STATUS:** ZALICZONO | TEST: PASS (38 STRICT, 22 REVIEW, 17/17 testów, 0 duplikatów, 0 faktycznych konfliktów ID; Lyon–Auxerre 60 min w kolejce) | DOWÓD: [STEP_07_ACCEPTANCE.md](STEP_07_ACCEPTANCE.md), [crosswalk JSON](../data/audits/STEP07_MATCH_CROSSWALK_2026-10-25.json), [Actions PASS](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40236615477) | DATA ODBIORU: 25.10.2026

#### Krok 08 — Projekt bazy danych i archiwizacji  [ZALICZONO]

- **CO ZROBIĘ:** Zdefiniować mecze, drużyny, sezony, źródła, statystyki, kursy, prognozy, N, treningi, wersje i rozliczenia.
- **CO ROBISZ TY:** Zatwierdzić lokalizację trwałego magazynu, jeżeli jest potrzebna płatna przestrzeń.
- **NARZĘDZIA I KOSZT:** SQLite, Parquet, trwały backup; na start 0 zł.
- **BRAMKA ODBIORU / TEST PASS:** Test zapis→odczyt→odtworzenie backupu przechodzi; baza wymusza unikalność meczów i niezmienność prognoz; wskazano sposób odzyskiwania po awarii.
- **DOWÓD ZALICZENIA:** Schemat bazy, migracje, test przywrócenia backupu i jego identyfikator.
- **ZALEŻY OD:** Krok 7.
- **STATUS:** ZALICZONO | TEST: PASS — 9/9 testów SQLite, UNIQUE, immutability i backup→restore + niezależny restore z Google Drive | DOWÓD: [protokół GATE08](STEP_08_ACCEPTANCE.md), [Actions 40241611841](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40241611841), [manifest Drive](../data/audits/STEP08_BACKUP_MANIFEST_2026-10-25.json) | DATA ODBIORU: 25.10.2026

#### Krok 09 — Pobranie pierwszej historii, potem rozszerzenie  [ZALICZONO]

- **CO ZROBIĘ:** Pobrać kontrolnie 1 ligę/1 sezon, zweryfikować import i rozszerzać na sezony/ligi mające dane.
- **CO ROBISZ TY:** Nie trzeba nic robić, chyba że plan API limituje import.
- **NARZĘDZIA I KOSZT:** API-Football, PitchAPI, GitHub Actions; bez nowych zakupów.
- **BRAMKA ODBIORU / TEST PASS:** Liczba importowanych meczów uzgodniona z kontrolnym terminarzem; powtórny import nie powiela danych; skrypt potrafi bezpiecznie wznowić przerwany import.
- **DOWÓD ZALICZENIA:** Plik manifestu z ligami, sezonami, liczebnościami, checksumami i logiem kontrolnym.
- **ZALEŻY OD:** Kroki 5–8.
- **STATUS:** ZALICZONO | TEST: PASS TECHNICZNY — Premier League 2024/25 380/380, 0 duplikatów, wznowienie po 17, 19/19 testów, zaszyfrowany backup odtworzony po ponownym pobraniu z Google Drive | DOWÓD: [GATE09](STEP_09_ACCEPTANCE.md) | DATA ODBIORU: 26.10.2026

#### Krok 10 — Weryfikacja jakości i chronologii danych  [ZALICZONO]

- **CO ZROBIĘ:** Zidentyfikować braki, powielone wydarzenia, niemożliwe daty, błędy źródeł i przyszłą wiedzę.
- **CO ROBISZ TY:** Przejrzeć podsumowanie jakości, jeśli potrzebna decyzja o wyłączeniu ligi.
- **NARZĘDZIA I KOSZT:** Python, testy jakości danych; 0 zł.
- **BRAMKA ODBIORU / TEST PASS:** Testy poprawności i no-lookahead przechodzą na przykładach pozytywnych i celowo błędnych; każda liga ma raport jakości; błędy krytyczne blokują trening.
- **DOWÓD ZALICZENIA:** Raport QA, wykaz odrzuconych rekordów i wynik testu negatywnego.
- **ZALEŻY OD:** Krok 9.
- **STATUS:** ZALICZONO | TEST: PASS — 30/30 kombinacji liga×sezon, 10 679 wpisów meczowych, 0 krytycznych błędów źródła, 10/10 wyjątkowych sezonów rozróżnionych na rundę zasadniczą i baraże; 19 meczów pucharowych/barażowych oddzielonych, 1 wynik AWD w kwarantannie; 54/54 testów PASS + 4/4 mutacje negatywne blokują, no-lookahead. Trening pozostaje ZABLOKOWANY do etapu cech i potwierdzenia point-in-time | DOWÓD: [protokół GATE10](STEP_10_ACCEPTANCE.md), [manifest](../data/audits/STEP10_FINAL_2026-10-26.json), [pełny przebieg](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40280931156) | DATA ODBIORU: 26.10.2026

### Etap C. Cechy i chronologia

#### Krok 11 — Cechy przedmeczowe  [ZALICZONE]

- **CO ZROBIĘ:** Wyliczać ELO, formę 5/10/15, siłę przeciwników, dom/wyjazd, gole, xG gdy dostępne i kontekst potwierdzony przed meczem.
- **CO ROBISZ TY:** Nie musisz liczyć wskaźników.
- **NARZĘDZIA I KOSZT:** Python, SQL/Parquet, testy; 0 zł.
- **BRAMKA ODBIORU / TEST PASS:** Każda cecha ma opis i znacznik daty dostępności; test odcina przyszły mecz i pokazuje brak przecieku; brak xG nie jest zamieniany na fikcyjną wartość.
- **DOWÓD ZALICZENIA:** Katalog cech z źródłem, datą i wynikiem testów no-lookahead.
- **ZALEŻY OD:** Krok 10.
- **STATUS:** ZALICZONE | GATE11: PASS (ORYGINALNY KONTRAKT) | ARCHIWUM: 760/760 wyników zaszyfrowanych na Drive z przywróceniem PASS; dwa rzeczywiste snapshoty PL 2026/27 po 380 meczów (09:01:49 UTC i 09:20:47 UTC 26.10.2026) osobno zaszyfrowane na Drive i odtworzone PASS; 0/380 zmian, 3/3 xG kompletne, źródłowo nadal w kwarantannie; po kontroli pełnych danych 3/3 **ściśle przypisane do konkretnych fixture** w osobnej warstwie pochodnej, bez ogólnych aliasów; 10 kolejnych xG (10/10 kompletnych, 5 ścisłych + 5 w kwarantannie) z osobnego zaszyfrowanego archiwum odtworzonego z Drive; niezależny odczyt do observed-at cech PASS; historyczny PIT dla 2023–2025 nadal 0; WIELOSEZONOWE ELO PitchAPI 2023/24–2026/27 REAL PASS: 1140 historycznych +80 obecnych wyników, 17 stabilnych team IDs między sezonami, źródła zobserwowane 26.10.2026, wciąż NIE historic prematch PIT; xG TRZY LIGI 2026/27: nowe 10/10 PL, 10/10 LE i 10/10 LK COMPLETE; dwa osobne archiwa UEFA dają 14 odmiennych meczów każdej Ligi UEFA, łącznie 38 odmiennych kompletnych spotkań, niepełne pokrycie całego sezonu; PREFEROWANY SINGLE-PROVIDER PitchAPI (dwa autentyczne niezależne native-PIT odczyty 11:29 i 12:19 UTC z Drive: 380/380 zgodnych meczów, 5/5 niezmienionych feedów xG, 385/385 hashy w obu backupach, bez produkcyjnej migracji), realny test PL 380+380+380, 5 xG, UEFA EL/LK i fauli/kartek PASS | TEST: 246/246 PASS (207 testów w bloku Step11, 19 pokrewnych testów bezpieczeństwa i 20 starszych) | ODBIÓR ORYGINALNYCH 3 KRYTERIÓW: PASS; pilot 380/380 i tymczasowy 760/760; xG PitchAPI 12/12 kompletnych, 8/12 dokładnych mapowań, 0/12 historycznej certyfikacji czasu; training_allowed=false | DOWÓD: [FORMALNY ODBIÓR GATE11 — pierwotne trzy kryteria spełnione, 246/246 testów i zakres wyłączeń](STEP_11_GATE_ACCEPTANCE_2026-10-26.md), [CI #40339012432](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40339012432), [trzy ligi PitchAPI 30/30 kompletnych strzałowych xG, 38 różnych meczów z porównaniem poprzedniej próby; 34 SEALED source restore PASS](STEP_11_THREE_LEAGUES_XG30_COVERAGE.md), [241/241 CI](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40334026441), [rzeczywiste ELO 2023/24–2026/27: 1140+80 meczów, offsite restore, stable team IDs, 231/231 CI](STEP_11_PITCH_MULTISEASON_ELO.md), [CI #40330403055](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40330403055), [legacy API-Football piloci 380/760 tylko po ręcznym dispatch, 220 testów i oba network jobs SKIPPED #40326752798](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40326752798), [audyt znacznika czasu wszystkich cech v0.5, 11 negatywnych testów no-lookahead](STEP_11_FIELD_PROVENANCE_GATE.md), [217/217 CI #40325431132](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40325431132), [weryfikator trybu SQLite read-only + zabezpieczony lokalny restore dwóch ZIP, 206 testów #40322588669](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40322588669), [DWA prawdziwe natywne snapshoty PitchAPI: 0/380 zmian, 0/5 zmian xG, osobne odtworzenia Drive PASS](STEP_11_NATIVE_SECOND_REAL_CAPTURE.md), [rzeczywisty run #40321588543](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40321588543), [UEFA PitchAPI 12/12, offsite RSA+AES restore 15/15 PASS](STEP_11_UEFA_NATIVE_XG_COVERAGE.md), [199/199 CI #40320084066](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40320084066), [PitchAPI encrypted observed-at PIT 380+5, Drive restore PASS](STEP_11_PITCH_NATIVE_PIT_ARCHIVE.md), [175/175 CI #40316210520](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40316210520), [PitchAPI jako jeden kandydat: 1140 fixture, 5 xG, EL/UECL + faule](STEP_11_SINGLE_PROVIDER_DECISION.md), [160/160 CI #40313071652](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40313071652), [10 nowych xG (5 strict, 5 kwarantanna) oraz 2 odrębne źródła as-of](STEP_11_XG10_STRATIFIED.md), [140/140 CI #40309316442](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40309316442), [integracja observed-at + ELO + realne Drive 80 wyników / 1 xG](STEP_11_OBSERVED_FEATURES.md), [125/125 CI #40306542175](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40306542175), [xG 3/3 z osobnym audytem](STEP_11_XG_IDENTITY_REVIEW.md), [111/111 CI #40302235918](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40302235918), [dwa snapshoty i xG](STEP_11_TWO_PIT_XG.md), [91/91 testów #40298663945](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40298663945), [pierwsza rzeczywista obserwacja PIT](STEP_11_PIT_OBSERVATION.md), [manifest i offsite](../data/audits/STEP11_PIT_LIVE_CAPTURE_2026-10-26.json), [testy 82/82 #40296978637](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40296978637), [backup+restore GDrive](STEP_11_OFFSITE_ARCHIVE.md), [poprzednie testy 66/66 #40292159243](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40292159243), [xG #40291895443](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40291895443), [katalog i blokady](STEP_11_PROGRESS.md) | START: 26.10.2026, ODBIÓR: 2026-10-26

#### Krok 12 — Podział TRAIN / VALIDATION / TEST  [ZALICZONY — GATE12 PASS]

- **CO ZROBIĘ:** Stworzyć chronologiczny podział i walk-forward; oddzielić drużyny/spotkania i daty informacji od wyników.
- **CO ROBISZ TY:** Akceptacja metodologii testów przed treningiem.
- **NARZĘDZIA I KOSZT:** Python/scikit-learn; 0 zł.
- **BRAMKA ODBIORU / TEST PASS:** Czas trenowania jest wcześniejszy od czasu testu, brak przekroczeń granic i przecieków; podział zapisany i niezmienny dla danej wersji eksperymentu.
- **DOWÓD ZALICZENIA:** Plik manifestu splitu, liczby prób i test niezmienności.
- **ZALEŻY OD:** Krok 11.
- **STATUS:** ZALICZONY — GATE12 PASS METODOLOGIA 2026-10-26 | Metoda: 760 TRAIN / 380 VALIDATION / 380 TEST, 4 kwartalne wspólne walidacje 60/126/123/71, warianty EXPANDING oraz ROLLING 24 miesiące, zero przecieków TEST i zero zmian zamrożonych źródeł. [Protokół PASS](../data/audits/STEP12_METHOD_GATE_PASS_2026-10-26.json), [zamrożone okna](../data/splits/STEP12_DUAL_WINDOWS_REAL_2026-10-26.json), [realny raport blokad danych](../data/audits/STEP12_REAL_PIT_GAP_REPORT_2026-10-26.json). **ODBIÓR WYŁĄCZNIE METODOLOGII; 0/1520 gotowych do treningu, training_allowed=false; krok13 nie rozpoczęty.** DATA ODBIORU: 2026-10-26.


**Decyzja 26.10.2026:** GATE11 PASS dotyczy inżynierii cech według pierwotnego testu: znacznik czasu i opis każdej cechy, zakaz lookahead oraz `null` przy brakującym xG. Testy offline 246/246 PASS. Niezrealizowane obserwacje z różnych dni, pełne pokrycie xG i historyczne provider-published-at należą do następnych kontroli jakości, NIE retroaktywnie do bramki 11. `training_allowed=false`; nie ma aprobaty produkcyjnej.

### Etap D. Modele i testy

#### Krok 13 — Baseline ELO i Poisson  [ZALICZONO — PIERWOTNY ZAKRES]

- **CO ZROBIĘ:** Zbudować prosty silnik prognoz 1X2 oraz goli, z odrębnym testem na historii.
- **CO ROBISZ TY:** Przejrzeć pierwsze wyniki referencyjne.
- **NARZĘDZIA I KOSZT:** Python, biblioteki matematyczne; 0 zł.
- **BRAMKA ODBIORU / TEST PASS:** P(1)+P(X)+P(2) sumują się do 1; prognozy nie korzystają z kursów; wzorcowe przykłady i testy historyczne przechodzą.
- **DOWÓD ZALICZENIA:** Raport baseline z Brier, log loss, kalibracją, wersją danych i uruchomieniem testów.
- **ZALEŻY OD:** Krok 12.

- **ODBIÓR 27.10.2026 — ZALICZONO / GATE13_ORIGINAL_SCOPE PASS:** na wyraźną decyzję właściciela projektu, po krótkim niezależnym audycie opartym na podpisanych raportach, **nie uzależniając pierwotnej budowy M0 od rozegrania kolejnych 10+10 meczów**. [Protokół formalny](STEP_13_FINAL_ACCEPTANCE_2026-10-27.md) · [automatyczny audyt](../data/audits/STEP13_ORIGINAL_BASELINE_ACCEPTANCE_2026-10-27.json) · [testy PASS #40472267733](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40472267733). Silnik ELO+Poisson, normalizacja P(1X2), brak kursów i referencje matematyczne PASS; **prawdziwy retrospektywny** test 760 TRAIN + 380 VALIDATION, 4 foldy, Brier/log loss/ECE, podpisana wersja danych PASS w **ograniczonym zakresie**. Wyniki EXPANDING: logloss 1.03263674, Brier sum3 0.61853690, fold-ECE 0.07395339. ROLLING: 1.03438039, 0.61968817, 0.07331601. **Zaliczenie kroku to nie dowód historycznego PIT, stabilnego zysku ani wybór championa.** Dalsze użycie danych historycznych do trenowania modelu produkcyjnego wciąż niedopuszczone (`training_allowed=false`). Prognozy 20 prematch pozostają zamrożone, ich przyszłe wyniki będą rozliczane odrębnie. **POSTĘP: 13/29, KROK 14 OTWARTY TYLKO DO PRZYGOTOWANIA.**

- **STATUS ARCHIWALNY (stan przed końcowym odbiorem):** W REALIZACJI od 2026-10-26. M0 ELO+Poisson matematyka PASS (3 przykłady syntetyczne). Rozpoczęto też [kontrolowany walk-forward replay](STEP_13_REPLAY_CONTRACT.md) dwóch historii: 4 foldy i 48h embargo, testy na wyłącznie syntetycznych wynikach PASS; sprawdzono niezmienność prognoz przy podmianie etykiet walidacji, brak TEST i kursów. [Realny raport gotowości terminarza 1520 ID](../data/audits/STEP13_REAL_FOLD_READINESS_2026-10-26.json) — PRAWIDŁOWY podział, **0 certyfikowanych historycznych PIT**; żaden prawdziwy backtest nie został wykonany, Brier/logloss/kalibracja z historii PENDING. **DODATKOWO v0.3:** [mechanizm dopasowania Poissona do TRAIN](../src/kb3_step13_poisson_train.py) metodą maksimum wiarygodności i stałej siatki parametru Elo, testy negatywne odrzucania VALIDATION/TEST, odds i późnych wyników. [Zamrożony raport wyłącznie SYNTETYCZNEGO dopasowania 12 rekordów](../data/audits/STEP13_SYNTHETIC_POISSON_FIT_V03_2026-10-26.json). Realnych wytrenowanych meczów nadal 0 i nie ma historycznych wyników skuteczności. **Dalszy postęp w tym samym kroku13:** [kod badawczego retrospektywnego backtestu na istniejącym 1140 historycznym archiwum](../src/kb3_step13_retrospective.py) i [uruchamiany lokalnie czytnik zabezpieczonego ZIP](../scripts/step13_pitch_retrospective_local.py). Eksperyment w trybie RECONSTRUCTED_EVENT_TIME_RESEARCH_NOT_VERIFIED_PIT, nie równoważny certyfikowanej historycznej prognozie prematch. Kod i testy syntetyczne przygotowane; prawdziwego ZIP nie odszyfrowano ani nie policzono metryk w CI, bo klucz prywatny jest poza GitHubem. **Zweryfikowano teraz oryginalne szyfrowane archiwum ZIP z Google Drive bez odszyfrowywania**: 31 907 bajtów, zgodne ZIP/cipher/manifest/chain SHA. [Niezmienny raport realnego pliku](../data/audits/STEP13_ORIGINAL_SEALED_ZIP_PREFLIGHT_2026-10-26.json), [walidator](../src/kb3_step13_archive_preflight.py). 9 lokalnych kontroli pozytywnych; cztery testy GitHub Actions na commitcie PR #34 PONOWIONE i PASS (Retrospective Research, Poisson TRAIN-only, M0 offline, Fold Replay); rzeczywiste wyniki nadal zaszyfrowane. Prywatny klucz nadal wymagany do odczytu wyników i realnego backtestu. Nie dodano żadnego nowego kroku do planu; **Dodatkowo 27.10.2026:** przygotowany [lokalny launcher Windows 10](../scripts/step13_windows_local_start.ps1) dla właściciela z RSA PEM/KEY na ASUS-ie, wybierający oryginalny ZIP i klucz przez okna wyboru plików; raport tylko w prywatnym folderze na Windows. Runner uruchamia istniejącą matematykę i autentyczną retrospektywną walidację bez TEST; nie stwierdzono jeszcze jego wykonania na laptopie właściciela. Brak nowego kroku, brak produkcji. **GATE13 PENDING, training_allowed=false, 12/29.**


**REALNY RETROSPEKTYWNY TEST 27.10.2026:** [1140 dopasowanych natywnych historycznych wyników PitchAPI — raport wyłącznie agregatowy](../data/audits/STEP13_REAL_RETROSPECTIVE_PITCHAPI_2026-10-27.json), 760 TRAIN, 380 VALIDATION, TEST 0; 4 zamrożone kwartalne foldy 60/126/123/71. Wynik EXPANDING log loss=**1.032637**, Brier sum3=**0.618537**, fold-ECE=0.073953. ROLLING log loss=1.034380, Brier=0.619688, fold-ECE=0.073316. Różnica minimalna, brak produkcyjnego zwycięzcy; brak historii autentycznych obserwacji prematch PIT. [Akcja PASS](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40422326740). Dane pobrano przez darmowy, istniejący PitchAPI (3 wywołania), bez RSA, nowych kosztów, klucza w logach ani danych TEST. Zmiana dotyczy wyłącznie istniejącego kroku13. **GATE13 PENDING, training_allowed=false, nadal 12/29; krok14 nie rozpoczęty.**


**AUDYT STABILNOŚCI 27.10.2026, W TYM SAMYM KROKU13:** [agregaty i 4 kwartalne diagnozy](../data/audits/STEP13_REAL_RETROSPECTIVE_STABILITY_2026-10-27.json), SHA `10e75ea0a247ca3d446379238ac4f97aab6be90f8ee55aac6796cf7d83bdeb8e`. Prawdziwe walidacyjne wyniki top1 1X2: EXPANDING **185/380 (48.68%)**, ROLLING **184/380 (48.42%)**. W I–III 2026 zaledwie **48/123 (39.0%)** przy średniej deklarowanej szansie **49.7% EXP / 48.8% ROLL**, czyli wyraźna zła kwartalna kalibracja. Pooled ECE 0.0169 / 0.0103 maskuje zmiany znaków błędów; preferujemy do oceny stabilności kwartalne weighted ECE 0.0740 / 0.0733. W 8/8 foldach elastyczność ELO równa górnej granicy pierwotnej siatki 0.6; **nie stroimy z walidacji**. Bez pobierania API i bez danych TEST. **GATE13 PENDING, training_allowed=false, 12/29, krok14 nie rozpoczęty.**

**DIAGNOSTYKA TYLKO TRAIN, 27.10.2026 (w ramach KROKU13):** [raport 760 rzeczywistych meczów](../data/audits/STEP13_TRAIN_760_ELO_ELASTICITY_DIAGNOSTIC_2026-10-27.json). W dodatkowej siatce ELO 0.0–1.2 tylko na TRAIN bramkowy Poisson NLL minimalny przy 1.0 (3.055322); w pierwotnej siatce 0.0–0.6 minimum 0.6 (3.071748). Dla 2023/24 minimum badanej siatki 1.2 (brzeg), dla 2024/25 0.9 — niestabilność między sezonami. To NIE log loss 1X2 z VALIDATION i nie podstawa do aktualizacji modelu. Pobranie: tylko 2 sezony TRAIN, zero VALIDATION, zero TEST. [CI PASS](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40425365353). **GATE13 PENDING, training_allowed=false, 12/29; bez zmiany kroków14–29.**


**PRAWIDŁOWA KONTROLA ISTOTNOŚCI PORÓWNANIA 27.10.2026 (nadal KROK13):** [sparowany raport 380 meczów z 3000 resamplingów tygodniowych](../data/audits/STEP13_REAL_PAIRED_UNCERTAINTY_2026-10-27.json), [GitHub Actions PASS](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40457581450). Delta logloss ROLL−EXP **+0,001744**, bootstrap 95% **[−0,000379, +0,003835]**; delta Brier **+0,001151**, bootstrap 95% **[−0,000496, +0,002724]**. Oba przedziały obejmują zero — nie wybierać zwycięzcy, nie promować parametrów, nie dodawać modelu. Kontrola wszystkich 4 foldów zgodna z podpisanym źródłowym raportem, TEST=0, historyczny prematch PIT nieudowodniony. **GATE13 PENDING; training_allowed=false; 12/29; krok14 nierozpoczęty.**


**NOWY DOWÓD PROSPECTIVE — 27.10.2026 (BEZ ZMIANY KROKU13):** [10 autentycznie przedmeczowych prognoz M0 Elo+Poisson](../data/forecasts/STEP13_FIRST_PROSPECTIVE_PREMATCH_2026-10-27.json) zamrożonych `2026-10-27T06:12:08.707287Z` na mecze 31.10–02.11.2026, SHA `9c346f79b1868fd1cb0d4d4ffa066f6f1629e09bbc6ce0454c5c8901e7645389`, [GitHub Actions PASS](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40459673538). Dokładnie 760 TRAIN do parametrów i ratingów, `VALIDATION wyniki=0`, `TEST wyniki=0`; z TEST tylko przyszła lista `upcoming` z pustym score. **PIT teraz przed kickoff, ale nie certyfikuje dawnego historycznego PIT**. Ratingi są celowo nieaktualne od końca TRAIN w 2025 r.; model shadow, bez zakładów i bez oceny skuteczności przyszłych wyników. **GATE13 PENDING, training_allowed=false, nadal 12/29, krok14 nierozpoczęty.**


**27.10.2026 — ZAMROŻONO ZASADY PRZYSZŁEJ OCENY 10 REALNYCH PROGNOZ PREMATCH (nadal KROK13):** [kontrakt z góry](STEP_13_FORWARD_SCORING_CONTRACT.md), [czysty scorer](../src/kb3_step13_forward_score.py), [testy bezpieczeństwa](../tests/test_step13_forward_score.py). Wyłącznie 10 natywnych meczów z przedmeczowego [snapshotu SHA `9c346f79...`](../data/forecasts/STEP13_FIRST_PROSPECTIVE_PREMATCH_2026-10-27.json), nie 370 pozostałych TEST. Po zakończeniu wszystkich spotkań i 3-godzinnym bezpieczniku wolno jednorazowo porównać zamrożone P z autentycznie później zarejestrowanymi 10 wynikami: top1 accuracy, log loss, Brier sum3, ECE (wyłącznie opisowe n=10), Poisson NLL i MAE goli. Dopiero przyszła, osobna obserwacja PitchAPI może dostarczyć rzeczywistych wyników, nie dziś; **testy tylko syntetyczne, 0 odczytów TEST**, żadnego strojenia po fakcie. GATE13 PENDING, training_allowed=false, 12/29 i krok14 nadal nie rozpoczęty.


**27.10.2026 — DODATKOWE CZTERY KONTROLE (PR #43, W RAMACH KROKU 13 Z 29, licznik ukończonych 12/29):** 1) [audyt matematyki ELO+Poisson](../data/audits/STEP13_MATH_INDEPENDENT_2026-10-27.json) 25 sztucznych par + 10 ponownie obliczonych przypiętych autentycznych prognoz, zgodności wzorów 1X2, BTTS, over, Elo conservation PASS; 2) [audyt przecieków](../data/audits/STEP13_LEAKAGE_INDEPENDENT_2026-10-27.json) tylko TRAIN played i tylko przyszły TEST upcoming, 0 odczytu wyników TEST (ograniczony do tego kodu i danych); 3) [drugi niezależnie zamrożony prematch snapshot](../data/forecasts/STEP13_SECOND_PROSPECTIVE_PREMATCH_2026-10-27.json) z 10 meczów 06–08.11.2026, SHA `bca520ffd20021cf984189c6aa5a15eda078b5a501f32345c87c334d6c3b045e`, razem 20 prognoz; 4) [bezpieczny przyszły kolektor wyników tylko pierwszej dziesiątki](../scripts/step13_first_ten_secure_postmatch_once.py), ręczny i niedostępny przed końcem wszystkich meczów, dokładnie `matches.get` dla 10 ID, szyfrowane źródło i zagregowane miary, [testy syntetyczne PASS](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40466814515). Nie odczytano realnych wyników tych meczów, a historyczny PIT nieudowodniony, nie zmieniano Elo/Poisson ani 29-etapowego planu. **GATE13 PENDING, training_allowed=false, 12/29 ukończone, CatBoost nierozpoczęty.**

#### Krok 14 — Pierwszy CatBoost 1X2  [W REALIZACJI — PRZYGOTOWANIE]

- **CO ZROBIĘ:** Wytrenować niezależny ML dla 1/X/2 na cechach przedmeczowych.
- **CO ROBISZ TY:** Brak programowania; ocenić czy rozumiesz sposób raportowania.
- **NARZĘDZIA I KOSZT:** Python, CatBoost, CPU GitHub/alternatywny runner; bez kosztu na start.
- **BRAMKA ODBIORU / TEST PASS:** Trening jest odtwarzalny (wersja danych, seed, parametry); eksport modelu działa; P sumuje się do 1; test bez przyszłych danych przechodzi.
- **DOWÓD ZALICZENIA:** Plik modelu z hashem, metryki TEST, log uruchomienia.
- **ZALEŻY OD:** Krok 13.
- **STATUS:** W REALIZACJI od 27.10.2026 — **techniczny pipeline CatBoost M1, testy syntetyczne i audyt pochodzenia wdrożone; 28/28 niezależnych testów CI PASS** ([Actions #40479522446](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40479522446), [PR #45](https://github.com/karolbarankiewicz1984-ui/kb-score-3/pull/45)). **To NIE jest oryginalny końcowy TEST PASS ani trening rzeczywisty:** historyczny prematch PIT niecertyfikowany, realny M1 niewytrenowany, GATE14 PENDING, `real_catboost_fit_eligible=false`, produkcja zabroniona. DOWÓD: [kontrakt syntetyczny i bramka danych](STEP_14_SYNTHETIC_CONTRACT.md), [karta otwarcia](STEP_14_KICKOFF.md) | ODBIÓR: —.

#### Krok 15 — Modele goli i spójność rynków  [NIE ROZPOCZĘTO]

- **CO ZROBIĘ:** Obliczać O/U 1,5/2,5/3,5, BTTS, team totals; porównać model bramkowy i warianty ML.
- **CO ROBISZ TY:** Przejrzeć sposób prezentacji rynków.
- **NARZĘDZIA I KOSZT:** Python, Poisson/CatBoost; 0 zł.
- **BRAMKA ODBIORU / TEST PASS:** Over 3,5 nie większy niż Over 2,5; wyniki wszystkich rynków zgodne z definicją 90 minut; testy znanych rozkładów przechodzą.
- **DOWÓD ZALICZENIA:** Testy własności matematycznych i raport prób na spotkaniach testowych.
- **ZALEŻY OD:** Kroki 13–14.
- **STATUS:** NIE ROZPOCZĘTO | TEST: NIE URUCHOMIONO | LINK DOWODU: — | DATA ODBIORU: —

#### Krok 16 — Kalibracja prawdopodobieństw  [NIE ROZPOCZĘTO]

- **CO ZROBIĘ:** Sprawdzić reliability bins, Brier/log loss; dobrać kalibrację bez trenowania na TEST.
- **CO ROBISZ TY:** Ocenić, czy raport wyjaśnia działanie P.
- **NARZĘDZIA I KOSZT:** scikit-learn / biblioteki; 0 zł.
- **BRAMKA ODBIORU / TEST PASS:** Kalibracja uczona wyłącznie na wydzielonych danych; metryki TEST liczone raz według zaplanowanej procedury; brak nieuprawnionego użycia oryginalnego P(cal).
- **DOWÓD ZALICZENIA:** Wykres/raport kalibracji, protokół podziału i wyniki przed/po.
- **ZALEŻY OD:** Kroki 14–15.
- **STATUS:** NIE ROZPOCZĘTO | TEST: NIE URUCHOMIONO | LINK DOWODU: — | DATA ODBIORU: —

#### Krok 17 — Porównanie silników  [NIE ROZPOCZĘTO]

- **CO ZROBIĘ:** Porównać ELO, Poisson, CatBoost bez xG, CatBoost z xG i ewentualny ensemble.
- **CO ROBISZ TY:** Przejrzeć czy wnioski są zrozumiałe i uczciwe.
- **NARZĘDZIA I KOSZT:** Python, testy statystyczne, tabele wyników; 0 zł.
- **BRAMKA ODBIORU / TEST PASS:** Wspólne spotkania/rynki, te same horyzonty czasowe, przedziały niepewności i koszt braków danych; brak wyboru zwycięzcy wyłącznie na podstawie jednej serii.
- **DOWÓD ZALICZENIA:** Macierz wyników, liczebności, metryki i test uczciwego porównania.
- **ZALEŻY OD:** Krok 16.
- **STATUS:** NIE ROZPOCZĘTO | TEST: NIE URUCHOMIONO | LINK DOWODU: — | DATA ODBIORU: —

#### Krok 18 — Wybór Champion — wersja bazowa  [NIE ROZPOCZĘTO]

- **CO ZROBIĘ:** Wybrać wersję dopuszczoną do prognoz testowych i zamrozić jej parametry.
- **CO ROBISZ TY:** Zatwierdzić wybór po obejrzeniu wyników; można wybrać brak awansu.
- **NARZĘDZIA I KOSZT:** GitHub tag/release, dokument decyzji; 0 zł.
- **BRAMKA ODBIORU / TEST PASS:** Decyzja zawiera metryki porównawcze, dokładną wersję, datę, zakres i powód; model odtwarzalny z zamrożonych danych; fallback dostępny.
- **DOWÓD ZALICZENIA:** Karta awansu Champion z commit SHA i identyfikatorem modelu, zatwierdzenie.
- **ZALEŻY OD:** Krok 17.
- **STATUS:** NIE ROZPOCZĘTO | TEST: NIE URUCHOMIONO | LINK DOWODU: — | DATA ODBIORU: —

### Etap E. Kursy, freeze i rozliczenia

#### Krok 19 — Historyczne i bieżące kursy  [NIE ROZPOCZĘTO]

- **CO ZROBIĘ:** Pobierać dokładne rynki i linie wraz z datą, bukmacherem, marżą oraz limitem czasowym; nie rekonstruować brakujących historycznych kursów.
- **CO ROBISZ TY:** Potwierdzić zakres bukmacherów i ewentualny zakup dopiero po raporcie.
- **NARZĘDZIA I KOSZT:** Obecne odds API-Football, ewentualny dostawca po zgodzie.
- **BRAMKA ODBIORU / TEST PASS:** Każdy kurs ma market+line+provider+timestamp; niewiarygodna linia nie jest porównywana; EV obliczone na kontrolnych przykładach bez pomyłek.
- **DOWÓD ZALICZENIA:** Próbka zapisów kursów, raport pokrycia i test matematyki EV/no-vig.
- **ZALEŻY OD:** Kroki 8, 18.
- **STATUS:** NIE ROZPOCZĘTO | TEST: NIE URUCHOMIONO | LINK DOWODU: — | DATA ODBIORU: —

#### Krok 20 — Rankingi jakości, szans i wartości  [NIE ROZPOCZĘTO]

- **CO ZROBIĘ:** Stworzyć osobne rankingi HIGH PROBABILITY, VALUE CANDIDATE, WATCH i NO BET; nie mieszać wysokiego P z dodatnim EV.
- **CO ROBISZ TY:** Wybrać preferencje prezentacji i budżet ostrożności, bez hazardowego automatu.
- **NARZĘDZIA I KOSZT:** Logika selekcji, dane z testów; 0 zł.
- **BRAMKA ODBIORU / TEST PASS:** Ten sam mecz i kurs dają tę samą klasyfikację; niska jakość danych blokuje publikowanie pewnych rekomendacji; progi mają uzasadnienie w walidacji.
- **DOWÓD ZALICZENIA:** Tabela warunków, przykłady graniczne i testy regresyjne.
- **ZALEŻY OD:** Kroki 16–19.
- **STATUS:** NIE ROZPOCZĘTO | TEST: NIE URUCHOMIONO | LINK DOWODU: — | DATA ODBIORU: —

#### Krok 21 — Niezmienialny przedmeczowy freeze  [NIE ROZPOCZĘTO]

- **CO ZROBIĘ:** Zapisać każdą prognozę z wersją modelu, danymi, czasem pobrania, czasem rozpoczęcia i kursami; osobno EARLY i FINAL PREMATCH.
- **CO ROBISZ TY:** Nie musisz utrwalać ręcznie; możesz przeglądać archiwum.
- **NARZĘDZIA I KOSZT:** Baza, manifest hashe, log GitHub; 0 zł.
- **BRAMKA ODBIORU / TEST PASS:** Zmiana starego rekordu jest odrzucana; test próby zapisu po kickoff skutkuje BLOCKED; niezależny odczyt zwraca pierwotny timestamp i P.
- **DOWÓD ZALICZENIA:** Freeze ID, kontrola hasha, wynik testu no-lookahead i przykładowy odczyt.
- **ZALEŻY OD:** Kroki 8, 20.
- **STATUS:** NIE ROZPOCZĘTO | TEST: NIE URUCHOMIONO | LINK DOWODU: — | DATA ODBIORU: —

#### Krok 22 — Automatyczne rozliczanie  [NIE ROZPOCZĘTO]

- **CO ZROBIĘ:** Zakończone mecze powiązać z prognozami, rozliczyć dokładny rynek i obliczyć Brier, log loss, WIN/LOSS/PUSH/VOID.
- **CO ROBISZ TY:** Przejrzeć audyt próbki historycznej.
- **NARZĘDZIA I KOSZT:** API-Football, lokalna baza, testy rynku; 0 zł.
- **BRAMKA ODBIORU / TEST PASS:** Przykładowe poprawne/odwołane/przełożone mecze rozliczone zgodnie z regułami; brak dubli; settlement nie przepisuje dawnej prognozy.
- **DOWÓD ZALICZENIA:** Raport settlement i zestaw testów WIN/LOSS/PUSH/VOID.
- **ZALEŻY OD:** Krok 21.
- **STATUS:** NIE ROZPOCZĘTO | TEST: NIE URUCHOMIONO | LINK DOWODU: — | DATA ODBIORU: —

### Etap F. PDF i automatyzacja

#### Krok 23 — Generator 3 PDF  [NIE ROZPOCZĘTO]

- **CO ZROBIĘ:** Przygotować czytelne raporty DZIS, JUTRO, POJUTRZE z prognozami, zastrzeżeniami, źródłami, kursami i audytem.
- **CO ROBISZ TY:** Zaakceptować szablon czytelny na telefonie.
- **NARZĘDZIA I KOSZT:** Python, PDF, Google Drive; 0 zł.
- **BRAMKA ODBIORU / TEST PASS:** Trzy PDF otwierają się; polskie znaki i zakres dat poprawne; brak wymyślonych danych; przykład niskiej jakości oznaczony jako WATCH; kontrola automatyczna zawartości i ręczny odbiór wyglądu.
- **DOWÓD ZALICZENIA:** 3 przykładowe PDF, raport kontroli tekstu/stron i zatwierdzony szablon.
- **ZALEŻY OD:** Kroki 20–22.
- **STATUS:** NIE ROZPOCZĘTO | TEST: NIE URUCHOMIONO | LINK DOWODU: — | DATA ODBIORU: —

#### Krok 24 — Harmonogram i kontrola uruchomienia  [NIE ROZPOCZĘTO]

- **CO ZROBIĘ:** Automatycznie zbierać dane, wyliczać, zamrażać, rozliczać i publikować w strefie Europe/Warsaw; kontrolować opóźnienia i ponowienia.
- **CO ROBISZ TY:** Potwierdzić docelową godzinę 09:30 i zakres 3 dni; może być zmienione.
- **NARZĘDZIA I KOSZT:** GitHub Actions, monitoring, trwałe składowanie; bez opłat w limitach.
- **BRAMKA ODBIORU / TEST PASS:** Test ręczny i test harmonogramu przechodzą; każdy błąd wywołuje kontrolowany retry albo alarm; brak podwójnej publikacji; archiwum nie zależy tylko od artefaktów Actions.
- **DOWÓD ZALICZENIA:** Linki do przebiegów Actions, próbna dostawa 3 PDF i raport retry/failure.
- **ZALEŻY OD:** Krok 23.
- **STATUS:** NIE ROZPOCZĘTO | TEST: NIE URUCHOMIONO | LINK DOWODU: — | DATA ODBIORU: —

#### Krok 25 — Wysyłka i powiadomienia  [NIE ROZPOCZĘTO]

- **CO ZROBIĘ:** Dostarczać PDF wybraną metodą; błędy i braki danych sygnalizować, ale nie wysyłać fikcyjnego raportu.
- **CO ROBISZ TY:** Wybrać odbiorcę i zatwierdzić dostęp do wysyłki, nie podawać hasła w czacie.
- **NARZĘDZIA I KOSZT:** Gmail/SMTP lub inny bezpieczny mechanizm po autoryzacji.
- **BRAMKA ODBIORU / TEST PASS:** Dostarczenie testowego raportu potwierdzone; brak duplikatu i wycieku danych; celowo wymuszony błąd powoduje właściwe powiadomienie.
- **DOWÓD ZALICZENIA:** Testowy e-mail/odbiór w Drive, log z redakcją danych oraz test alarmu.
- **ZALEŻY OD:** Krok 24.
- **STATUS:** NIE ROZPOCZĘTO | TEST: NIE URUCHOMIONO | LINK DOWODU: — | DATA ODBIORU: —

### Etap G. Nauka kontrolowana

#### Krok 26 — Champion–Challenger — okresowe trenowanie  [NIE ROZPOCZĘTO]

- **CO ZROBIĘ:** Nowe wyniki powiększają bazę, lecz nie zmieniają automatycznie oficjalnego modelu; test nowej wersji odbywa się osobno.
- **CO ROBISZ TY:** Zatwierdzać tylko istotne awanse modelu.
- **NARZĘDZIA I KOSZT:** Python, CI/CD, rejestr modeli; koszt wg czasu obliczeń.
- **BRAMKA ODBIORU / TEST PASS:** Challenger przechodzi niezależne testy; wersja produkcyjna nie zmienia się bez decyzji; istnieje sprawdzony rollback; trening loguje dane i ustawienia.
- **DOWÓD ZALICZENIA:** Raport champion/challenger, protokół awansu i test powrotu do starej wersji.
- **ZALEŻY OD:** Kroki 18, 22, 24.
- **STATUS:** NIE ROZPOCZĘTO | TEST: NIE URUCHOMIONO | LINK DOWODU: — | DATA ODBIORU: —

#### Krok 27 — Monitoring jakości i degradacji  [NIE ROZPOCZĘTO]

- **CO ZROBIĘ:** Kontrolować dryf danych, pogorszenie Brier/log loss, braki ligowe i stabilność prognoz w czasie.
- **CO ROBISZ TY:** Zapoznawać się z sygnałami ostrzegawczymi i decydować o ograniczeniach.
- **NARZĘDZIA I KOSZT:** Monitor metryk, powiadomienia; 0 zł na start.
- **BRAMKA ODBIORU / TEST PASS:** Celowo zepsute dane powodują alarm/blokadę; poprawne dane nie generują fałszywej awarii; istnieją jawne progi i reakcja systemu.
- **DOWÓD ZALICZENIA:** Dziennik kontrolowanego testu awarii i dashboard jakości.
- **ZALEŻY OD:** Kroki 22, 25, 26.
- **STATUS:** NIE ROZPOCZĘTO | TEST: NIE URUCHOMIONO | LINK DOWODU: — | DATA ODBIORU: —

### Etap H. Rynki specjalne i panel

#### Krok 28 — Modele rożnych, kartek i fauli  [NIE ROZPOCZĘTO]

- **CO ZROBIĘ:** Osobno przetestować rodziny rynków, z uwagą na rzeczywiste definicje statystyk i dokładne linie; faule Under jako osobny moduł.
- **CO ROBISZ TY:** Zatwierdzić kolejność rozwoju, dopiero po wynikach testów podstawowych.
- **NARZĘDZIA I KOSZT:** API-Football/PitchAPI jeśli dane wystarczą; koszt dopiero po audycie.
- **BRAMKA ODBIORU / TEST PASS:** Każda rodzina ma osobny zbiór, freeze, wyniki, benchmark i próbę walk-forward; brak awansu przy niskiej jakości lub nieporównywalnych liniach.
- **DOWÓD ZALICZENIA:** Raport per rynek i osobna karta dopuszczenia/odrzucenia.
- **ZALEŻY OD:** Kroki 10–27.
- **STATUS:** NIE ROZPOCZĘTO | TEST: NIE URUCHOMIONO | LINK DOWODU: — | DATA ODBIORU: —

#### Krok 29 — Opcjonalny panel mobilny  [NIE ROZPOCZĘTO]

- **CO ZROBIĘ:** Zaprojektować panel z kalendarzem, historią, P(model), oceną rynku, raportami i statusem bramek.
- **CO ROBISZ TY:** Ocenić czy panel jest potrzebny i wybrać sposób korzystania z telefonu.
- **NARZĘDZIA I KOSZT:** Strona PWA, ewentualnie Base44 po odrębnej decyzji.
- **BRAMKA ODBIORU / TEST PASS:** Panel pokazuje dokładnie dane z archiwum i nie generuje alternatywnych wartości; test mobilny, autoryzacji oraz dostępności przebiega poprawnie.
- **DOWÓD ZALICZENIA:** Link do panelu, test mobilny i odbiór użytkownika.
- **ZALEŻY OD:** Krok 24, opcjonalny.
- **STATUS:** NIE ROZPOCZĘTO | TEST: NIE URUCHOMIONO | LINK DOWODU: — | DATA ODBIORU: —


## Krok 08 — dodatkowy dowód odbioru

**08 PASS (25.10.2026):** [schemat SQLite](../migrations/001_initial_schema.sql), [testy backupu i blokady prognoz](../tests/test_step08_storage.py), [protokół](STEP_08_ACCEPTANCE.md). Google Drive zawiera wyłącznie niezaszyfrowany backup **syntetyczny**. Produkcyjne backupy wymagają szyfrowania i automatyzacji przed przyjęciem prawdziwych danych.

## Jak wznowić pracę

W nowej rozmowie wystarczy: „Otwórz plan KB Score 3.0 na Dysku Google; podaj status i dowody ostatniej bramki”. Do odbioru wymagany jest zawsze **aktualny odczyt** planu i dowodów, a nie pamięć czatu.

## Aktualne dowody pierwszych kroków

- **01 PASS (24.10.2026):** audyt kont, limitów i budżetu — protokół w [Google Docs](https://docs.google.com/document/d/10wjHL3r3OAuxtezwcIeWztxS8lwjhYon5GM3BLhI0xE/edit).
- **02 PASS (25.10.2026):** [prywatne repozytorium](https://github.com/karolbarankiewicz1984-ui/kb-score-3) i [commit struktury](https://github.com/karolbarankiewicz1984-ui/kb-score-3/commit/7c6cee2be18b3a771d0d94ccd3f6841f7f6d83a6).
- **03 PASS (25.10.2026):** [odczyt API-Football i PitchAPI](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40203074557) oraz [checklista bezpieczeństwa](STEP_03_SECURITY_CHECKLIST.md).
- **04 PASS (25.10.2026):** cztery dokumenty, 29/29 bramek, poprawne linki i [protokół odbioru GATE 04](STEP_04_ACCEPTANCE.md).
- **05 PASS (25.10.2026):** [GATE 05](STEP_05_ACCEPTANCE.md), [30-wierszowy audyt API-Football](audits/API_FOOTBALL_STEP05_2026-10-25.md) i dwa testy GitHub Actions.

- **06 PASS (25.10.2026):** [GATE 06 — protokół po korekcie LaLiga](STEP_06_ACCEPTANCE.md), [30 sezonów i 60 kompletnych próbek xG](audits/PITCHAPI_STEP06_2026-10-25.md), [GitHub Actions SUCCESS](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40235545588).

- **07 PASS (25.10.2026):** [GATE07 — protokół](STEP_07_ACCEPTANCE.md), [38 ścisłych i kolejka 22](audits/STEP07_MATCH_CROSSWALK_2026-10-25.md), [uruchomienie SUCCESS](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40236615477). Kolejka pozostaje nierozstrzygnięta; nie traktować jako mapy całej historii.


## Krok 09 — dodatkowy dowód odbioru

**09 PASS TECHNICZNY (26.10.2026):** [protokół](STEP_09_ACCEPTANCE.md), [manifest](../data/audits/STEP09_IMPORT_2026-10-26.json), [test na rzeczywistych danych](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40277192712). Prywatna, zaszyfrowana kopia na Drive została niezależnie pobrana i przywrócona; właściciel powinien zabezpieczyć wydany plik klucza odzyskiwania. Kolejny etap — 10.


## Krok 10 — odbiór końcowy (26.10.2026)

**PASS / ZALICZONO:** [pełny protokół](STEP_10_ACCEPTANCE.md), [manifest odbioru](../data/audits/STEP10_FINAL_2026-10-26.json). Pięć lig, 30 kombinacji liga×sezon i 10 679 wpisów; 10 sezonów z nadmiarowymi meczami przeanalizowano po nazwach rund. 19 baraży oddzielono, jeden mecz z wynikiem AWD wyłączono z normalnych etykiet, 54/54 testów PASS. Statystyki/xG/odds i chronologia realnych prematch snapshots nie są jeszcze gotowe: **trening zablokowany**, prace przy cechach w kroku 11. Postęp **10/29**.

**26.10.2026 — PONOWNA INTERPRETACJA WG ORYGINALNEJ BRAMKI:** Rozdzielono odbiór metodyki podziału od gotowości danych treningowych. Niezależny audyt 1520 rzeczywistych fixture, podział 760/380/380 i foldy VALIDATION: 60,126,123,71 (razem 380). [Bezpieczny widok bez hashy wyników](../data/splits/STEP12_SAFE_MODEL_VIEW_2026-10-26.json) i [audyt formalny](../data/audits/STEP12_INDEPENDENT_METHODOLOGY_2026-10-26.json) — SHA widoku `3b8da84b334d897e327c883b769944bf36016cb44daf1da041bfb7d16a7b11e7`. Oryginalny manifest zachowany jako AUDIT-ONLY (zawiera hash zależny od etykiet). [Propozycja decyzji właściciela](STEP_12_METHOD_DECISION.md). **Metodyka gotowa do akceptacji; GATE12 PENDING do akceptacji; trening nadal zabroniony z osobnej przyczyny braku historycznych PIT.**

**26.10.2026 — UZGODNIONA KONTYNUACJA METODYKI:** Do pierwotnego splitu 760/380/380 dodano *porównanie długości historii w walk-forward* — EXPANDING (cała wcześniejsza historia od 2023-07-01) i ROLLING (tylko poprzednie 24 miesiące). Oba warianty mają TE SAME walidacje 60,126,123,71. Rzeczywiste liczebności kandydatów TRAIN EXPANDING: 760,820,946,1069; ROLLING: 760,753,750,776, każda liczba odnosi się wyłącznie do terminu, **0 zakwalifikowanych do treningu**. [Dowód i metodę porównania](STEP_12_DUAL_WINDOWS.md) oraz [zamrożony nowy manifest](../data/splits/STEP12_DUAL_WINDOWS_REAL_2026-10-26.json) z [audytem](../data/audits/STEP12_DUAL_WINDOWS_AUDIT_2026-10-26.json) zweryfikowano offline. Użytkownik zgodził się kontynuować wdrożenie dwóch wariantów; formalna akceptacja całej metodyki przed treningiem nie została jeszcze odrębnie potwierdzona. GATE12 PENDING i training_allowed=false.

**Końcowy odbiór 26.10.2026 — GATE12 PASS (metoda, nie dane):** Wcześniejsze wzmianki o PENDING dokumentują historyczny stan w trakcie prac. Dwukrotne potwierdzenie przez użytkownika kierunku obu okien w rozmowie i ukończenie kryteriów technicznych umożliwiają zapis metodyki jako PASS. Niezależny finalny CI w GitHub Actions potwierdził 4 parowane foldy bez TEST i niezmienność manifestów; 1220 wyników RETROSPECTIVE i 300 terminarzy bez dopuszczenia cech = 0 prób gotowych na historyczny trening. **training_allowed=false** pozostaje twardą blokadą, bez fikcyjnego backtestu. [Rekord GATE12](../data/audits/STEP12_METHOD_GATE_PASS_2026-10-26.json), [realny PIT-gap](../data/audits/STEP12_REAL_PIT_GAP_REPORT_2026-10-26.json).
