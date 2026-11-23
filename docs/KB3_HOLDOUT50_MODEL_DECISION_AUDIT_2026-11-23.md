# KB Score 3.0 — 23.11.2026: HOLDOUT50, analiza lig i oryginalny PIT

**Status:** RESEARCH ONLY. Bez zmiany M0, prognoz, FIT/HOLDOUT, źródeł, chronionego TEST i Championa.

## Dane wejściowe zweryfikowane 23.11.2026

- [Rzeczywisty receipt M0](../data/pit_sidecar/m0_720_eight/2026-11-23/settle-024730964942/RECEIPT.json): **268** host-proof prognoz przedmeczowych, **208** prawidłowo rozliczonych, **60** nierozliczonych, w tym bieżący przyrost 20.
- Kalibracja: pierwszy niezmienny **FIT 100/100**, badawcza temperatura **0.7**. **61** nowych kwalifikowanych wyników po dacie dopasowania (próg 50 przekroczony). Utworzono pierwszy niezmienny przegląd 50 HOLDOUT. Produkcja niezatwierdzona; GATE16 nadal PENDING. Uwaga: flaga zewnętrzna 50_future_after_fit_verified w receipt wciąż ma false; liczbę i istnienie HOLDOUT sprawdzać w tabelach szczegółowych, bez fabrykowania zamknięcia bramki.
- M0 208 meczów: **57.21%** top1 1X2, Brier sum3 **0.574133**, log loss **0.966563**, top1 ECE10 **0.120839**. Nie są to kursy ani ROI.
- Porównanie na dokładnie **135 tych samych host-attested spotkaniach**: M0 top1 56.30%, Brier 0.579740, LL 0.975656; Elo-only top1 55.56%, Brier 0.571945, LL 0.962666; CatBoost no-xG top1 58.52%, Brier 0.576960, LL 0.974073. Jedynie **2** bloki tygodniowe i brak wyznaczonych CI95 — formalnie nie wolno wskazać zwycięzcy.
- Osobny Shadow Six: 84 pary; M0 Brier 0.571056 i LL 0.961987; Shadow Brier 0.596419 i LL 1.000901. Wyższa trafność top1 Shadow nie wystarcza, bo jakość prawdopodobieństw gorsza.
- Podział M0 na ligi (n na ligę 18–29, duża niepewność): BEL 53.6%, ESP 62.1%, FRA 48.0%, GER 63.0%, ITA 58.6%, NED 51.9%, POL 52.0%, TUR 72.2%. Nie optymalizować progów na tak małych próbach.

## A. Niezależna weryfikacja HOLDOUT

Dodano [samodzielny audyt read-only](../scripts/kb3_review_postfit_readonly.py) i [workflow tygodniowy](../.github/workflows/kb3-holdout50-weekly-research.yml).

Skrypt otwiera SQLite tylko do odczytu, sprawdza integralność i SHA256 niezmiennego FIT oraz HOLDOUT. Wymaga dokładnie 100 FIT, 50 rozłącznych HOLDOUT, serwerowego dowodu publikacji co najmniej 90 minut przed kickoff i opóźnionych rezultatów; nowe prognozy HOLDOUT muszą powstać po momencie dopasowania. Przelicza od zera log loss i Brier bez oraz z **zamrożoną** temperaturą 0.7 i sprawdza zgodność z oryginalną tabelą holdout_reviews. Każda rozbieżność oznacza FAIL. Osobno oblicza wyniki M0 według lig i pasm top1 1X2, liczności i średnich deklarowanych prawdopodobieństw. Nie używa rynków skorelowanych jako niezależnych meczów.

**Kryterium PASS A:** rzeczywisty sukces self-test i real-data audit GitHub Actions, autentyczne metryki 50 HOLDOUT i brak naruszenia integralności. Sam kod i 50 rekordów nie wystarczają do uznania zadania za zakończone.

## B. Badania i decyzja o modelu

Uruchomienie cotygodniowe oraz ręczne i test PR daje audytowalny JSON, bez commitów wyników do bazy. Porównuje M0, CatBoost no-xG i Elo-only tylko na identycznych rozegranych spotkaniach, nie łączy retrospekcji z forward, raportuje liczbę niezależnych tygodni. Dla CatBoost with-xG nadal wymaga własnych rzeczywistych host-attested par z M0. Rozdzielić top1 od Brier/log loss; nie używać 50 HOLDOUT do optymalizacji progów. Wymagać przedziałów niepewności, zgodności cech treningu i predykcji oraz zgody właściciela przed promocją.

## C. Oryginalna chronologia historycznych danych — NIEZAMKNIĘTA

[Audyt 22.11](../data/audits/STEP14_INDEPENDENT_RECHECK_2026-11-22.json): badawczy zbiór **7568** obserwacji nie dowodzi pełnego oryginalnego PIT 159 pól. Nadal **0/760** certyfikowanych TRAIN i **0/380** VALIDATION. Brak niezależnych dowodów first-publication PitchAPI team-xG oraz pola-w-czasie dla kompletnej zamrożonej macierzy. GATE14 PENDING i oryginalny M1 bez formalnej zgody na fit.

Do odbioru potrzeba dla każdego rekordu i pola: oryginalnych wersji/bajtów i SHA, źródłowego ID, serwerowego zegara publikacji przed kickoff, definicji, mapowania drużyny/meczu i missingness oraz niezależnego testu 159 pól i chronologii 760/380. Braki opcjonalne pozostają oznaczone jako braki, nie zera i nie blokują odrębnych eksperymentów forward.

**Ograniczenia:** GATE14/16/17 PENDING, bez dostępu do chronionego ENG TEST, brak zatwierdzenia produkcyjnego, brak automatycznego Championa i nowych opłat. Skrypt oraz workflow mają najpierw wykazać realny PASS w CI.