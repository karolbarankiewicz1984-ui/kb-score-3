# KB Score 3.0 — kontrola rzeczywistego uruchomienia M0 720-TRAIN / 8 lig

**Data sprawdzenia: 2026-10-30 (Europe/Warsaw), KROK 16 — GATE16 PENDING, 15/29.**

## Zlecenie i stan zastany

Właściciel zlecił uruchomienie równoległego, **odrębnego badawczego** M0 dopasowanego na 720 TRAIN we wszystkich ośmiu dopuszczonych ligach, wraz z wpisem do rejestru zmian. Przed scaleniem jakiejkolwiek nowej implementacji odkryto, że **istniejący main już realizuje dokładnie to zlecenie**. Aby zapobiec podwójnemu poborowi, prognozowaniu tego samego meczu przez dwa kolektory i rozdzieleniu populacji 100+50, nie scalono nowo szkicowanej implementacji alternatywnej.

**Obowiązujący, jedyny strumień:** `src/kb3_step16_m0_720_eight_forward.py` + `scripts/step16_m0_720_eight_run.py` + `.github/workflows/kb3-step16-m0-720-eight-forward.yml`.

- Model `M0_ELO_POISSON_RESEARCH_720TRAIN_V1`, zamrożone parametry SHA256: `55310f0e1dd3842e6d876069ef21b1380901b3a6cc6884cf6ec6ea351a5812d1`.
- Ligi: ESP LaLiga, ITA Serie A, GER Bundesliga, FRA Ligue 1, NED Eredivisie, BEL Pro League, TUR Süper Lig i POL Ekstraklasa.
- Własna append-only baza `data/forward_m0_720_eight/kb3_forward_eight.sqlite`, własne raporty i szyfrowane źródła; dotychczasowy 3-ligowy M0 SHADOW nie jest zastępowany.
- Harmonogram oryginalny: forecast 06:21 UTC; settlement 08:17 i 22:17 UTC. Pułapy na przebieg: 17 zapytań poboru i 9 zapytań rozliczania, **nie nowy klucz ani płatny pakiet**.
- Próg do kandydata kalibracji: 100 różnych, później rozliczonych i serwerowo poświadczonych prognoz niezmiennej wersji, a później 50 niezależnych prognoz, utworzonych po fit T. Brak automatycznego awansu do Championa.

## Weryfikacja rzeczywista

- [GitHub Actions #40943149804 — SUCCESS, 29.10.2026](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40943149804) — autentycznie wywołano 17 zapytań PitchAPI i zamrożono **73 niezależne prognozy**. Rozkład: ESP 9, ITA 10, GER 9, FRA 9, NED 9, BEL 9, TUR 9, POL 9. [Archiwalny receipt](../data/pit_sidecar/m0_720_eight/2026-10-29/forecast/RECEIPT.json), `report_sha256=3ec7866afb509ff28279e46f1b00639bfce03b16a457acfb7a04e4c69938a54b`.
- [GitHub Actions #40952265632 — SUCCESS, 29.10.2026](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40952265632) — **73/73** historycznych prognoz poświadczono autentycznym, serwerowo datowanym artefaktem Actions, przed ich kickoff, zachowując minimum 90 minut. W tym samym ostatnim poświadczonym rozliczeniu **0 zakończonych meczów**, `eligible_settled_unique=0`, `missing_to_fit=100`.
- [GitHub Actions #40989084598 — FAILURE, 30.10.2026, 01:59:58 UTC](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40989084598) — pierwsze nieudane zaplanowane wywołanie; job `anti-leakage-and-data-safety` failure, job realnego M0 skipped.
- [GitHub Actions #41059563977 — FAILURE, 30.10.2026, 12:59:38 UTC](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/41059563977) — ponownie nieudane zaplanowane wywołanie, z tym samym stanem. **Wykonano ponowienie tylko nieudanych zadań (attempt 2, 14:50 UTC) i ono również zakończyło się failure; zadanie danych ponownie zostało pominięte.** Metadane GitHub jobs pokazały brak uruchomionych kroków (`steps=null`), brak dostępnego logu joba (404 `BlobNotFound`). To **nie jest dowód** błędu formuły M0 ani poprawnego pobrania danych; wskazuje na blokadę wykonania zanim wystartował runner. Możliwy limit/billing GitHub Actions wymaga osobnego potwierdzenia w ustawieniach konta. Nie wpisywać PASS ani diagnozy rozliczeniowej jako faktu.
- W `main` podczas weryfikacji **nie znaleziono** `data/forecasts/m0_720_eight/2026-10-30/FROZEN_M0_720_EIGHT.json`; **nie wolno zwiększać** liczby poświadczonych 73 bez nowego rzeczywistego pliku.

## Decyzja o zmianach

**Kontynuować już uruchomiony strumień** zamiast tworzyć duplikat M0. Żadnej zmiany parametrów 720-TRAIN, kluczy, budżetów, podstawowego M0 SHADOW, chronionego Premier League TEST 2026/27, progów 100+50 ani modeli KROKU 17. Wpis do rejestru jest nową kontrolą stanu i ryzyka działania GitHub Actions, a nie nową próbką forecast ani wdrożeniem produkcyjnym.

**Następny warunek:** przywrócić realne wykonywanie GitHub-hosted Actions, sprawdzić limit i billing; odnotować nowy SUCCESS `forecast` lub `settle`, odczytać liczniki SQLite, hash i potwierdzenie czasu publikacji i dopiero wtedy zadeklarować nowy postęp. Przy braku działania runnera nie można wiarygodnie uzupełnić pominiętych przedmeczowych prognoz wstecznie. Formalnie `GATE16 PENDING`, `GATE17 PENDING` i **15/29**.


## Uzupełnienie: źródłowy dowód limitu GitHub Actions

Odczytana wiadomość GitHub z **29.10.2026, 22:13:41 UTC**, temat `[GitHub] You have used 100% of the Actions minutes included for the karolbarankiewicz1984-ui account`, potwierdza **3 000 / 3 000** minut w bieżącym okresie rozliczeniowym oraz wskazuje **reset na 1 listopada 2026 r.** Wiadomość wyjaśnia, że po darmowej puli rozliczenie zależy od ustawionego budżetu, a budżet Actions `$0` blokuje dalsze płatne użycie do resetu. Stan konkretnego budżetu `$0` nie był na potrzeby tego wpisu ponownie odczytany; nie należy go podawać jako zweryfikowany.

**Wniosek operacyjny:** jednoczesny brak startu jobów z 30.10 oraz zużycie 100% minut wskazują na brak dostępnego limitu Actions, a nie potwierdzoną usterkę matematyki modelu. Nie kupowano dodatkowych minut i nie odblokowywano płatnego usage. Pierwszy zaplanowany przebieg po resecie 1.11.2026 wymaga sprawdzenia realnego `SUCCESS` i nowego receipt; **bez dopisywania wyników wstecz**. Dotychczasowy M0 720-TRAIN nadal jest skonfigurowany, lecz po nieudanym wykonaniu 30.10 nie jest aktualnie potwierdzony jako pracujący codziennie.
