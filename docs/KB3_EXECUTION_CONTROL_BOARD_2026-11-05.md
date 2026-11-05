# KB Score 3.0 — wspólny audyt 29 etapów i planu TEST 12 kroków (05.11.2026)

**Zakres:** stan oryginalnego rejestru docs/ZMIANY.md i oryginalnych dowodów GitHub do 05.11.2026, ok. 15:00 UTC. Nie oznacza dopuszczenia starego CatBoost, FIT ani produkcji.

## A. P1-01: TRAIN kontra FORWARD — rzeczywista diagnoza

- Pierwotny CatBoost M1-R o 85 cechach korzystał w rekonstrukcji TRAIN z warunku poprzedni kickoff+48h, natomiast rzeczywiste źródła forward z faktycznego momentu obserwacji i minimalnego opóźnienia +3h. Także days_since_last_kickoff odnosił się do innych punktów czasu (kickoff celu wobec capture cutoff). Zgodność nazw lub liczby 85 kolumn NIE dowodzi tożsamości wejść. PR #149 ogranicza nieuprawniony awans, ale nie zmienia oryginalnego modelu.
- Wspólny kod v2 z PR #151 został scalony do main: src/kb3_p1_shared_asof_features_v2.py używa tej samej agregacji Step11 dla TRAIN i FORWARD, przy identycznych rzeczywistych źródłach, ich zegarach i cutoff. compare_same_asof sprawdza wektor, braki, lineage i SHA. CI #41911645305 zweryfikował 17 testów v2 i 21 regresji Step11 na Python 3.11 i 3.12. Nowe offline CI na gałęzi TEST powtarza ten zestaw.
- Dotychczasowa historyczna baza PitchAPI nie ma niezależnych znaczników pierwotnej publikacji i oryginalnych prematch snapshots dla przeszłych spotkań. Historyczne CERTIFIED_ASOF_V2 TRAIN=0, VALIDATION=0; aktualne rekonstrukcje last5, Core5 i xG5 są wyłącznie research, nawet przy wzroście kompletnych rekordów.
- Baza bieżąca zawiera 149 M0 z host proof, 23 Shadow z host proof. To prawdziwe zamrożenia źródłowe, ale w pojedynczym wierszu M0 pozostają skróty cech i wybrane lambdy, a nie pełen certyfikowany 85-feature historyczny TRAIN starych wag M1-R. Shadow Six to odrębny model sześciu cech.
- **Decyzja:** P1-01 PARTIAL, legacy M1-R PROMOTION NO-GO, P1-02 legacy FIT BLOCKED, wspólna semantyka algorytmu v2 CODE-LEVEL PASS, historyczny PIT 0. Nie rozpoczynać ponownego użycia starego 85-feature CBM bez nowego treningu i rzeczywistych dowodów.

**Do domknięcia P1:** zebrać prawdziwe bajty i źródłowe zegary pełnego 121+38 dla tych samych przedmeczowych meczów, odtworzyć identyczne wejścia TRAIN/FORWARD przy tym samym cutoff, porównać wartości/NULL/missing i lineage, po czym dopiero trenować nowy, odrębnie wersjonowany CBM. Nie wolno podmieniać dawnej historii za poprawne PIT przez heurystykę +48h.

## B. Oddzielny generator podglądu KB3 TEST: nowy kod

W nowym PR na gałęzi badawczej powstały:
- src/kb3_test_readonly_markets.py
- scripts/kb3_test_readonly_market_preview.py
- tests/test_kb3_test_readonly_markets.py
- .github/workflows/kb3-test-readonly-market-ci.yml

Funkcje wykorzystują istniejącą i przetestowaną matematykę src/kb3_step15_goal_markets.py, a NIE nowy model. Z oryginalnie zamrożonych lambda M0 obliczają 1/X/2, 1X/X2/12, O/U 1.5, 2.5, 3.5, BTTS oraz team-goals. Sprawdzają niezależnie, czy 1X2, p_over i BTTS idealnie zgadzają się z tymi, które zapisano przy pierwotnym M0 (tolerancja 2e-10). Rozbieżność = blokada.

Oryginalna SQLite otwierana tylko mode=ro/query_only. Wymagany realny wiersz host proof w tej bazie, SHA zamrożonego M0, identyfikator i wersja M0, źródłowe lineage i termin przed kickoff−90min. Brak proof, zmiana starego payload lub mecz z przeszłości = brak podglądu. Nie ma provider calls, nowych kursów ani nowych prognoz; nie są dopisywane nowe rekordy rynków do SQLite. Wynik research-only i NIE jest oddzielnym oryginalnym freeze rynku, zatem nie wolno go traktować jako zatwierdzonego testu zakładów, nowego FIT lub GATE TEST PASS.

**Kolejne wymagania TEST:** samodzielny, autentyczny przedmeczowy market+line+P+SHA/cutoff freeze oraz wynik rynkowy po meczu (WIN/LOSS/PUSH/VOID), potem dopiero generator trzech PDF.

## C. Matryca postępu — 12 kroków względem oryginalnych 29

| Plan wykonawczy | Stan rzeczywisty | Powiązany etap 29 | Warunek następnego odbioru |
|---|---|---|---|
| 01 backup i restore | OPERATIONAL_GO, offsite decrypt/restore nieudowodniony | 08,21 | Zachować odtwarzalne kopie, bez proszenia o prywatny RSA |
| 02 PR #146/#148 | Main MERGED, realne 23 M0/Shadow poświadczone | 16,24 | Monitorować skuteczność przyrostu, retry, brak dubli i koszty |
| 03 PR #143/#149 i wspólne as-of v2 | P1 PARTIAL, stary model 85 niezgodny, historyczny PIT 0 | 16,17 | Rzeczywisty TRAIN/FORWARD identyczne źródła + cutoff |
| 04 audyt M0 live | 149/149 M0 host proof, 23/23 Shadow proof, 75 raw settlements | 16,17 | Rozliczyć te same 23 po 08.11 i sprawdzić paired scoring |
| 05 generator TEST | Kod badawczego odczytu rynków w nowym PR, nie odebrany GATE | 15,20,23 | CI, następnie niezależny market freeze |
| 06 rynki i rozliczenia | M0 1X2 działa, pełne TEST O/U, BTTS itd. nieodebrane | 21,22 | Zapis market+line i scenariusze VOID/PUSH |
| 07 trzy PDF | PENDING | 23–25 | Trzy prawdziwe czytelne PDF z audytem |
| 08 selektor historii #145 | Nowy gain-first #162 MERGED, #145 DRAFT | 11,17 | ΔCore5 i ΔCore5∩xG5 w każdej lidze |
| 09 CatBoost #144 | #144 DRAFT, #161 research nie wykazał przewagi xG; 23 live pary oczekują na wynik | 17,18 | Sparowany Brier/log loss + niepewność |
| 10 kalibracja | Ostatni kwalifikowany FIT 74/100, 75 raw settlement nie równa się 75 FIT; HOLDOUT 0/50 | 16 | 100 prawdziwych FIT, pierwszy fit, później 50 nowych HOLDOUT |
| 11 kartki, rożne, faule | PENDING | 28 | Dla każdej rodziny statystyki, definicje i osobny TEST |
| 12 monitoring | Watchdog M0 wykonany, alerty progów/drift i dostawa nieodebrane | 24–27 | Kontrola fałszywych dispatch i test alertów |

**Oryginalna mapa:** 01–15 zaliczone; 16 i 17 IN_PROGRESS/GATE PENDING; 18–29 formalnie nieodebrane pomimo wcześniejszych prototypów, read-only rozliczeń, a także badań kroku 19.

## D. Dane bieżące i nieprzekraczalne granice

- Oryginalny ZIP #42037486832: 2001→2241 obserwacji; 1774→1986 źródłowo zgodnych xG. Dla identycznego historycznego podzbioru krajowych ośmiu lig 2023–2025: Core5=1225 (+249), xG5=464 (+87), wspólny Core5+xG5=372 (+92). Liczby 1228/466 dotyczą nieco szerszej populacji — nie mieszać z nimi wyników eksperymentów.
- NED/POL: Core5+xG5 odpowiednio 4 i 9; 30 kandydatów do uzupełnienia historycznych żółtych kart wybranych, ale legalne źródło wtórne i ścisły crosswalk = 0; odzyskane kartki 0. Bez nieautoryzowanego importu lub zakupów.
- W M0: 23 prawdziwe pary na mecze 08.11, 0/23 sparowanych rozliczeń; nie generować retro.
- Bez zmian oryginalnego M0, Shadow Six, chronionego ENG TEST, immutable forecasts, parametrów, harmonogramu oraz FIT100+50. Żadnego automatycznego Champion i żadnej nowej subskrypcji.

## E. Przyjęta dalsza kolejność

1. Uruchomić i odebrać CI nowego read-only TEST i testów P1-01.
2. Przygotować w izolacji autentyczne nowe market-freeze + indywidualne rozliczanie rynków.
3. Nadal mierzyć prawdziwy przyrost Core5 i wspólnego xG5 na istniejącym kolektorze; nie zwiększać bezrefleksyjnie API.
4. Po rzeczywistym 08.11 rozliczyć 23 pary na identycznych meczach.
5. Dopiero po FIT100 oraz kolejnych 50 rzeczywistych HOLDOUT rozważyć GATE16/GATE17 i formalnego Championa.

Stan kodu TEST jest oddzielony od main do czasu prawdziwego CI, nie należy opisywać go jako wdrożenia produkcyjnego.


## F. Zakończony odbiór badań TEST — 05.11.2026, 16:15 UTC

- **Kontrolowany merge po prawdziwym CI:** [PR #164](https://github.com/karolbarankiewicz1984-ui/kb-score-3/pull/164) został scalony do main metodą squash. Merge commit: f5cacaea0ecfe1efc7d644a9a87825467fea0767. To jest przyjęcie odizolowanego narzędzia badawczego, a nie nowego modelu produkcyjnego ani pełnego kroku 05 TEST.
- **Najnowszy dokładny HEAD kodu:** bf24456448fc5125c5903c813f819dd721b5d2dd. [CI #42061889570](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/42061889570) completed/SUCCESS; 7 testów nowej nakładki, 12 regresji Step15 i 17 testów wspólnego as-of v2 = **36/36 PASS**, plus prawdziwy read-only audyt istniejącej SQLite oraz kontrola git diff. Ponowiona kopia CI #42061879876 także SUCCESS.
- **Pierwszy niezmieniony oryginalny materiał źródłowy:** w CI odczytano istniejącą ośmioligową SQLite i **74 nierozliczone przedmeczowe forecasty M0**, bez żadnego nowego generowania prognozy i bez zapisów w bazie. As-of rzeczywiście wykonanego artefaktu: 2026-11-05T16:11:06.003513Z; 74 unikalne SHA oryginalnych M0, osiem lig, kickoff od 2026-11-06T17:00:00Z do 2026-11-08T20:00:00Z. To jest podgląd z istniejących forecastów; w 74 nie jest ukryty żaden nowy FIT.
- **Rzeczywisty opublikowany artefakt GitHub:** 13432377358, nazwa KB3_TEST_READONLY_DERIVED_MARKETS_NOT_NEW_FORECAST, utworzony na serwerze 2026-11-05T16:11:07Z, oryginalny ZIP 32055 bajtów, SHA256 0689f580b35621865ac71b512ae53cd090a7f1881c4e538355f801d842ef7cc8. Pobrano autentyczny ZIP, potwierdzono SHA względem GitHub API, CRC i plik DERIVED_RESEARCH_ONLY.json: 191385 bajtów, SHA256 045c77ddf99899111081d8c071e7004d17cfaee7ccc8c3161611c3af1aa2c200; 74/74 poprawne komplementy O/U i kombinacje podwójnej szansy. Oryginalna baza nie została nadpisana.
- **Granice odbioru:** oryginalne rodzicielskie host proofs pochodzą z wcześniej zachowanych rekordów bazy; nowy odczyt nie reattestował niezależnie oryginalnych bajtów archiwów forecast. **Nie powstał nowy odrębny market+line freeze**, mimo że pochodne są odtwarzalne; brak nowych rozliczeń O/U, BTTS i team-goals. P1-01 historyczny PIT nadal 0, stare M1-R 85 NO-GO, FIT100 + 50 późniejszych HOLDOUT bez zmian, GATE16/GATE17=PENDING, liczba formalnie przyjętych etapów **15/29**. Następny krok: niezależny nowy append-only market freeze wraz z wynikowym settlement na właściwych rynkach, dopiero później trzy PDF.

## G. Kontynuacja 05.11 — LIVE market freeze i settlement readiness

- Wdrożono na main [PR #165](https://github.com/karolbarankiewicz1984-ui/kb-score-3/pull/165) oraz techniczną poprawkę GitHub CDN [PR #166](https://github.com/karolbarankiewicz1984-ui/kb-score-3/pull/166). Obydwa MERGED. Odizolowany plikowy append-only ledger **nie modyfikuje** oryginalnej M0 SQLite, źródła historii ani ustawień Shadow.
- **Zadanie TEST 05 — częściowo wykonane:** rzeczywiste 74 autentyczne, przedmeczowe, niezależnie poświadczone migawki rynków, razem 2072 wyborów. 28 na jeden fixture nie stanowi 28 niezależnych próbek kalibracyjnych. [Run LIVE #42071340249](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/42071340249) SUCCESS i [persist commit dfff112a](https://github.com/karolbarankiewicz1984-ui/kb-score-3/commit/dfff112a042e47cd71a7e9eb7b966e16386778f7), host artifact 13435597051, SHA256 ZIP c9aeb5d9d35ffa5bbe24b4b0f880b9ebdd1c77a9a9863ac3618163ff377bbab6, host stworzył go 05.11.2026 17:07:02Z. Nie ma nowych płatnych API.
- **Zadanie TEST 06 — przygotowano kod, realny settlement 0/74, PENDING:** mechanizm działa z prawdziwym immutable wynikiem M0 dopiero po kickoff+3h; obsługuje win/loss, całkowity 2.0 push, a VOID tylko z niezależnie potwierdzonym zdarzeniem — brak wyniku nie powoduje automatycznego VOID. Brier i log loss obliczane osobno dla konkretnych linii i wyborów. Niezbędne przyszłe prawdziwe obserwacje i niezależny audyt utworzonych plików wynikowych.
- **Zadanie TEST 07 (trzy PDF) — PENDING.** Nie generować raportu sugerującego rozliczone sukcesy z przyszłych meczów.
- **Zadanie P1-01 — nadal PARTIAL.** Oddzielny rynek TEST nie dowodzi historycznych oryginalnych timestamps dla starego 85-cechowego M1-R; brak jego promocji.
- **Formalny plan bez zmiany:** 15/29, GATE16/GATE17 PENDING, 100 autentycznych FIT + 50 nowych po pierwszym kalibracyjnym dopasowaniu. Dalszy etap: zweryfikować pierwsze rzeczywiste `data/test_markets/settlements/` po zakończonych fixture, następnie podłączyć do generatora trzech czytelnych PDF.
