# KB Score 3.0 — Protokół GATE 05: audyt API-Football

**Data:** 25.10.2026 (Europe/Warsaw). **WYNIK: PASS / ZALICZONO** w zakresie audytu **źródła** danych. **Nie oznacza to jeszcze importu całej historii statystyk ani gotowej bazy treningowej.**

## Testy i trwałe dowody

- **Główny audyt 5 lig × sezony 2021–2026 (30 kombinacji):** [Actions run #40218310521](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40218310521), wykonanie zakończone `success`. [Pełny raport liga–sezon](audits/API_FOOTBALL_STEP05_2026-10-25.md), [zagregowane dane JSON](../data/audits/API_FOOTBALL_STEP05_2026-10-25.json). Jego procedura: [skrypt](../scripts/api_football_coverage_audit.py) i [6 testów](../tests/test_api_football_coverage_audit.py).
- **Drugi niezależny audyt z odrębnym skryptem:** [Actions run #40218180472](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40218180472), również `success`, [drugi skrypt](../scripts/step05_api_football_audit.py), [5 testów](../tests/test_step05_api_audit.py). Zebrane 25 kombinacji sezonów 2022–2026, **131 zapytań, bez błędów**; raport w artefakcie uruchomienia. **Wszystkie 25 wspólnych wierszy miało identyczne wartości liczby meczów i liczby zakończonych spotkań** w obu niezależnych odczytach.
- Oba workflow są testami etapowymi, nie harmonogramem do codziennego pobierania. Przy przyszłej automatyzacji wybrać jedną kanoniczną wersję, aby nie zużywać podwójnie limitów.

## Wyniki głównego testu

| Parametr | Weryfikowalny wynik |
|---|---:|
| Plan dostępu | Pro, aktywny |
| Limit dzienny API-Football | 7500 zapytań |
| Pozostało po głównym teście w chwili zrzutu | 6816 (liczba nietrwała) |
| Limit na minutę z nagłówka | 300 |
| Wykorzystane przez główny audyt | 112 zapytań, limit bezpieczeństwa w skrypcie 125 |
| Liczba sprawdzonych kombinacji liga–sezon | 30/30 |
| Łączna liczba wpisów meczowych w terminarzach 2021–2026 | 10 679 |
| Próbki statystyk dwóch drużyn (2 na liga–sezon) | 60/60 zwróciło dane |
| Faul, rożny, strzały celne: obie drużyny w próbkach | 60/60 dla każdej z trzech kategorii |
| Żółte kartki obu drużyn w próbkach | 59/60 (jeden brak, nie zero) |
| Przykładowe odpowiedzi składów / wydarzeń / statystyk zawodników | 5/5 lig zwróciło listy |
| Odpowiedź bieżącego endpointu kursów (Premier League, sezon 2026) | 10 wpisów na pierwszej stronie, 3 strony w chwili testu |
| Błędy API w głównym teście | 0 |
| Testy offline główne / dodatkowe | 6/6 oraz 5/5 PASS |

## Wnioski i anomalie

1. **API-Football to realnie działające główne źródło historycznych terminarzy, wyników i części statystyk dla lig: Premier League, La Liga, Serie A, Bundesliga, Ligue 1.** Główne pięć zakończonych sezonów 2021–2025 ma historię wynikową; sezon 2026 jest nieukończony, więc nie traktować przyszłych meczów jako brakujących wyników.
2. **Kolejność i liczbę meczów ustala API, nie teoretyczna liczebność ligi.** W raportach występują np. Serie A 2022: 381 rekordów, Bundesliga 2021: 308, Ligue 1 2021: 382. Do wyjaśnienia w kroku 10: baraże, anulacje, przełożenia i duplikaty. Nie usuwać rekordów tylko dlatego, że liczba różni się od oczekiwanych 380/306.
3. **Ligue 1 / 2025:** 308 wpisów, 307 oznaczonych jako zakończone w chwili audytu. W bazie wymaga jawnego statusu nieukończonego spotkania.
4. **Ligue 1 / 2022:** w jednej z dwóch próbek brak żółtych kartek dla obu drużyn mimo obecności ogólnych statystyk. Braku nie wolno zastąpić zerem.
5. Próbka **2/2 na sezon** świadczy o dostępności, a nie o 100% kompletności wszystkich 10 679 spotkań. Pełny audyt jakości statystyk per fixture należy do kroków 09–10.
6. Kursy API-Football mają opisane w dokumentacji wąskie okno historii (~7 dni). **Nie można z bieżących kursów odtworzyć potwierdzonych prematch odds dla sezonów 2021–2025.** Osobny plan archiwizacji i ocena kosztu w kroku 19.
7. Opóźnienia dostarczania danych mogą zależeć od rozgrywek — statyczny audyt jednej chwili nie jest pomiarem faktycznej latencji. Przed produkcją należy wdrożyć próbkowanie z czasem pobrania i retry.
8. Nie było nowych zakupów. Łącznie dwa audyty użyły **112 + 131 = 243 wywołań** API; pozostała pula zależy również od innych workflow na tym samym koncie i zmienia się w czasie.

## Warunki PASS / testy GATE 05

- [x] Istnieje tabela **liga × sezon × typ danych**, z 30 wierszami i konkretnymi liczebnościami; **brak nie jest kodowany jako zero**.
- [x] Raport ma datę, znane limity, zużycie zapytań, kontrolę sezonów i zgłoszone błędy.
- [x] Odczyt 60 statystyk, 15 dodatkowych endpointów i kursów, z zachowaniem informacji o braku.
- [x] Scenariusze offline sprawdzające powtarzalność próbki, błędne statusy, braki danych, limity wywołań.
- [x] Drugi niezależny przebieg potwierdził wszystkie 25 wspólnych liczebności.
- [x] Wynik zapisano w repo i w głównym dzienniku projektu na Google Drive; bez ujawnienia sekretów.

**Decyzja:** GATE 05 — **PASS**, techniczna kontrola powyższych dwóch wykonań. **Kolejny: KROK 06 — audyt PitchAPI**, nieuruchomiony w tym kroku. Krok 05 nie zatwierdza automatycznie historii xG ani modeli ML. Główny plan: [Google Docs](https://docs.google.com/document/d/10wjHL3r3OAuxtezwcIeWztxS8lwjhYon5GM3BLhI0xE/edit).
