# KB Score 3.0 — rejestr zleceń dla Codex R1–R5 / CatBoost / xG / M0
**Decyzja właściciela:** 2026-11-03, strefa Europe/Warsaw
**Stan:** PLAN / DO WYKONANIA PRZEZ CODEX; ten dokument nie jest dowodem wykonania ani wdrożenia żadnej poprawki.

## Zasady obowiązujące wszystkie cztery zadania
- Punkt wyjścia: aktualny prywatny GitHub `karolbarankiewicz1984-ui/kb-score-3`, aktualna gałąź `main`, `docs/PLAN.md`, `docs/ZMIANY.md`, realne raporty CI, archiwa i testy. Porównać stare gałęzie z `main` i uwzględnić już scalone PR #137–#142. Nie przywracać starszej implementacji nad nowszą.
- Każdy task ma osobną gałąź, diff, raport, testy i PR. **Nie scalać automatycznie**, nie podnosić GATE16/17 ani licznika 15/29 na podstawie samego PR lub testów jednostkowych.
- Ochrona: bez zmiany zatwierdzonych parametrów M0, historii zamrożonych prognoz, prawdziwych źródeł immutable SQLite, kryterium **100 kwalifikujących FIT + 50 nowych po FIT HOLDOUT**, modelu Champion i chronionego Premier League 2026/27 TEST. Nie wymyślać pierwszych dat publikacji historycznych cech. Nie ujawniać sekretów i nie kupować API.
- Odbiór minimum: zero przecieków, integralność identyfikatorów meczów i drużyn, brak podstawiania 0 za NULL, spójne timestamp UTC, brak modyfikacji raw evidence, offline regression CI; live tylko z kontrolowanym przyzwoleniem. Poprawki na `main` wymagają odrębnej oceny i decyzji.
- Każdy task dopisuje historię decyzji i jej stan do `docs/ZMIANY.md` **na gałęzi PR**. Raport: PASS/PARTIAL/NO-GO, kryteria jakości, aktualne blokery, lista testów, liczba rzeczywistych rekordów i dalsze kroki. Bez deklarowania wykonania bez dowodów.
- Jeśli brakuje źródłowej paczki Codex lub testów, wskazać to jawnie. Nie odtwarzać paczki w oparciu o domysły.

## CODEX-01 — krytyczne R1–R5 / PR #124 — najpierw
**Priorytet:** P1. **Status wejściowy:** dokumentacyjny draft PR [#124](https://github.com/karolbarankiewicz1984-ui/kb-score-3/pull/124), **NO-GO** do merge (nie jest gotową poprawką kodu).

**Zakres techniczny:**
1. Porównać autentyczne R1–R5 z aktualnym `main`; sklasyfikować ustalenia jako naprawione, nadal otwarte, niedostępny dowód. Nie scalać ślepo historycznej paczki 57 plików, sprawdzić SHA i rzeczywisty diff, zależności z obecnym kolektorem.
2. **FIND-01 / `total_shots`:** zbadać wymagalność i typ danych, prawdziwe 0 vs brak, niekompletne/sprzeczne źródła, testy każdej gałęzi walidacji.
3. **FIND-02 / atomowość `shots + stats`:** matching natywnych identyfikatorów meczu i stron, identyczna definicja okresu, walidacja obu źródeł przed zatwierdzeniem dowodu, transakcja/rollback bez połowicznego PASS, kontrola ponownych uruchomień.
4. Inne potwierdzone błędy P1/P2: weryfikacja spójności cech TRAIN vs forecast, źródła xG, zapis SQLite Actions, migracja **wyłącznie kopii** baz.
5. Uruchomić istniejące testy i nową regresję; zestawy 197/108 (w starym PR) mogą się pokrywać — raportować faktyczne unikalne testy. Brak prawdziwych testów = NO-GO.

**Brama odbioru:** wszystkie potwierdzone P1 naprawione lub wyraźnie wstrzymane z uzasadnieniem; PASS spójności źródła, brak zmian M0, brak nadpisania immutable, CI SUCCESS; osobny PR. **Nie scalać bez niezależnej oceny.**

## CODEX-02 — CatBoost TRAIN-only i porównanie / PR #126 — po kontroli CODEX-01
**Priorytet:** P1. **Status wejściowy:** draft badawczy [#126](https://github.com/karolbarankiewicz1984-ui/kb-score-3/pull/126), bez automatycznego merge. Przed rozpoczęciem uwzględnić już wykonany [pilot xG5 PR #141](../data/audits/step17_xg5_ablation/STEP17_XG5_ABLATION_41691844430_1.json), 102 TRAIN / 44 VAL na tych samych meczach, bez poprawy Brier/log loss po dodaniu xG5, z ograniczeniem BEL/ESP i zaledwie 5 tygodniami VAL.
  
**Trzy warianty badawcze:** A = CatBoost bez xG (Elo, forma i dostępne cechy przedmeczowe), B = A + prawdziwe xG5/xGA5 z rzeczywistych poprzedników, C = A+B + opcjonalne xG10/xG15, strzały, kartki, rożne, faule. Każdy brak = jawne NULL/NaN, nie zero. Nie używać xG w modelu A.
  
**Metodyka:** wyłącznie TRAIN chronologiczny, predefiniowane foldy walk-forward, identyczne mecze/etykiety walidacyjne, hiperparametry/cechy ustalane wyłącznie w TRAIN, zachowane pierwsze daty obserwacji, źródła PIT certyfikowane odrębnie od retrospectively reconstructed. Porównanie M0 vs CatBoost możliwe dopiero na **tych samych** meczach (stare 374 z inną ligą ≠ bieżące 44). Liczyć Brier sum3, log loss, accuracy, ECE/kalibrację per liga, tygodniowe niepewności i odsetek braków; wyniki mogą być nierozstrzygające, gdy liczebność/niezależność za mała.

**Brama odbioru:** bez przecieku do TRAIN i bez chronionego TEST; czytelne i reprodukowalne wyniki porównań A/B/C, osobno od produkcyjnego M0, źródłowe SHA i raport. Nie zatwierdzać GATE17 ani Championa na pilocie.

## CODEX-03 — selekcja danych PitchAPI / PR #125 — równolegle, po kontroli kolizji z PR #142
**Priorytet:** P2. **Status wejściowy:** draft [#125](https://github.com/karolbarankiewicz1984-ui/kb-score-3/pull/125), wciąż niezintegrowany ze strumieniem live. Obecny kod **już ma** 5×48 meczów na workflow, `priority_predecessor_matches` i `underserved_national_scope` z [PR #142](https://github.com/karolbarankiewicz1984-ui/kb-score-3/pull/142). Nie podmieniać ich starszym ograniczeniem 33 requestów dla innego eksperymentalnego collectora.

**Zakres:** przebadać prawdziwe ostatnie 5/10/15 (w poprzednich sezonach i z podziałem dom/wyjazd), ranking zapytań według przyrostu **kompletnych par obu drużyn**, pokrycie 8 lig, niedoreprezentowane ITA/NED/TUR/GER/POL/FRA, koszt zapytań i duplikatów. Porównać aktualny selektor z kandydatami na dokładnie tej samej liście dostępnych spotkań: liczba pełnych xG5/10/15 na każde 100 pobrań, liczba nowych nieprawidłowych xG, liczba rzeczywistych opóźnień, rozkład lig. Wykluczyć ENG TEST i UCL bez niezależnego mapowania.
  
**Brama odbioru:** pozytywna korzyść netto przy niezmienionym standardzie dowodu, prawdziwe SHA i status source-first-published, CI offline i kontrolowany live w oddzielnym PR; w razie braku poprawy pozostawić obecną metodę. Bez fikcyjnych wartości i bez zmian modeli.

## CODEX-04 — audyt freeze / rozliczeń M0 / PR #131 — równolegle
**Priorytet:** P1/P2. **Status wejściowy:** częściowy draft [#131](https://github.com/karolbarankiewicz1984-ui/kb-score-3/pull/131), nie jest pełnym rolloutem. Ostatni **potwierdzony** punkt odniesienia to 91 zamrożonych prognoz, 74 kwalifikujące rozliczenia, 26 brakujących do FIT100; liczby trzeba **ponownie odczytać w chwili pracy** z latest Actions, nie zakładać że nie zmieniły się.

**Zakres:** audyt rzeczywistego harmonogramu, limitów na run, duplikatów, weryfikacji cutoff przed kickoff, wyjątków provider, opóźnionych settlement, klasyfikacja odrzuceń i retry. Poprawić jedynie potwierdzone pominięcia, aby uzyskać więcej **nowych autentycznie przedmeczowych** próbek bez zwiększania przecieku. Wykluczyć produkowanie forecastów po kickoff lub retrospektywne dopisywanie predykcji jako zamrożonych. Chronić idempotency i zliczać tylko kwalifikujące.
  
**Brama odbioru:** wykaz realnych przyczyn utraty próbek, testy harmonogramu/timezone, cutoff, retry, idempotency, read-only audyt skutków i osobny PR. Formalna kalibracja dopiero po faktycznym FIT100 i *nowych*, nieużytych do dopasowania 50 HOLDOUT.

## Kolejność i odpowiedzialność
- **Najpierw:** CODEX-01, niezależny odbiór poprawek integralności; **następnie:** CODEX-02.
- **Równolegle, osobne gałęzie:** CODEX-03 i CODEX-04; przed ewentualnym scaleniem obowiązkowy rebase i ponowne CI względem bieżącego main.
- **Rola Codex:** kod + testy + raport + PR. **Rola właściciela/ChatGPT:** audyt dowodów, decyzja o merge, metodologia, aktualizacja rejestru odbioru.
- **Stan harmonogramu 29 kroków:** formalnie 15/29, GATE16/17 PENDING; wydanie niniejszego zlecenia nie zmienia stanów i nie jest nowym treningiem ani pobraniem.
