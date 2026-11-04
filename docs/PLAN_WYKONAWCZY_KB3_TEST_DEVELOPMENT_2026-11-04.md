# KB Score 3.0 — plan wykonawczy TEST + DEVELOPMENT (12 kroków)

**Decyzja właściciela:** 2026-11-04. **Status:** zatwierdzony plan, wykonanie etapami. To uszczegółowienie istniejących 29 kroków, a nie zmiana ich bramek ani dowód automatycznego ukończenia.

**Wersja zasad:** oryginalny model M0, immutable archiwa, 73 dawne prognozy i nowsze zamrożenia, chroniony ENG Premier League 2026/27 TEST, brak wycieków, dopuszczenie treningu tylko na zaakceptowanych źródłach. GATE16 i GATE17 nadal PENDING; 15/29 formalnych etapów PASS. Kalibracja wymaga 100 rzeczywistych kwalifikujących FIT tej samej wersji, następnie 50 **nowych po pierwszym FIT** HOLDOUT. Żadne próby nie mogą być sfabrykowane po kickoffie. Brak automatycznego awansu Championa, płatnego zakupu API lub nowej wersji produkcyjnej.

**Sekwencja:** 01 → (02 i 03 równolegle; przygotowania offline 05, 08, 09 możliwe) → 04 → 05 → 06 → 07; następnie 08–12, przy czym 10 zależy od rzeczywistego osiągnięcia progu. Zmiana źródeł #145 wymaga zamknięcia blokad #143. Każde wykonanie wpisujemy w `docs/ZMIANY.md` wraz z SHA, testem, PASS/PARTIAL/NO-GO, kryteriami i kolejnym krokiem.

## Rejestr realizacji

| Nr | Etap | Dlaczego | Warunek odbioru | Status początkowy |
|---|---|---|---|---|
| 01 | Zabezpieczenie i odtwarzalność | Bez odtwarzalnego stanu wyjściowego nie można bezpiecznie wdrażać kolejnych modyfikacji. | Backup odtwarza dane bez modyfikacji produkcyjnych źródeł. | START 2026-11-04 — przegląd źródeł |
| 02 | Odbiór i ograniczony pilotaż PR #146 | Wcześniejsze dzienne ograniczenie może zmniejszać tempo zbierania próbek potrzebnych do FIT100. | Bezpieczny nowy freeze przed kickoff-90 min; brak dubli i nieuprawnionych kosztów. | PENDING — zależy od 01 |
| 03 | Naprawa krytycznych P1 w PR #143 | Różnice cech i niepoświadczone publikacje mogą fałszować uczenie i skuteczność. | P1-01 i P1-02 zamknięte testami, realne źródła poprawne, brak lookahead. | PENDING — praca równoległa |
| 04 | Rzeczywisty audyt pilota M0 | Regresja offline nie dowodzi faktycznego wzrostu liczby prognoz. | Niezależnie potwierdzony przyrost kwalifikujących FIT lub jawny raport braku. | PENDING — zależy od 02 |
| 05 | Generator KB Score 3.0 TEST | Gotowe matematycznie rynki goli można testować wcześniej niż pełne nowe rodziny rynków. | Spójność P, identyczne źródła i parametry M0; zero zmyślonych danych. | PENDING — można przygotować offline obok 02–04 |
| 06 | Freeze i settlement każdego rynku TEST | Oddzielne rynki potrzebują oddzielnej oceny i niezmiennego dowodu prognozy. | Każdy rynek rozliczany oddzielnie bez zmiany forecastu. | PENDING — zależy od 05 |
| 07 | Trzy raporty TEST | Użytkownik powinien widzieć realne wyniki pracy zanim zakończą się wszystkie 29 formalnych kroków. | 3 prawdziwe pliki PDF otwierają się, daty PL poprawne. | PENDING — zależy od 05–06 |
| 08 | Badawcze ulepszenie historii PR #145 | Obecny historyczny selektor nie zawsze domyka pełne xG5/10/15 efektywnie. | Wykazany uzysk vs current bez gorszej jakości i bez chronionego TEST. | PENDING — zależy od 03 |
| 09 | Porównanie CatBoost A/B/C PR #144 | Nowy algorytm nie ma potwierdzonej przewagi, wymagane porównania bez przecieku. | Rzetelne Brier/logloss/ECE i niepewność, brak automatycznej promocji. | PENDING — odseparowany eksperyment |
| 10 | Formalna kalibracja GATE16 | Sam trafiony wynik nie mówi, czy deklarowane prawdopodobieństwo jest dobrze skalibrowane. | Rozłączne snapshoty i raport przed/po, formalny odbiór. | PENDING — 74/100 FIT na ostatnim dowodzie, HOLDOUT 0/50 |
| 11 | Modele kartki, rożne, faule | Faule, kartki i rożne mają odrębne definicje i rozkłady niż gole. | Model porównany na realnych parach, zaakceptowany lub odrzucony. | PENDING — niezależne po audycie źródeł |
| 12 | Monitoring progów i Champion–Challenger | System ma sam informować o osiągnięciu progów, bez samowolnej zmiany modelu. | Test alarmów i powiadomień, log decyzji oraz rollback. | PENDING — monitoring można przygotować wcześniej |

### Krok 01 — Zabezpieczenie i odtwarzalność

**Zakres:** Zweryfikować najnowsze manifesty SHA, encrypted sidecar/backup, kopie SQLite, parametry M0, archiwum zamrożeń, recovery. Odtworzenie prawdziwej kopii testowej w izolacji wymagane do zaliczenia.

**Odbiór:** Backup odtwarza dane bez modyfikacji produkcyjnych źródeł.

**Stan wejściowy:** START 2026-11-04 — przegląd źródeł.

### Krok 02 — Odbiór i ograniczony pilotaż PR #146

**Zakres:** Po kroku 01: przegląd diffu, rebase, CI, request budget, idempotencja i host proof; osobne zatwierdzenie merge; jeden live run z miernikami.

**Odbiór:** Bezpieczny nowy freeze przed kickoff-90 min; brak dubli i nieuprawnionych kosztów.

**Stan wejściowy:** PENDING — zależy od 01.

### Krok 03 — Naprawa krytycznych P1 w PR #143

**Zakres:** Równolegle do 02: wersjonowanie TRAIN/forward i walidacja historycznych dowodów FIT, kwarantanna legacy, bez zmian M0/TEST.

**Odbiór:** P1-01 i P1-02 zamknięte testami, realne źródła poprawne, brak lookahead.

**Stan wejściowy:** PENDING — praca równoległa.

### Krok 04 — Rzeczywisty audyt pilota M0

**Zakres:** Liczby nowych freeze, przyczyny pominięć, rozliczenia, cutoff, koszty, SHA, odzyskiwanie po awariach.

**Odbiór:** Niezależnie potwierdzony przyrost kwalifikujących FIT lub jawny raport braku.

**Stan wejściowy:** PENDING — zależy od 02.

### Krok 05 — Generator KB Score 3.0 TEST

**Zakres:** Rynki 1X2/1X/X2/OU gole/BTTS/team totals, jeden rozkład M0, tylko realne źródła i model_version, status RESEARCH.

**Odbiór:** Spójność P, identyczne źródła i parametry M0; zero zmyślonych danych.

**Stan wejściowy:** PENDING — można przygotować offline obok 02–04.

### Krok 06 — Freeze i settlement każdego rynku TEST

**Zakres:** Immutable market+line+P+timestamp+source SHA, po meczu wynik danego rynku, PUSH/VOID.

**Odbiór:** Każdy rynek rozliczany oddzielnie bez zmiany forecastu.

**Stan wejściowy:** PENDING — zależy od 05.

### Krok 07 — Trzy raporty TEST

**Zakres:** Dziś/jutro/pojutrze, czytelne PDF, jawne luki i bez wymyślonych kursów, wysyłka po testach.

**Odbiór:** 3 prawdziwe pliki PDF otwierają się, daty PL poprawne.

**Stan wejściowy:** PENDING — zależy od 05–06.

### Krok 08 — Badawcze ulepszenie historii PR #145

**Zakres:** Po źródłowym odbiorze #143: rebase na aktualne dane, nowy plan, A/B live z licznikiem requestów i xG5/10/15.

**Odbiór:** Wykazany uzysk vs current bez gorszej jakości i bez chronionego TEST.

**Stan wejściowy:** PENDING — zależy od 03.

### Krok 09 — Porównanie CatBoost A/B/C PR #144

**Zakres:** Zachować badawczy challenger, nowe niezależne okresy i te same fixture co M0, bez tuning na VAL/TEST.

**Odbiór:** Rzetelne Brier/logloss/ECE i niepewność, brak automatycznej promocji.

**Stan wejściowy:** PENDING — odseparowany eksperyment.

### Krok 10 — Formalna kalibracja GATE16

**Zakres:** 100 kwalifikujących rzeczywistych FIT tej samej wersji; po dopasowaniu nowe 50 HOLDOUT; nie mieszać wersji.

**Odbiór:** Rozłączne snapshoty i raport przed/po, formalny odbiór.

**Stan wejściowy:** PENDING — 74/100 FIT na ostatnim dowodzie, HOLDOUT 0/50.

### Krok 11 — Modele kartki, rożne, faule

**Zakres:** Każdy rynek: odrębne feature/label, freeze, walidacja, settlement; zero automatycznej zmiany M0.

**Odbiór:** Model porównany na realnych parach, zaakceptowany lub odrzucony.

**Stan wejściowy:** PENDING — niezależne po audycie źródeł.

### Krok 12 — Monitoring progów i Champion–Challenger

**Zakres:** Automatyczne alerty FIT100, HOLDOUT50, źródła i dryf; raport skuteczności; ręczna decyzja Champion.

**Odbiór:** Test alarmów i powiadomień, log decyzji oraz rollback.

**Stan wejściowy:** PENDING — monitoring można przygotować wcześniej.

## Kontrola po niezależnym audycie 4 PR

- [Audyt #143–146](AUDIT_PR_143_146_2026-11-04.md): #143 pełne NO-GO, #144 badawczy, #145 i #146 warunkowo po kontroli i pilocie.
- Żadnego automatycznego merge czterech PR. Plan właściciela „zacznij wykonywać” uruchamia analizy i przygotowania, nie uchyla bramek przed modyfikacją istniejącego M0.
- Przy audycie kroku 01, jeśli nie ma dostępu do oryginalnych kluczy lub nie można odszyfrować źródeł z poziomu konektora, zapisać uczciwie **PARTIAL / RESTORE_NOT_VERIFIED** zamiast deklarować PASS.

## Decyzja 04.11.2026 — krok 01 bez obsługi prywatnego klucza

**Dyspozycja właściciela:** „Omiń kwestie korzystania z prywatnych kluczy jeśli to możliwe”.

- **Krok 01 — gotowość OPERACYJNA do kontynuacji:** PASS dla byte-for-byte copy i niezależnego SQLite `backup()`/restore na odrębnej kopii, row/table SHA, `integrity_check`, `foreign_key_check` oraz immutable triggers. Dowody: [raport kroku 01](STEP01_M0_BACKUP_RESTORE_2026-11-04.md), [CI 41853754238](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/41853754238). Jest to wystarczające, aby **przygotowywać krok 02 i 03**, bez oczekiwania na obsługę klucza prywatnego.
- **Pełna odtwarzalność kopii OFFSITE:** nadal `NOT_VERIFIED`. Google Drive zawiera przesłaną zaszyfrowaną paczkę, z potwierdzonym SHA/CRC, ale nie odszyfrowano jej ani nie wykonano końcowego restore. Taka paczka **bez dostępnego klucza prywatnego nie jest praktycznie odtwarzalną kopią**, dlatego NIE traktować jej jako jedynego zabezpieczenia ani dowodu disaster recovery. Zachować historię i ryzyko.
- **Nie wymagać od użytkownika przesyłania, importowania czy udostępniania klucza prywatnego w ChatGPT, GitHub lub Codex**. Nie zmieniać obecnego szyfrowania, nie publikować wrażliwych danych ani nie przechodzić na jawny backup w chmurze bez osobnego zatwierdzenia użytkownika.
- **Możliwa przyszła alternatywa:** usługa zarządzanego przechowywania prywatnych kopii, z szyfrowaniem po stronie usługi i dostępem za pomocą konta (bez ręcznej obsługi własnego klucza), dopiero po audycie uprawnień, retencji i wyraźnej decyzji. To nie jest bieżące wdrożenie.
- **Status:** `STEP01_OPERATIONAL_GO / OFFSITE_DECRYPT_RESTORE_NOT_VERIFIED`; nie oznacza formalnego pełnego `OFFSITE_RESTORE_PASS`. Dalej #146 i #143 według pozostałych bramek oraz 15/29, GATE16/17 PENDING.
