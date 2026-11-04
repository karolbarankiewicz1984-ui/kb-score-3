# KB Score 3.0 — plan wykonawczy 12 kroków: TEST + DEVELOPMENT
**Decyzja właściciela:** 2026-11-04, Europe/Warsaw. **Status dokumentu:** ZATWIERDZONY PLAN; wykonanie według osobnych dowodów. 
**Powiązanie:** [29 formalnych etapów](PLAN.md), [rejestr zmian](ZMIANY.md), [audyt PR #143–146](AUDIT_PR_143_146_2026-11-04.md). Ten plan **nie zmienia** statusu GATE16/GATE17 ani formalnego 15/29.

## Zasady wykonania
- Najpierw kroki **1 → (2 || 3) → 4 → 5 → 6 → 7**. Gdy nie tworzy to zależności krytycznej, przygotowywać równolegle 8 i 9 offline, potem 10, 11, 12. Każdy krok ma status, dowód, warunek odbioru i zapis do `docs/ZMIANY.md`.
- Odrębne poziomy: **CODEX/DRAFT** (kod lub badanie), **TEST/SHADOW** (prawdziwe prognozy bez produkcyjnych roszczeń), **CHAMPION** (osobno zatwierdzony). Nie nazywać testowego modelu produkcyjnym.
- Wymaga realnego przedmeczowego `freeze` i niezależnego dowodu publikacji host GitHub; brak dowodu to brak kwalifikacji do FIT. Nie dopisywać wyników po kickoff jako prematch. Nie przepisujemy oryginalnych forecastów, wyników, `data/`, `models/`, parametrów M0 i chronionego ENG Premier League 2026/27 TEST.
- **GATE16:** co najmniej 100 właściwych rozliczonych, uwierzytelnionych FIT tej samej wersji oraz **50 nowych** prognoz wyprodukowanych *po pierwszym fit*, następnie niezależny HOLDOUT; brak automatycznej promocji modelu. **GATE17:** uczciwe parowane porównanie na tych samych meczach.
- Pull requesty #143–146 mogą być scalone tylko po osobnym audycie, aktualnym rebase i przejściu regresji. Nie wprowadzać automatycznego merge. Przed live najpierw kontrolowany, mierzalny pilotaż i jawna decyzja.
- Zmiany zwiększające API use tylko po pomiarze i kontroli limitów. Nie kupować nowych API bez osobnej zgody. Prywatne dane i klucze nie trafiają do repo ani logów.
- **Stan początkowy (zweryfikowany 2026-11-04):** GATE16/17 PENDING, 15/29; M0 91 zamrożonych, 74 kwalifikujące settled, 26 do FIT100, HOLDOUT 0/50; PR #143–146 draft. Dane historyczne są badawcze, nie certyfikowany stary PIT. Te liczby weryfikować ponownie w każdym rzeczywistym run.

## Wykonanie i bramki

| ID | Zadanie i po co | Warunek ukończenia / dowód | Priorytet / zależności | Stan wejściowy |
|---|---|---|---|---|
| **01** | **Zabezpieczyć stan**: sprawdzić backup, manifesty, SHA, możliwość odtworzenia SQLite, prognozy i parametry M0; by móc bezpiecznie cofnąć zmiany | Odtwarzalne kopie na oddzielnej kopii, `PRAGMA integrity_check`, liczby immutable oraz SHA modelu i prognoz zgodne z oryginałem. Odnotować braki, nie deklarować PASS bez faktycznego restore | P1; start | START / WERYFIKACJA |
| **02** | **Przygotować PR #146**: kontrola nowej polityki do 3 forecast attempts/dzień UTC, dedup przed quota, timeoutów, kosztu API, publikacji GitHub i rozłączenia FIT/HOLDOUT; by zwiększać rzeczywiste pregame próbki | Obecny main+patch, regresja, backup PASS i jawny review; osobny merge dopiero po zgodzie; jeden kontrolowany live i pomiar nowych, host-attested próbek, 0 duplikatów i 0 ex-post | P1; po 01, równolegle z 03 | DO ODBIORU / PILOT NIEURUCHOMIONY |
| **03** | **Naprawić PR #143**: krytyczne P1-01 różna semantyka cech TRAIN/forward, P1-02 niewiarygodny historyczny FIT, zamknąć legacy VERIFIED sources; by zapobiec leakage i fałszywym wynikom | Wersjonowany kontrakt cech / kwarantanna niepoświadczonych danych / testy negatywne / SQLite kopia / rebase+CI. Nie zmieniać zatwierdzonych historycznych freeze/M0. | P1; po 01, równolegle z 02 | BLOKADA P1 / NO-GO |
| **04** | **Sprawdzić realny przyrost M0** po kontrolowanym pilocie: pobrane cele, powody odrzuceń, nowe freeze, SHA, host proof, settlements, retry i API cost; by odróżnić poprawę kodu od efektu | Co najmniej jeden wiarygodny live run po dopuszczonej integracji, dowody przed kickoff−90 min, brak duplikatów, udokumentowane koszty i aktualne FIT/HOLDOUT; w razie FAIL rollback | P1; po 02 | CZEKA NA 02 |
| **05** | **Uruchomić generator KB3 TEST** z M0 Elo+Poisson dla 1X2, 1X/X2/12, O/U goli, BTTS i team totals; by pokazać rzeczywiste prognozy bez finalnego Championa | Rzeczywiste dane oraz matematycznie spójne P, audyt rynków i źródeł, wersja modelu, wyraźne RESEARCH/TEST; bez sztucznych typów i bez odblokowania GATE16 | P1; po 01, źródłowe kontrole 03; projekt można tworzyć offline wcześniej | PLAN / NIEURUCHOMIONY |
| **06** | **Archiwizować i rozliczać każdy rynek**: pregame freeze, nazwa+linia rynku, P, godzina, rozstrzygnięcie, Brier/logloss i wyjątki VOID/PUSH; by dane TEST zasilały późniejsze badanie | Immutable freeze, niezależny postmatch scorer na rzeczywistym meczu, dedup, granica czasowa, poprawne reguły per rynek, 0 przepisywania starego forecast | P1; po 05 | PLAN |
| **07** | **Generator raportów PDF**: 3 osobne raporty dziś/jutro/pojutrze plus audyt; bez kursów dopóki nie mają prawdziwej linii/timestamp; by korzystać już z TEST | Trzy rzeczywiste poprawne PDF w języku polskim, testy dat/źródeł/braków, brak fikcji, akceptacja czytelności na telefonie i ustalenie harmonogramu | P2; po 05–06; powiązanie formalne 23–25 | PLAN |
| **08** | **PR #145: zoptymalizować PitchAPI** — pełne native last5/10/15, strony/venue, osiem lig, request count i nowe brakujące źródła; by domykać prawdziwe okna zamiast pobierać nieprzydatne ID | Kompatybilność z integralnością #143, fresh plan na nowej bazie, kontrolowany live A/B z przyrostem xG5/xG10/xG15 na zapytanie; bez przełączania schedule na podstawie starej retrospekcji | P2; przygotowanie offline równolegle, live po 03 | RESEARCH / WARUNKOWY GO |
| **09** | **PR #144: rozwijać CatBoost A/B/C** niezależnie od M0: no-xG, xG5, opcjonalne verified xG10/15 i core stats; by dowieść faktycznej poprawy lub jej braku | Chronologiczne te same mecze, SHAs, brak przecieków, przedziały niepewności, oddzielne prospektywne pary; model nadal NO-GO dla Championa bez silnego wyniku | P2; przygotowanie offline równolegle, nowy freeze po 03 | RESEARCH |
| **10** | **Zamknąć GATE16** wyłącznie po 100 FIT i 50 nowych po fit HOLDOUT; by prawdopodobieństwa były właściwie skalibrowane | Rozłączne ID/timestamps/wersja, fit TRAIN-only, niezależny HOLDOUT i raport before/after; formalny właścicielski odbiór | P1; zależny od prawdziwych nowych wyników i 04/06 | 74/100 FIT; HOLDOUT 0/50, PENDING |
| **11** | **Dodać kartki, rożne, faule** jako osobne modele i rynki TEST; bez szczególnego priorytetu dla under fauli; by rozszerzyć portfolio rynków | Dla każdej rodziny osobna kontrola definicji i danych, trening/chronologia, Brier/logloss, źródła, freeze i settlement; dopiero potem publikacja TEST | P2; after 05/06; formalny krok 28 ma dalsze zależności | PLAN |
| **12** | **Monitoring progów + Champion–Challenger**: FIT100, HOLDOUT50, kompletność xG, drift, wyniki, błędy, alerty i cotygodniowe podsumowanie; by użytkownik wiedział kiedy podjąć decyzję | Trwałe liczniki i ID bramek, brak podwójnych alertów, przetestowane dostarczenie, brak automatycznej promocji, rollback modelu; akceptacja kanału wysyłki | P1 dla monitoringu, P2 dla promocji; może rozpocząć się wcześniej jako read-only | PLAN |

## Kolejność wykonania / kryteria decyzji
1. Rozpocząć od odczytu aktualnego stanu i backup/restore. **Nie scalać PR #146, jeśli krok 01 nie ma wiarygodnego PASS.**
2. **#146** przetestować pod nowym main; **#143** równolegle naprawiać w oddzielnej gałęzi; wyników tych dwóch PR nie łączyć bez audytu.
3. Po dopuszczonym #146 zrobić **tylko kontrolowany pilotaż**. Gdy nie udowodni nowych poprawnych próbek lub przekroczy zatwierdzone limity, wstrzymać szerszy rollout i naprawić.
4. TEST z prawdziwym M0 można przygotowywać offline. Publikować wyłącznie nowe, rzeczywiście zamrożone przedmeczowe prawdopodobieństwa; historyczny replay oznaczać wyraźnie.
5. #145, #144 rozwijać bez nadpisania aktywnego M0. Osiąganie progów monitorować automatycznie; dopiero świadoma decyzja o Champion.
6. Po każdej kontroli dopisać datę, wynik PASS/PARTIAL/FAIL, SHA, link CI/PR, brakujące dane i następny krok do `docs/ZMIANY.md`. Nie wymyślać benchmarków, liczby nowych próbek ani statusu wykonania.

## Rejestr bieżącego wykonania
- **2026-11-04:** plan 12 kroków zatwierdzony na polecenie właściciela. Nie jest dowodem uruchomienia generatora TEST.
- **Następna czynność:** niezależna weryfikacja dostępnych backupów i ich odtwarzalności na kopii (krok 01); następnie kontrola najnowszego main vs PR #146 i równoległe P1 #143.

## Dyspozycja właściciela — 04.11.2026, bez prywatnych kluczy

- Właściciel nie chce angażowania prywatnego klucza RSA w dalszą budowę. Krok 01: **operacyjny GO** na podstawie odtworzenia kopii SQLite na izolowanej bazie, testów integralności i hashy. Nie stanowi to potwierdzenia odtwarzalności szyfrowanej kopii offsite.
- Szyfrowany backup na Google Drive pozostaje `OFFSITE_DECRYPT_RESTORE_NOT_VERIFIED`, a bez klucza może być niemożliwy do odtworzenia. Nie przedstawiać go jako samodzielnej, pełnej ochrony przed utratą wszystkich innych kopii.
- Nie wymagać wysyłania/ujawniania żadnych kluczy w rozmowie. Nie zamieniać automatycznie backupu w jawny plik w Drive. Dalsze prace: #146 i równolegle #143, po odrębnych testach i bez naruszania M0.
- Szczegółowa wersjonowana decyzja: [plan uzupełniający](PLAN_WYKONAWCZY_KB3_TEST_DEVELOPMENT_2026-11-04.md) i [rejestr](ZMIANY.md).
