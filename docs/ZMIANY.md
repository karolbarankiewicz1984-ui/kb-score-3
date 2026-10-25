# KB Score 3.0 — ZMIANY I DECYZJE

**Typ dokumentu:** append-only dziennik zmian, decyzji, ryzyk i bramek odbioru. Nie usuwać zapisów historycznych ani wpisów FAIL; ewentualną korektę opisać nowym wpisem. **Źródło prawdy dla statusów:** [Google Docs — Plan główny](https://docs.google.com/document/d/10wjHL3r3OAuxtezwcIeWztxS8lwjhYon5GM3BLhI0xE/edit). **Kopia 29 etapów:** [PLAN.md](PLAN.md). Dokumenty techniczne: [DANE.md](DANE.md), [MODEL.md](MODEL.md).

## Reguły wpisów

Każdy odbiór zawiera: identyfikator kroku, datę i godzinę (z podaną strefą lub UTC), stan przed/po, wynik PASS/FAIL, link do dowodu, metadane testu, znane ograniczenia, osobę/automat dokonujący weryfikacji oraz następny krok. Samo uruchomienie testu **nie oznacza** PASS. Przed wpisaniem ZALICZONO należy ponownie odczytać dowody. Nowa wersja modelu, nowa opłata lub uruchomienie produkcji wymaga osobnej zgody właściciela.

**Status projektu podczas tworzenia tego dokumentu:** 3/29 odebranych (01–03); krok 04 w przygotowaniu; 05–29 jeszcze nieodebrane. Dziennik Google Docs może zawierać późniejsze wpisy — w razie rozbieżności **odczytujemy oryginał Google Docs**.

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

## GATE 04 — dokumentacja (w opracowaniu, jeszcze NIE ZALICZONO)

**Cel:** przygotować 4 pliki [PLAN.md](PLAN.md), [DANE.md](DANE.md), [MODEL.md](MODEL.md), [ZMIANY.md](ZMIANY.md) i linki między nimi oraz do Google Docs; skontrolować 29/29 kryteriów odbioru, brak fałszywych zaliczeń i zgodność źródła prawdy. 

**Dowód do dołączenia po wykonaniu:** URL commitów, raport odczytu wszystkich plików GitHub, porównanie statusów z dokumentem Google, wpis w Google Docs, końcowa kontrola README. 

**Decyzja odbioru:** PENDING — wynik będzie wpisany dopiero po potwierdzonym odczycie i testach, bez uznawania samego faktu stworzenia dokumentów za ukończenie.

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
