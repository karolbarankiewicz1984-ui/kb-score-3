# KB Score 3.0 — audyt pracy offline podczas wyczerpania GitHub Actions

**30.10.2026, Europe/Warsaw.** Analiza odczytanych plików `.github/workflows/`, metadanych GitHub Actions i repozytorium **bez uruchamiania płatnych runnerów, bez użycia PitchAPI, bez fit i bez dotykania Premier League TEST 2026/27**.

## Potwierdzone ograniczenia i wielkość obciążenia

- GitHub powiadomił 29.10.2026 o **3000/3000** wykorzystanych minutach w miesięcznej puli konta i resecie 01.11.2026; stan budżetu konta $0 nie został samodzielnie odczytany.
- Katalog `.github/workflows/` na `main`: **111** plików workflow. To nie jest liczba aktywnych harmonogramów; część to jednorazowe zadania historyczne.
- API repozytorium raportuje **1009** historycznych uruchomień w chwili odczytu. Sama liczba nie dowodzi, ile minut pochłonęło konkretne zadanie; dokładnego rozkładu billed minutes nie odczytano.
- [Main M0 8-league](../.github/workflows/kb3-step16-m0-720-eight-forward.yml) ma trzy harmonogramy dziennie: `21 6 * * *` (forecast), `17 8,22 * * *` (dwa settlement), oraz `push` i `pull_request` ograniczone filtrami plików. Testy uruchamiają instalację `catboost==1.2.8` i kryptografii, następnie zadanie rzeczywiste instaluje je ponownie w **oddzielnym jobie**, gdy zostaje zakwalifikowane do wykonania. To koszt uruchomienia/instalacji, ale nie znamy jego dokładnej wartości w minutach.
- [Step17 native xG](../.github/workflows/kb3-step17-native-xg-eight-daily.yml) — jedna próba dziennie `41 6 * * *`.
- [Trzy-ligowy starszy M0 SHADOW](../.github/workflows/kb3-pitchapi-three-league-daily.yml) — jedna próba dziennie `17 6 * * *`; [starszy settlement](../.github/workflows/kb3-m0-real-postmatch-calibration.yml) — dwie próby `47 7,22 * * *`.
- [Starszy Step14 C native xG](../.github/workflows/kb3-step14-c-native-asof-daily.yml) — jedna próba `42 4 * * *`; [starszy publiczny sidecar](../.github/workflows/kb3-step14-public-schedule-sidecar.yml) — jedna próba `35 5 * * *`. **Łącznie wymienione procesy dają 9 zaplanowanych uruchomień dziennie**, poza innymi harmonogramami z pełnego katalogu i uruchomieniami ręcznymi/PR.
- Nieustawiony lub przekroczony limit API, liczba wywołań providera i koszt Actions to **różne** ograniczenia. Optymalizacji czasu runnera nie wolno utożsamiać z automatycznym zwiększeniem liczby próbek.

## Priorytety offline — bez ingerencji w model

| Priorytet | Zadanie | Korzyść | Decyzja / status |
|---|---|---|---|
| P0 | Zachować istniejący `M0_ELO_POISSON_RESEARCH_720TRAIN_V1` i jego SHA, 73 zamrożone poświadczenia i 100+50 | Brak duplikacji prognoz i przecieku czasowego | OBOWIĄZUJE, niczego nie przeliczać wstecz |
| P1 | Rozdzielić w 111 workflow zadania: (a) live collecting/settlement, (b) potrzebne jednorazowe audyty, (c) historyczne ręczne | Ograniczenie zbędnego zużycia miesięcznych minut | WYMAGA pełnej klasyfikacji i zatwierdzenia wyłączeń |
| P1 | Ocenić, czy stary 3-ligowy SHADOW, Step14 native xG i sidecar mają nadal wymagane niezastępowalne dowody | Nie usuwać cennego strumienia badawczego bez dowodu równoważności | BEZ AUTOMATYCZNEGO WYŁĄCZANIA |
| P1 | Usprawnić instalację zależności i cache, a po resecie zmierzyć rzeczywisty czas 2 jobów Step16 | Obniżenie czasu runnera bez zmiany matematyki M0 | POMIAR PRZED ZMIANĄ, brak oszacowanych oszczędności |
| P2 | Przygotować porównanie sparowane: M0 720, ELO_ONLY, CatBoost 720 bez xG — tylko dla prognoz z tego samego nowego cutoff i późniejszym wynikiem | Uczciwy wybór modelu w kroku 17 | mechanizm istnieje, bez sztucznego backfill 73 starych M0 |
| P2 | Dopracować raport przed kalibracją: liczba kwalifikowanych, Brier sum3, log loss, hit rate, podział na 8 lig, rozrzut i spójność | Brak pozornej poprawy przez dominację jednej ligi | Żaden nowy wynik nie jest dostępny; 100+50 bez zmian |
| P2 | Kontynuować audyt native xG last5: wymagane te same źródła, oba zespoły, pięć faktycznie ostatnich meczów, żadnego 0 za brak danych | Bezpieczna przyszła gałąź CatBoost z xG | 29.10: zweryfikowane 7/8 par xG, kompletność last5 0/74, `NOT_TRAINED` |

## Bramki przed zmianą automatyzacji

1. **Nie zmieniać teraz** produkcyjnych czy badawczych parametrów, progów kalibracji, listy lig, definicji wejść czy dat historycznych prognoz.
2. Przed wyłączeniem workflow ustalić: jaki zbiór danych generuje, czy obecny M0/Step17 z niego korzysta, czy nadpisywanie jest wykluczone, czy są obowiązkowe dowody do kroku 14/16/17.
3. Wszelkie proponowane redukcje `schedule` i `push` przygotować w osobnym PR ze skryptowymi testami statycznymi; nie scalać bez przejścia testów po resecie albo osobnego zaakceptowania ryzyka przez właściciela.
4. Po 01.11.2026 sprawdzić realny przydział Actions, `SUCCESS`, nowe `FROZEN_M0_720_EIGHT.json`, oryginalny hash, datę artefaktu GitHub przed meczem i prawdziwe oddzielne rozliczenia. **Nie nadrabiać opuszczonego cutoff prognozami po meczach**.

## Faktyczny efekt tej pracy

Odtworzono harmonogramy wymienionych 6 workflow z `main`, zakres kolektora i zależności; stworzono **plan optymalizacji**. Nie wyłączono żadnej automatyzacji, nie uruchomiono żadnego nowego modelu lub treningu, nie tworzono fikcyjnych prognoz, nie uruchamiano usług płatnych, nie naruszono dowodów 73 zamrożonych prognoz. Formalnie `GATE16=PENDING`, `GATE17=PENDING`, 15/29.
