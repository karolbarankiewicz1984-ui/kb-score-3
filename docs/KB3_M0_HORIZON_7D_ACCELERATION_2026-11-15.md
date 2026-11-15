# KB Score 3.0 — przyspieszenie nowej puli przedmeczowej M0, 15.11.2026

## Dlaczego przestały przyrastać prognozy

Oryginalny, rzeczywisty [M0 run #43722430224](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/43722430224), godz. 14:07 UTC, wykonał 17 istniejących zapytań PitchAPI, ale **new_forecasts=0, total_forecasts=149**. Źródło `data/pit_sidecar/m0_720_eight/2026-11-15/forecast-140659244929/RECEIPT.json`, pole `forecast_selection_diagnostics`: zdarzenia klubowe 20–22.11 były bezwarunkowo oznaczane `OUTSIDE_96H`, mimo że ich rozkład był już widoczny w oryginalnym terminarzu. Ma to związek z przerwą reprezentacyjną i dotychczasowym `HORIZON=timedelta(hours=96)`.

**Nie** był to błąd API ani powód do ponownego trenowania M0.

W przedziale od 96h do 168h liczonych od oryginalnego cutoff 2026-11-15T14:07:02Z znaleziono **55 przyszłych pozycji terminarza** na już pobranych danych: ESP=6, ITA=7, GER=7, FRA=7, NED=8, BEL=6, TUR=7, POL=7. Ocenę przeprowadzono bez nowych requestów. Te 55 to potencjalne kandydatury; **nie** 55 sprawdzonych modeli/prognoz. Dalsze warunki form5, identyfikatorów, dostępności i czasu mogą wyeliminować część.

## Wdrożenie

[PR #178](https://github.com/karolbarankiewicz1984-ui/kb-score-3/pull/178) **MERGED** (squash SHA `27da28a95445ed0a3c4c6c9c2741d938ebd071db`), końcowy PR HEAD `2b81b477d8200af97df8278e0b863f7684c06e54`.

- `src/kb3_step16_m0_720_eight_forward.py`: prospektywny horyzont `HORIZON=7 dni`, kontrola `OUTSIDE_7D`, jawna diagnostyka `forecast_horizon_hours=168`. Nie zmieniono matematyki, FIT, identyfikacji lub źródłowych dowodów.
- Minimalne wyprzedzenie przed kickoff nadal **90 minut**, jedna zamrożona prognoza na natywny mecz, maksimum **10 nowych na ligę**, 8 lig bez chronionego Premier League TEST, historyczne ostatnie pięć meczów obowiązkowe. **Ten sam limit 17 zapytań na pełen forecast**; bez nowego API ani podnoszenia limitu 3 prób dziennie.
- `tests/test_step16_m0_720_eight_forward.py`: rzeczywista logika na syntetycznych terminarzach — +5 dni przyjęte, +8 dni odrzucone; brak zmiany modeli i progów.
- `tests/test_m0720_operations.py`: oryginalna granica 90 minut pozostaje kontrolowana, nowa ścisła granica 168h.
- **Nietykalność historycznego dowodu:** `scripts/audit_m0720_operations.py` i workflow operacyjny weryfikują raport z 04.11 na jego **oryginalnym 96h** poprzez `--verify-report ... --historical-horizon-hours 96`. Parametr jest blokowany w nowych audytach bez `--verify-report`; żadne historyczne prognozy ani raport nie zostały przerobione według 7d.

## Realny odbiór i ograniczenia

Dokładnie ten sam końcowy PR HEAD przeszedł wszystkie trzy niezależne [CI M0 Step16 #43753413678](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/43753413678), [CI pełna regresja #43753413635](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/43753413635), [Shadow Six #43753413619](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/43753413619): **3× SUCCESS**.

**Jeszcze NIE potwierdzono realnego `new_forecasts>0` po merge.** Zwykły kodowy `push` nadal zgodnie z ochroną pomija płatne wywołania provider API; następny `schedule` lub jawny GitHub Actions `workflow_dispatch mode=forecast` musi potwierdzić nowe próbki, ich publikację i serwerowy czas. Do tego czasu oficjalna pula to **149 frozen M0 / 147 settled M0**, nowy po-fit HOLDOUT nadal **0/50**. Po nowym freeze: ocenić host-proof, lidera czasu i podział jakości według rzeczywistego wyprzedzenia 1–4d vs 4–7d; wcześniejsze prognozy mogą być mniej świeże. Nie wolno przypisywać im wyższej skuteczności na podstawie samego horyzontu.

**Formalne bramki pozostają otwarte.** [Recheck PIT z 15.11 o 19:04 UTC](https://github.com/karolbarankiewicz1984-ui/kb-score-3/blob/main/data/audits/STEP14_INDEPENDENT_RECHECK_2026-11-15.json) podtrzymuje 0/760 oryginalnych TRAIN oraz 0/380 VALIDATION i brak niezależnego czasu pierwszej publikacji xG. Nie podmieniać ich dzisiejszym backfillem. Nie promować M1/Championa. Zachować dwa późniejsze konflikty kickoff do rozliczenia wyłącznie po rzeczywistym potwierdzeniu, nie przyspieszać fikcyjnym wynikiem.

## Dalsze priorytety

1. Odczytać **pierwszy realny forecast na nowym kodzie** i odnotować liczbę nowych SHA oraz zarchiwizowany server-proof przed kickoff; jeżeli wynik zero, odczytać powody `reason_counts` (last5, time, id i już zamrożone).
2. Utrzymać settle i audyt rynków; po rozegraniu spotkań sprawdzić nowe rozliczenia oraz ile kwalifikuje się do odrębnego HOLDOUT po kandydacie FIT z 08.11.
3. Zachować przyrost historyczny przez już wdrożony `gain-first`, ale **bez podnoszenia liczby zapytań PitchAPI tylko dla wolumenu**: ostatni backfill #43739366688 wykorzystał 655 historycznych zapytań + 73 recheck i dodał 240 stat-observations, 226 native xG. Zwracać uwagę na niedopokrycie xG5/NED/POL, narzuty i rzeczywisty zysk danych.
4. V3 9 oryginalnych badawczych 87-wektorów na 20–21.11 nie zastępuje formalnego PIT 121+38. Oddzielna ścieżka licencjonowanych, niezależnie datowanych źródeł historycznych oraz bezpieczeństwa publicznych materiałów dostawcy nadal wymaga działań.

**Wniosek:** gotowa poprawka usuwa realną barierę dostępu do meczów po przerwie; nie skraca fizycznego oczekiwania na rozegranie meczów, nie zmienia kalibracji ani nie certyfikuje historii.
