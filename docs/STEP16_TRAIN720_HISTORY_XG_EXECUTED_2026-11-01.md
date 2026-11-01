# KB Score 3.0 — wykonanie historycznego uczenia i rozszerzenia xG, 1 listopada 2026

**Status:** eksperymenty badawcze naprawdę wykonane w GitHub Actions. GATE16=PENDING, GATE17=PENDING, formalnie 15/29. M0 produkcyjne/research i parametry SHA niezmienione. Nie odblokowano chronionego 2026/27 TEST.

## A. Badanie historyczne — bez czekania na nowe kolejki

Zreprodukowany historyczny zbiór M1-R: oryginalne dwa sezony TRAIN 2023/24 + 2024/25, 760 meczów w źródłowej partycji, z czego 720 dopuszczonych. Wcześniejszy zbiór 374 VALIDATION z 2025/26 został całkowicie wyłączony z wyboru cech, parametrów i oceny trzech nowych eksperymentów wewnętrznych. Z chronionego TEST nie czytano żadnych danych.

W PR [#126](https://github.com/karolbarankiewicz1984-ui/kb-score-3/pull/126) dodano skrypt **scripts/step16_train_only_walkforward_catboost.py** i dwa odseparowane workflow (trening + audyt historii). Trzy rosnące chronologiczne foldy: około 360→100, 480→100, 600→100; w rzeczywistych przebiegach łącznie 300 przyszłych względem lokalnego odcięcia meczów. Selekcja cech i fit parametrów Poissona zachodzą tylko na części poprzedzającej każdy fold. Profil CatBoost BASE, SHALLOW i ELO_FORM5 prerejestrowano przed oglądaniem raportów. Każdy realny trening wymagał wyłącznie katalogu i dwóch sezonów TRAIN PitchAPI = 3 wywołania (dwa wykonane przebiegi po 3). Brak odczytu historycznej VALIDATION 2025/26 lub TEST 2026/27.

**Wynik rzeczywistego, uczciwego porównania czterech wariantów na 300 wynikach:**

| Silnik | Trafność 1X2 | Brier multiclass sum3 | Log loss | ECE5 |
|---|---:|---:|---:|---:|
| **M0 — Elo+Poisson, ponownie fitted tylko wewnątrz wcześniejszego TRAIN** | **0,5000** | **0,619313** | **1,032689** | **0,018735** |
| CatBoost SHALLOW_FIXED | 0,4700 | 0,628357 | 1,050416 | 0,063318 |
| CatBoost BASE_FIXED | 0,4800 | 0,631690 | 1,056504 | 0,059975 |
| CatBoost ELO_FORM5_FIXED | 0,473333 | 0,636161 | 1,059603 | 0,061885 |

**Dowód:** [realny Actions #41302041310 — SUCCESS](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/41302041310). Cztery testy offline PASS, rzeczywisty fit i scorer PASS, artefakt ZIP **KB3_TRAIN_ONLY_WALKFORWARD_720_RESEARCH**. Wcześniejszy run #41301845910 z trzema wariantami CatBoost też SUCCESS. Poprzedni błąd uruchomienia #41301806538 dotyczył wyłącznie niewłaściwej konfiguracji pip cache, poprawiono bez uruchomienia modelu. Wnioski: drobna poprawa płytszego CatBoost względem CatBoost bazowego, ale M0 pozostaje lepszy na tych samych 300 meczach; żaden wariant nie jest promowany.

**Granica metodologiczna:** cechy 720 TRAIN są odtworzone chronologicznie z rzeczywiście wcześniejszych meczów, ale nie są certyfikowanym historycznym provider-first-published PIT; raport z 300 meczów dotyczy wewnętrznego treningowego CV, a nie niezależnego forward 8 lig.

## B. Przyrost rzeczywistych xG

Dotychczasowy kolektor 8 lig bez zmiany selektora, parametrów i limitu 33 zapytań został uruchomiony na main. [Run #41302170924 — SUCCESS](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/41302170924), 33 rzeczywiste wywołania PitchAPI, 8/8 nowych par shot/stats poprawnych, 0 błędów semantycznych tej rundy, **15 zweryfikowanych spotkań xG kumulatywnie** (poprzednio 7). Nowy raport źródłowy: [XG_READINESS_RECEIPT 2026-11-01](../data/pit_sidecar/step17_native_xg_eight/2026-11-01/XG_READINESS_RECEIPT.json), źródła zaszyfrowane i zachowane w archiwum.

Kompletne xG exact-last5 obu stron: **0 z 29 aktualnie skanowanych przyszłych spotkań**, mimo zwiększenia bazy. Zbiór 29 różni się od wcześniejszych 74 ze względu na aktualny horyzont; nie wolno przedstawiać zmiany mianownika jako poprawy. Nie ma xG CatBoost. Oryginalne 2023–25 PitchAPI provider-published UTC pozostaje nieudowodnione.

Równoległy niezależny dzienny kolektor [Step14 C run #41302103885 — SUCCESS](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/41302103885) zapisał 2 pary native shot/stats, 4 przyszłe cele, zaszyfrowane źródła, 6 zapytań. Nie sumujemy tych 2 par do liczby 15 bez kontroli duplikatów w tych różnych bazach. [Receipt Step14 C 2026-11-01](../data/pit_sidecar/step14_pitchapi_native/2026-11-01/KB3_PITCH_NATIVE_ASOF_RECEIPT.json).

Badawczy selektor PR [#125](https://github.com/karolbarankiewicz1984-ui/kb-score-3/pull/125) otrzymał dodatkowe bezpieczniki: dla budżetu zero zwraca zero wyborów, cel z zakończonym wynikiem lub poza 96h nie trafia do projekcji. [Testy offline #41302060282 — SUCCESS](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/41302060282), 0 provider calls. PR nadal DRAFT, bez aktywacji live, bo nie dowiedziono jeszcze rzeczywistej przewagi xG selection.

## C. Historyczne dane 8 lig — audyt rozbudowy zbioru

W PR #126 dodano niezależny auditor **scripts/step16_eight_league_history_inventory.py**, sprawdzający niezmienność źródła, kompletność sezonu historycznego i podejrzane dodatki do dwurundowej ligi. Z zapisanego manifestu M0 z 1 XI: **2606 pozycji zakończonych spotkań sezonu 2025/26**, w ośmiu ligach, 0 nowych zapytań API.

- NED: 309 pozycji dla 18 drużyn wobec 306 pozycji sezonu dwurundowego: **3 poza referencją**, wymagają niezależnej klasyfikacji po faktycznych fixture IDs.
- BEL: 313 pozycji dla 16 drużyn wobec 240 pozycji sezonu dwurundowego: **73 poza referencją** (możliwe fazy dodatkowe), wymagają klasyfikacji zgodnie z formułą ligi.
- Pozostałe sześć lig bez różnicy liczbowej względem podstawowej struktury, ale sama liczba meczów **nie dowodzi** poprawności wszystkich ID ani oryginalnego czasu publikacji.

[Offline Actions #41302401942 — SUCCESS](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/41302401942), 3/3 testy PASS, zero API, bez treningu i bez nadpisania źródeł. Nie włączamy historycznych NED/BEL do żadnego nowego wieloligowego treningu, dopóki nie ustalimy identyfikatorów i faz rozgrywek. Pierwsze uruchomienie #41302352797 padło na niepotrzebnym imporcie biblioteki szyfrowania, usunięto go; drugi run PASS.

## D. Decyzje i warunki dalszej nauki

1. **M0 pozostaje zamrożony**, bez zmian parametrów, bez dostrajania do 300 wewnętrznych testów i bez automatycznej kalibracji. Obecny formalny licznik FIT 38/100; 50 przyszłych HOLDOUT jeszcze się nie zaczęło. Dalsze prawdziwe probki prospektywne nadal zbierają istniejące workflow.
2. **CatBoost SHALLOW** zachować jako wersjonowaną hipotezę badawczą, nie zwycięzcę; przygotować ocenę na nowych wspólnych prospektywnych prognozach bez podglądania wyników.
3. **xG** dalej gromadzić jako osobny niezmienny zbiór, z wymaganiem dokładnie ostatnich pięciu faktycznych spotkań obu drużyn przed cutoff i zgodności semantycznej.
4. **Dane historyczne 8 lig:** najpierw per-fixture scope/phase ID NED/BEL oraz zgodność drużyn i cutoff; dopiero później szkoleniowe rozszerzenie kohorty. Nie deklarować formalnego provider PIT dla odtworzonych danych.
5. Zachować **GATE16 i GATE17 PENDING** do właściwych niezależnych porównań, a także 2026/27 Premier League TEST nigdy nietknięty. PR #126 i #125 badawcze niepołączone z main.

**Weryfikacja i zakres:** rzeczywiste źródła z GitHub Actions i utrwalone receipty. Nie dokonano pełnego osobnego audytu źródłowych 300 rekordów na poziomie każdej wartości, a raporty nie świadczą o przyszłej przewadze któregokolwiek silnika.
