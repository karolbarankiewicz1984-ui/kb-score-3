# KB Score 3.0 — MODEL (koncepcja metodologii i testów)

**Stan:** specyfikacja projektowa v0.1, KROK 04. **To nie jest implementacja ani wynik treningu.** Brak zatwierdzonego modelu KB3.0; nie podajemy fikcyjnych skuteczności i nie nazywamy starych modeli nowym silnikiem.

**Źródło prawdy:** [plan i dziennik Google Docs](https://docs.google.com/document/d/10wjHL3r3OAuxtezwcIeWztxS8lwjhYon5GM3BLhI0xE/edit) · [PLAN.md](PLAN.md) · [DANE.md](DANE.md) · [ZMIANY.md](ZMIANY.md).

## 1. Cel, zakres, rozdzielenie projektów

- Budujemy **nowy i niezależny** model piłkarski KB Score 3.0. Historyczne KB2.1, API Market, MultiModel służą wyłącznie jako **punkty odniesienia**, z odpowiednią kontrolą porównywalności.
- Cel podstawowy: **rzetelne, kalibrowane szanse zdarzeń sportowych**, nie automatycznie wysoki ROI i nie dowolnie przyjęte 80–90% hit rate.
- Model wyznacza P **z cech sportowych, nie z kursu bukmachera**. Porównanie ceny/EV jest osobną warstwą po prognozie.
- Pierwsze rodziny: 1X2, rozkład goli, Over/Under, BTTS. Kolejne: faule (w tym Under), kartki, rożne — po osobnym audycie źródeł.
- Nie kopiujemy z KB2.1 schematu wag 35/35/30 ani kalibracji N150 jako algorytmu ML.

## 2. Architektura modelowania — kolejne poziomy

### M0: baseline bez uczenia skomplikowanego ML

- **ELO**: dynamiczna względna siła drużyn; współczynniki i początkową ocenę trzeba oszacować na TRAIN, bez dostępu do przyszłych wyników.
- **Model bramek Poissona**: parametry atak/obrona + przewaga gospodarzy; ewentualna korekta Dixon–Coles lub odmiana modelu tylko po pozytywnych testach.
- Z rozkładu wyniku wyprowadzić P(1), P(X), P(2), O/U, BTTS i team totals. Weryfikować sumowanie się prawdopodobieństw i monotoniczność rynków.

### M1: niezależny ML 1X2

- **CatBoost**: wejściem są historycznie dostępne cechy przedmeczowe; wyjściem P(1), P(X), P(2).
- Eksperymenty obowiązkowe: model bez xG, model z xG (tam, gdzie dane rzeczywiście istnieją), porównanie wpływu braków danych.
- Wersjonowanie: konfiguracja parametrów, seed, kod SHA, zbiór i hash danych, zakres treningowy, pliki modelu i wynik odtwarzalnego testu.
- Jednoznacznie oddzielić wytrenowane modele od kandydatów, modeli odrzuconych i wersji produkcyjnych.

### M2: rynki goli i specjalizacje

- Najpierw wyprowadzić Over/Under i BTTS ze wspólnego rozkładu bramkowego. Potem dopuścić osobne modele ML, **jeśli wykazują poprawę** na uczciwym teście.
- Kontrola własności: P(Over 3,5) ≤ P(Over 2,5) ≤ P(Over 1,5); P(1)+P(X)+P(2)=1; dla Under odpowiednia relacja odwrotna; dla 90 minut brak nieuprawnionego uwzględniania dogrywki.
- Faule, rożne i kartki nie są matematycznie tym samym co gole. Osobne cechy/etykiety, odrębna walidacja i rozliczenia bukmacherskich linii.

### M3: ensemble (opcjonalny)

Łączenie Poissona, ELO i CatBoost wyłącznie wtedy, gdy porównywalne wyniki walidacyjne pokazują poprawę względem najlepszej niezależnej metody. Nie ustalamy z góry wag 50/50 i nie dobieramy ich na zbiorze końcowym TEST.

## 3. Typy cech (planowane, niepotwierdzone w API)

1. Siła długoterminowa — ELO, siła rywali, poziom ligi.
2. Forma — ostatnie 5/10/15 spotkań, średnie ważone czasowo, dom i wyjazd.
3. Gole i defensywa — zdobyte i stracone, jakość przeciwników.
4. xG/xGA — **tylko rzeczywiście dostępne wcześniej** i z udokumentowanym pokryciem; wersja bez xG obowiązkowa jako kontrola.
5. Obciążenie — liczba dni odpoczynku, liczba meczów ostatnio, podróże (gdy dane wiarygodne).
6. Skład, trener, kontuzje — tylko autentyczne historyczne snapshoty albo przyszłe odczyty forward z timestampem. Nie wolno przenosić dzisiejszego stanu na dawny mecz.
7. Braki danych — maski braków i informacja o jakości pobranych cech; nigdy nie wypełniać ich fikcyjną liczbą.

Pełny katalog i warunki pochodzenia danych opisuje [DANE.md](DANE.md); zostanie zatwierdzony w kroku 11.

## 4. Ścisła metodologia oceny bez przecieków

- **TRAIN**: starsze mecze używane do nauki.
- **VALIDATION**: późniejszy okres do wyboru wariantów, doboru parametrów i kalibracji.
- **TEST**: wydzielony, nowszy, nieużywany do strojenia ani selekcji. Odczytać wyniki i raportować tylko zgodnie z wcześniej zatwierdzoną procedurą.
- **Walk-forward**: trening na dostępnej przeszłości i symulacja prognoz w kolejnych okresach. Wszystkie rolling features wyliczać osobno dla daty rozegrania meczu.
- **Anti-lookahead**: testy celowo błędnego inputu muszą wykazać, że użycie wyniku późniejszego meczu lub opublikowanego po cutoff składu powoduje błąd/blokadę.
- **No leakage through odds**: model sportowy nie używa kursów jako cechy wejściowej; kurs porównawczy po stronie cenowej jest dozwolony, ale posiada oddzielny timestamp.
- **Spójność i reproducibility**: to samo wejście, kod, seed i model muszą dawać powtarzalny wynik w ramach określonej tolerancji.
- Benchmark ze starego KB2.1: tylko dla prawdziwych przedmeczowych prognoz; odzyskany po wydarzeniu wiersz nie jest równoznaczny z przedmeczowym freeze.

## 5. Co uznamy za dobrą prognozę?

| Miara | Co mierzy | Zasada |
|---|---|---|
| Brier score | Średni błąd kwadratowy prawdopodobieństwa | Niżej lepiej; definicję multi-class ustalić z góry |
| Log loss | Kara za błędną wysoką pewność | Niżej lepiej, test na tych samych meczach |
| Reliability/calibration | Czy prognozy np. 70% odpowiadają trafieniom w długiej próbie | Przedziały i liczebności z przedziałami niepewności |
| Hit rate | Odsetek trafień przy danej regule selekcji | Raportować kursy, rynek i N, nie porównywać różnych linii bez kontroli |
| Coverage | Ile meczów rzeczywiście przeanalizowano | Niskie pokrycie obniża wartość wniosków |
| EV i ROI symulowane | Opłacalność po cenie dokładnie dostępnej w danym momencie | Wyłącznie na realnych historycznych snapshotach kursów i z ograniczeniami |
| CLV | Relacja do późniejszej ceny rynku | Tylko po zapisaniu prawidłowych kursów otwarcia/pobrania/zamknięcia |
| Stabilność | Jakość między ligami, sezonami i oknami czasowymi | Nie awansować po jednej udanej serii |

**Nie zakładamy dodatniego ROI.** Odróżniamy trafność prognozy od przewagi cenowej. Dodatnia wartość oczekiwana w modelu nie gwarantuje wyniku finansowego.

## 6. Kalibracja

- Nie korzystać z mapy P(cal) KB2.1.
- Kalibrację (np. sigmoid/isotonic) wybrać na wydzielonych danych, chroniąc finalny TEST.
- Raportować przed/po: Brier, log loss, reliability bins i rozmiary prób.
- Jeśli kalibracja nie poprawia jakości na walidacji i w niezależnym teście, nie wdrażać jej.

## 7. Champion–Challenger i zgoda właściciela

1. Najlepszy po testach silnik zostaje **Championem** — nie musi nim zostać CatBoost; możliwy Poisson lub brak awansu.
2. Nowy **Challenger** otrzymuje odrębną wersję, dane, log treningu i wynik porównania na tych samych meczach.
3. Pozytywna walidacja nie wystarcza do bezwarunkowego awansu: potrzebna kontrola jakości forward, szczególnie przy małym N.
4. **Awans lub wycofanie** z produkcji wymaga udokumentowanej decyzji i osobnej zgody właściciela; musi istnieć rollback.
5. Nie wolno modyfikować starych zamrożonych prognoz po poznaniu wyniku meczu.

## 8. Warstwa decyzji, ceny i raportów

Najpierw P(model), potem niezależna jakość danych i poziom niepewności, na końcu cena/EV. Zdarzenia klasyfikujemy w osobnych rankingach HIGH PROBABILITY, VALUE CANDIDATE, WATCH, NO BET. Ich progi **nie są dziś zatwierdzone** — będą wyznaczone po walidacji. 

Dwa momenty prognozy: **EARLY** (z wyprzedzeniem) oraz **FINAL PREMATCH** (po nowszych potwierdzonych informacjach, ale przed kickoff). Oba mają własne ID, timestamp i zapis freeze. Raporty PDF dziś/jutro/pojutrze i docelowe 09:30 Europe/Warsaw są przyszłym zadaniem kroku 23–25, nie działającą dziś automatyzacją.

## 9. Kiedy kończy się poszczególny etap modelowy?

| Krok | Warunek PASS — konieczne dowody |
|---|---|
| 11 | Katalog cech z datami dostępności, testy no-lookahead |
| 12 | Chronologiczny manifest TRAIN/VALIDATION/TEST, walk-forward |
| 13 | ELO + Poisson, sumowanie P do 1, baseline Brier/log loss i testy |
| 14 | Odtwarzalny model CatBoost, hash, metryki TEST, eksport i P-sum |
| 15 | Modele goli i testy monotoniczności/spójności |
| 16 | Kalibracja bez leakage, wyniki przed/po |
| 17 | Uczciwa macierz porównania na wspólnych meczach/rynkach |
| 18 | Karta Championa z zatwierdzeniem i identyfikatorem wersji |
| 20 | Reprodukowalne rankingi i testy graniczne klas decyzji |
| 26 | Challenger/Champion, protokół awansu lub odrzucenia, rollback |
| 27 | Kontrolowany test alarmów jakości/dryfu i reakcji |
| 28 | Oddzielne testy każdej rodziny rynku, brak awansu przy słabej próbie |

## 10. Otwarte decyzje (nie są implementacją)

- Które ligi i lata zapewniają wiarygodną próbę? **Kroki 05–06.**
- Gdzie znajduje się trwały magazyn i jak weryfikować jego restore? **Krok 08.**
- Czy prawdziwe xG poprawia wynik na TEST? **Kroki 14–17.**
- Dokładne parametry kalibracji, progi jakości i minimalna próbka? **Kroki 16–18 i 20.**
- Dostępność historycznych kursów i zasady EV? **Krok 19.**
- Wysyłka, monitorowanie i harmonogram produkcyjny? **Kroki 23–25.**

**Stan na 25.10.2026:** to dokument metodologiczny, bez nowych predykcji, bez treningu i bez uznanych rekomendacji KB Score 3.0.
