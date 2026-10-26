# KB Score 3.0 — protokół odbioru kroku 11 (oryginalna bramka)

**Data:** 26 października 2026 r.  
**Decyzja:** **GATE11 PASS — zakończono etap inżynierii cech przedmeczowych**, na podstawie pierwotnych kryteriów w `docs/PLAN.md`.  
**Stan projektu po odbiorze:** **11/29 etapów zaliczonych**. Krok 12 — gotowy do rozpoczęcia, **niezaliczony**.  
**Wyłączenia:** `training_allowed=false`; brak produkcyjnych prognoz, kursów, kalibracji lub zakupów.

## Dlaczego bramka może zostać zamknięta już dziś?

Pierwotny zakres kroku 11 nie zakładał dowodu stabilności dostawcy przez wiele dni ani pełnego xG we wszystkich meczach. Dosłownie wymagał:
1. **Każda cecha ma opis i znacznik daty dostępności.** Katalog cech w [STEP_11_FIELD_PROVENANCE_GATE.md](STEP_11_FIELD_PROVENANCE_GATE.md); w `src/kb3_features.py` i `src/kb3_step11_field_audit.py` tryb `observed` tworzy wpis `feature_availability` **dla każdego** `features[*]` i `missing_flags[*]`, ze źródłem, zachowawczym czasem obserwacji i SHA wejścia.
2. **Test odcina przyszły mecz i wykazuje brak przecieku.** `validate_observed_rows` oraz testy `tests/test_step11_field_availability.py` i `tests/test_step11_original_acceptance.py` odrzucają wynik meczu docelowego, mecze przyszłe lub niedokończone, wynik/strzały pobrane po `cutoff`, późniejsze zatwierdzenie xG, niejednoznaczne zegary i źródło późniejsze niż cutoff. Dla zaobserwowanych danych działa `source_observed_at <= feature_cutoff < kickoff`. Nie korzystamy z późniejszego wyniku w cechach przedmeczowych.
3. **Brak xG nie staje się fikcyjną wartością.** `xg_avg=null` i `xg_n=0`, odpowiadający `missing_flags= true` gdy nie ma źródła. Wartości xG są używane wyłącznie ze źródła z prawidłowym natywnym match/team ID, z czasem przed cutoff.

**Dowód regresji:** [GitHub Actions #40339012432](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40339012432) **246/246 PASS** (207 testów kroku 11 + 9 dodatkowych testów PIT + 10 testów przechwytywania danych + 20 testów wcześniejszych etapów). Nowe pięć testów bada **oryginalne trzy kryteria bramki** i utrzymanie blokady treningu. Job pobierania danych sieciowych był **SKIPPED**, nie kosztował nowych zapytań API. Pełny model nie był trenowany.

## Zakres udowodniony dodatkowymi próbami

- Jedno główne źródło sportowe **PitchAPI** z natywnymi identyfikatorami meczów i drużyn, bez obowiązkowego crosswalk do API-Football.
- Prospektywne obliczenia wielosezonowego ELO z 1140 zakończonych wyników PL 2023/24–2025/26 oraz 80 z bieżącego sezonu, z 17 stabilnymi team IDs między sezonami; parametry ELO pozostają **prowizoryczne, a nie skalibrowane**. [Audyt](STEP_11_PITCH_MULTISEASON_ELO.md).
- Premier League, Liga Europy i Liga Konferencji: w późniejszej próbce **30/30** kompletnych xG; po odjęciu powtórek z wcześniejszych prób UEFA, **38 różnych meczów** z kompletnymi obserwacjami. Próbka nie jest losowa i **nie** poświadcza xG dla wszystkich meczów. [Audyt](STEP_11_THREE_LEAGUES_XG30_COVERAGE.md).
- Nienadpisywalne, zaszyfrowane zapisy obserwacji i źródłowe hashe, odtwarzane niezależnie z Google Drive; prospektywne zegary obserwacji, nie fikcyjne znaczniki wcześniejszej publikacji.
- Dwa autentyczne odczyty PL 2026/27 tego samego dnia nie wykazały zmian w 380 terminarzowych rekordach. Jest to dowód **tylko dla sprawdzonego przedziału**, nie zapewnienie stabilności przez kolejne dni. [Audyt](STEP_11_NATIVE_SECOND_REAL_CAPTURE.md).

## Otwarte kontrole — nie wstrzymują GATE11

1. **Dane między różnymi dniami**: obserwować źródło PitchAPI prospektywnie, porównywać rzeczywiste zmiany, nie tworzyć sztucznych historycznych timestampów. Kontrola jakości danych do kolejnych etapów.
2. **Kompletność xG poza audytowanymi próbkami**: zbierać obserwacje wraz z nowymi spotkaniami, odrzucać niepełne feedy lub zachowywać `null`. Nie trzeba wymagać 100% xG do odbioru modułu cech.
3. **Oryginalne czasy publikacji historycznych danych nieznane**: źródła lat 2023–2025 pobrane 26.10.2026 są RETROSPECTIVE, nie historycznym prematch PIT. **Nie wolno** przeprowadzić na nich pozornie chronologicznego backtestu wcześniejszych prognoz. To obowiązkowa kontrola przy tworzeniu zbiorów TRAIN/VALIDATION/TEST w kroku 12.
4. **Brak zgody na trening/produkcję**: GATE11 PASS **nie jest** GATE12, nie uruchamia treningu ani rekomendacji bukmacherskich.

## Decyzja przejścia

**ZAMYKAMY KROK 11 zgodnie z pierwotnym kontraktem.** Przestajemy dokładać coraz nowsze testy xG jako warunek tego etapu. Następna praca: **krok 12 — rozdzielenie TRAIN / VALIDATION / TEST z zamrożonym manifestem, blokadą przecieków i uczciwą klasyfikacją RETROSPECTIVE vs OBSERVED_AT**. Rozpoczęcie planowania podziału jest dozwolone; **uruchomienie treningu nadal nie**.

Ten protokół dokumentuje *techniczny odbiór według wymagań repozytorium*, nie akceptację przez właściciela jakichkolwiek wydatków czy produkcyjnego uruchomienia.

**GATE11: PASS • completed_steps: 11/29 • training_allowed: false.**
