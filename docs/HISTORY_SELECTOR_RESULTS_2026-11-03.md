# CODEX-03 — selektor pełnych okien i rzeczywisty replay źródeł

Przygotowanie zakończone 04.11.2026; nazwy artefaktów zachowują datę rozpoczęcia 03.11.2026.

**Odbiór: PARTIAL.** Kod i regresja przechodzą; na zapisanych danych nowe
uszeregowanie szybciej domyka xG5. Nie wykazano przyrostu xG10/15 ani
skuteczności na niepobranych źródłach. Nowy selektor pozostaje opcją badawczą;
harmonogram używa `current`. Bez automatycznego merge lub uruchomienia live.

Baza main: `eabab06139b185d34450d314989783bdc980b088`.
[Protokół przed A/B](HISTORY_SELECTOR_PROTOCOL_2026-11-03.md),
[pełny raport A/B i obu planów](audits/HISTORY_SELECTOR_AB_2026-11-03.json.gz),
[podsumowanie](audits/HISTORY_SELECTOR_SUMMARY_2026-11-03.json),
[konkretne następne 240 ID](audits/HISTORY_SELECTOR_NEXT_240_2026-11-03.csv).

## Kontrola starszych prac

| PR / element | Stan wykorzystany w tym PR |
| --- | --- |
| [#125](https://github.com/karolbarankiewicz1984-ui/kb-score-3/pull/125) | Draft head `1cf4a54c8e746dfbcca24cad4f0f57bcaed58f23`. Jego moduł/testy rankingu last5 są już identyczne na main, nadal bez podłączenia do live. Obsługuje przyszłe cele i inny strumień <=33 calls, bez historycznych par 10/15/venue. Nie dodano ponownie tego kodu ani jego starego limitu. |
| [#137](https://github.com/karolbarankiewicz1984-ui/kb-score-3/pull/137) | Izolowany collector, natywne ID, 48 meczów / 150 wywołań, 2023/24 warmup, encrypted evidence i immutable SQLite zachowane. |
| [#138](https://github.com/karolbarankiewicz1984-ui/kb-score-3/pull/138) | Pełny indeks zakończonych spotkań, prawdziwe poprzedniki 5/10/15 przez sezony, all/venue i diagnostyka braków już istnieją. Bez kopiowania cache jako dowodu. |
| [#139](https://github.com/karolbarankiewicz1984-ui/kb-score-3/pull/139) | Pięć odrębnie szyfrowanych paczek, priorytet poprzedników, osobne recheck xG i kartek pozostają. Nie zmieniono tolerancji 0.15 ani definicji źródłowego PASS. |
| [#140](https://github.com/karolbarankiewicz1984-ui/kb-score-3/pull/140) | Kontrolowane badawcze nakładki kartek zamiast duplikowania placeholderów pozostają; stare immutable source items bez zmian. |
| [#141](https://github.com/karolbarankiewicz1984-ui/kb-score-3/pull/141) | Realny eksperyment xG5 nie dowiódł poprawy CatBoost. Ten PR optymalizuje źródła; nie zmienia modelu ani nie przypisuje mu przewagi. |
| [#142](https://github.com/karolbarankiewicz1984-ui/kb-score-3/pull/142) | Zachowano rotację całej paczki do niedopobranej ligi przy rozstępie >=64, >=3 ligach i paczce >=32. Nowy ranking działa wewnątrz takiej paczki, przez wszystkie sezony. |

Dotychczasowy priorytet sumuje punktację pojedynczych braków z okien dwóch
drużyn, lecz nie mierzy łącznego kosztu domknięcia pary. Nowy greedy wybiera
uzupełniające się zestawy brakujących meczów. Wagi all5/10/15=16/8/4 oraz
venue5/10/15=4/2/1 są zamrożone przed A/B; nie stroiliśmy ich na wyniku replay.
Nie jest to dowód globalnie optymalnego rozwiązania.

## Potwierdzony stan źródeł

Odczyt read-only potwierdza **8621** indeksowanych spotkań, **816** obserwacji
i **742** źródłowe statusy VERIFIED. Po wykluczeniu UCL: **8064 / 811 / 738**
w ośmiu ligach. ENG nie ma w tej bazie i jest zabronione w nowym selektorze.

| Populacja celów na bieżącym snapshocie | xG5 | xG10 | xG15 | Venue5 / 10 / 15 |
| --- | ---: | ---: | ---: | ---: |
| Obserwowane szczegółowo cele — definicja dotychczasowego raportu | 150 | 32 | 5 | 107 / 18 / 2 |
| Wszystkie zaindeksowane krajowe cele z wynikiem | 155 | 32 | 5 | 115 / 20 / 2 |

Różnica populacji nie jest poprawą kolektora. Wynik celu może być dostępny
w indeksie bez jego szczegółowych statystyk; kompletne cechy pochodzą wyłącznie
z wcześniejszych spotkań. Raport zawsze rozdziela te dwa mianowniki.

SQLite SHA256:
`bf95048fdff2dc098d0d3add55a0a3b5fadc45687f4a24703a03f9cbf87ed164`.
Kontrole integralności, natywnych tożsamości, zegarów i jawnego historycznego
statusu przeszły. Użyto **zapisanych statusów main**, bez ponownego odszyfrowania
i uwierzytelnienia raw receipts. Nie jest to odbiór CODEX-01 / PR #143 ani
naprawa jego konfliktów `total_shots`. Wyniki są warunkowe względem bieżącej
polityki źródłowej i wymagają ponownego pomiaru po jej odbiorze.

## Rzeczywisty A/B bez nowych pobrań

Replay korzysta z run **41692857683-1**: początkowo **571** krajowych
obserwacji (518 statusów VERIFIED), następnie **240 rzeczywiście zapisanych
par źródeł**: 220 VERIFIED i 20 źródłowych rozbieżności xG. Oba selektory mają
te same dostępne ID i pełny indeks poprzedników. Status wybranego źródła jest
ujawniany dopiero po wyborze; ranking nie otrzymuje przyszłych wyników poboru.

Tabela dotyczy **tych samych 571 początkowych celów**, bez zmiany próby.
Początek: xG5=146, xG10=32, xG15=5. Wartości poniżej to **rzeczywiste przyrosty
względem tego początku**, obliczone z zapisanych źródeł.

| Pary źródeł na metodę | Odczyty udanych endpointów na metodę | Przyrost xG5 current | Przyrost xG5 nowy | Przyrost xG10 current / nowy | Przyrost xG15 current / nowy |
| --- | ---: | ---: | ---: | ---: | ---: |
| 48 | 96 | 0 | 1 | 0 / 0 | 0 / 0 |
| 96 | 192 | 0 | 3 | 0 / 0 | 0 / 0 |
| 144 | 288 | 1 | 4 | 0 / 0 | 0 / 0 |
| 192 | 384 | 2 | 4 | 0 / 0 | 0 / 0 |
| 233 | 466 | 4 | 4 | 0 / 0 | 0 / 0 |

Przy 96 parach nowy ma **3 dodatkowe pełne xG5** względem starego, czyli
3.125 na 100 par / 1.5625 na 100 udanych odczytów endpointów. Przy 144 parach
nowy osiąga cały obserwowany przyrost czterech xG5. W pięciu paczkach baseline
wybrał 233 rekordy, nowy 240; baseline przy 233 już osiąga ten sam wynik.
**Nie ma większego końcowego zbioru xG5 po wyczerpaniu tej samej puli**.
Venue5/10/15 nie wzrosły w tej próbie. W populacji wszystkich celów wyniki
przesuwają się odpowiednio 151→155 xG5, z tym samym przyrostem i rankingiem;
nie sumujemy wyników obu populacji.

Odczyty endpointów oznaczają dwie zarchiwizowane odpowiedzi stats/shots na
parę, nie nowe zapytania HTTP. Nowych calls: **0**. Archiwalny raport podaje
655 wywołań SDK dla oryginalnych pięciu paczek (175 katalog/listing + 480
stats/shots). Historyczne wewnętrzne retry SDK mogły być poza tym licznikiem;
nie potwierdzamy na tej podstawie dokładnej dawnej liczby fizycznych HTTP.
Przy 48 i 96 parach obie metody dotykają tylu samych paczek; przy 144 i 192
baseline dotyka o jedną więcej z powodu niewypełnionych paczek. To także
raportujemy, zamiast ukrywać koszt katalogowania za liczbą par.

**Ograniczenie A/B:** to zamknięty replay puli wybranej wcześniej przez stary
kolektor, nie randomizowany test live ani dowód na nieznanych źródłach.
Nie obejmuje wyników nieudanych pobrań, które nie utworzyły rekordu.
Porównanie daje dowód lepszego porządku w tej puli, bez generalizacji wyniku
3 do pozostałych lig lub przyszłych okresów. Nie zaobserwowano przyrostu 10/15.

## Które mecze pobrać dalej

[CSV 240 prawdziwych ID](audits/HISTORY_SELECTOR_NEXT_240_2026-11-03.csv)
podaje paczkę, kolejność, ligę, sezon i kickoff. Każdy rekord ma status
`PLANNING_NOT_FETCHED`. Indeks potwierdza zakończenie spotkania, nie przyszłą
kompletność jego stats/shots. Paczki: **ITA48 → POL48 → NED48 → TUR48 → FRA48**.
GER, BEL i ESP pozostają w kandydaturze ośmiu lig; po tej rotacji GER będzie
jedną z najmniej pobranych. Nie zwiększamy koncentracji BEL/ESP. Jeśli źródła
zawiodą, po każdej paczce ranking i rotacja są liczone z rzeczywiście zapisanych
rekordów, a nie z założonego planu.

Poniżej **WYŁĄCZNIE SUFIT PLANOWANIA**, jeśli każda nowa para okaże się
zweryfikowana. To nie jest realny przyrost i nie zmienia obecnych liczników.
Stała populacja: wszystkie 8064 krajowe cele, początek 155 / 32 / 5.

| Metoda, plan kolejnych 5×48 | xG5, jeśli wszystkie źródła poprawne | xG10, jeśli poprawne | xG15, jeśli poprawne |
| --- | ---: | ---: | ---: |
| Current | 170 (+15) | 33 (+1) | 5 (+0) |
| Nowy | 243 (+88) | 49 (+17) | 5 (+0) |

Te liczby nie uwzględniają nieznanego przyszłego powodzenia API. Nie stosujemy
fikcyjnej średniej skuteczności ani nie oznaczamy planu jako zebranego dowodu.

## Retry, budżet i brak duplikatów

- PitchAPI **0.1.6 ma domyślne `max_retries=2`**. Poprzedni licznik owijał
  wywołanie SDK i nie widział tych prób. Trzy historyczne CLI ustawiają teraz
  `max_retries=0`; capture/recheck odrzucają SDK z włączonym ukrytym retry
  przed pierwszą siecią. M0 i jego klienci nie są zmieniane.
- Wspólny budżet wykonuje najwyżej jedno jawne ponowienie transportu,
  z krótkim opóźnieniem i rezerwą na wszystkie dalsze źródła. Respektuje
  krótkie `retry_after`; dłuższe od 2s odracza. Błędy autoryzacji/pozostałe
  4xx poza 429 nie są ponawiane. Stan długiego rate limit nie jest trwałą
  kolejką z terminem — taki scheduler może być osobnym usprawnieniem.
- Limit **150/paczkę, 48 meczów, 5 paczek**, osobny dotychczasowy recheck
  **115** i 16 MiB raw na szyfrogram pozostają. Rezerwa działa także w recheck.
  Test SDK na mockowanym HTTP potwierdza równość prób HTTP i licznika.
- Sukces konkretnego zasobu jest memoizowany w paczce: ponowne odwołanie nie
  tworzy drugiego receipt. Błędna próba bez odpowiedzi nie staje się dowodem.
  Już użyty `run_token` blokowany jest przed API, również po zmianie dnia.
- Po wyczerpaniu retry brak shots nie zamyka połowy pary jako immutable
  observation. Odebrane stats pozostają w zaszyfrowanym archiwum; mecz jest
  kwalifikowany do kolejnej paczki. Driver nie przerywa po zerze sukcesów,
  jeśli rzeczywiście wybrano źródła do ponowienia. Nadal najwyżej pięć paczek.
- Recheck z transportowo niepełną parą nie zapisuje terminalnego issue,
  który blokowałby przyszłe pobranie. Prawdziwe utrzymujące się rozbieżności
  oraz stare immutable issue records nie są kasowane ani ponawiane bez końca.
- Potwierdzony błąd pustego pierwszego poboru: brak `targets_checked` w
  agregacie powodował KeyError. Raport poprawnie podaje zero, bez fikcyjnych
  cech. Odczyt `existing_ids` nie wykonuje już DDL na oryginalnej bazie.

Nie zmieniono `native_xg_verified`, parserów natywnych statystyk/strzałów,
RSA/AES, tolerancji xG, protokołu receiptów ani źródłowego PASS. Problemy
semantyczne i dawne niepełne issue records pozostają do CODEX-01 / osobnej
audytowalnej rewizji. Nie ma automatycznego wznowienia transakcji publikacji
po przerwaniu procesu między archiwum a podmianą SQLite: istniejący token
blokuje powtórzenie, a osierocone archiwum wymaga osobnej kontroli. To nie jest
pełne zamknięcie R1–R5.

## Testy i odtworzenie

- Końcowo **1207/1207 PASS**, 0 errors/failures/skips na Pythonie **3.11.17**
  oraz **3.12.14**, w tym **27 nowych**. Zestawy liczone po unikalnych ID.
  Blokada sieci, realnego fit oraz zapisów do oryginalnych data/models/config;
  SQLite read-only. Wyjątki fit dotyczą tylko trzech nazwanych starych demo
  syntetycznych. Nie wykonywano rzeczywistego treningu.
- Testy obejmują wspólne zestawy braków obu drużyn, prawdziwe last N,
  sezony, home/away, identyczne kickoff i +3h, zero xG vs brak, niejawny
  dostęp do przyszłych statusów, równoważność starego default, rotację lig,
  limit 150 wraz z retry i rezerwą, realny SDK przez MockTransport,
  odrzucenie ukrytych retry, timeout obu shots, późniejszy udany zapis,
  SHA bazy, blokadę powtórnego tokenu, szyfrowanie i błąd seal bez publikacji.
  Fikcyjne receipt'y mają w testach jawny origin `SYNTHETIC_TEST` i są usuwane
  wraz z katalogiem tymczasowym; nie są dowodem skuteczności selektora.
- Niezależny weryfikator standardowej biblioteki, bez importowania selektorów:
  **55** kontroli liczników przez prosty przegląd poprzedników, 240 rzeczywistych
  kandydatów, **480 wpisów ID** dwóch planów, źródłowe SHA bez zmian: **PASS**.
- Ślad nieudanych prób: pierwszy replay błędnie wymagał zużycia wszystkich
  240 rekordów w pięciu paczkach obu metod; ujawnił niedopełnienie baseline.
  Poprawiono tylko kontrolę/metodę wyrównania kosztu, bez zmiany rankingu.
  Pierwszy test integracyjny wykrył błędne przekazanie datetime do istniejącej
  funkcji oczekującej string i błąd pustego agregatu; oba poprawiono przed PASS.

```bash
# Brak API, brak fit, oryginał SQLite otwierany tylko mode=ro:
python -m scripts.history_selector_ab --out /tmp/history-ab-new.json.gz
python scripts/verify_history_selector_ab.py \
  --report docs/audits/HISTORY_SELECTOR_AB_2026-11-03.json.gz
python scripts/test_history_selector_offline.py
```

Nowy selektor jest dostępny przez `--selector window-yield` w historycznych
CLI i jako jawny wybór workflow_dispatch; domyślnie i w schedule: `current`.
W tej pracy nie uruchomiono żadnego capture/dispatch live i nie użyto sekretów.

## Przed integracją i kontrolowanym live

1. Ponownie porównać z najnowszym main i odebrać źródła CODEX-01, zwłaszcza
   counts/okresy/atomowość. Przeliczyć raport po zmianie kryteriów źródłowych.
2. Przejrzeć osobno zmiany retry i selektor, potwierdzić CI; pozostawić current
   do świadomego wyboru nowej opcji. Bez automatycznego merge.
3. W kontrolowanym, późniejszym poborze ocenić rzeczywiste nowe źródła,
   odrzucenia, opóźnienia i fizyczne wywołania; zestawić wynik na stałej
   populacji celów, z jednakowym kosztem i bez podglądu nieznanych statusów.
4. Sprawdzić, czy korzyść xG5 utrzymuje się poza zapisaną pulą i czy rosną
   xG10/15 oraz venue. Brak poprawy oznacza pozostawienie current.

**M0, kalibracja, zamrożone prognozy i chroniony TEST bez zmian.** Dane nadal
`HISTORICAL_RECONSTRUCTED_NOT_ORIGINAL_PIT`; GATE16/17 nadal PENDING.
