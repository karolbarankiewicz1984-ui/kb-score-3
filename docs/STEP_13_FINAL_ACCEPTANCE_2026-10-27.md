# KB Score 3.0 — PROTOKÓŁ ODBIORU KROKU 13 (oryginalny zakres)

**Data odbioru:** 27 października 2026 r.  
**Decyzja właściciela projektu:** „Wybierz rozwiązanie 1 z krótką kontrolą z rozwiązania 2”.  
**Decyzja metodologiczna:** KROK 13 **ZALICZONO, wyłącznie jako budowę i testy referencyjnego baseline ELO + Poisson (M0)**. Nie jest to zatwierdzenie modelu produkcyjnego, certyfikat danych historycznych PIT ani dowód opłacalności bukmacherskiej. Harmonogram nie zmieniony: 29 kroków, ukończonych 13, krok 14 otwarty tylko do bezpiecznego przygotowania.

## Kryteria bez zmiany ich pierwotnego brzmienia

| Oryginalne kryterium z PLAN.md | Dowód i interpretacja odbioru |
|---|---|
| Silnik prawdopodobieństw 1X2 i goli | [M0 ELO + Poisson](../src/kb3_step13_baseline.py), [audyt matematyczny](../data/audits/STEP13_MATH_INDEPENDENT_2026-10-27.json); PASS |
| P(1)+P(X)+P(2)=1 | 25 par sztucznych Elo i 10 zapamiętanych rzeczywistych prematch P ponownie wyliczonych: błąd numeryczny < 1e-12, [testy](../tests/test_step13_math_independent_audit.py); PASS |
| Brak kursów jako danych wejściowych | [Audyt ścieżek wejścia](../data/audits/STEP13_LEAKAGE_INDEPENDENT_2026-10-27.json), kod M0 i testy odrzucające nieznane pola; PASS w badanym zakresie |
| Wzorcowe przykłady i test historyczny | [Syntetyczne referencje](../data/audits/STEP13_M0_REFERENCE_2026-10-26.json) PASS; [prawdziwa retrospektywna analiza](../data/audits/STEP13_REAL_RETROSPECTIVE_PITCHAPI_2026-10-27.json) na 760 TRAIN + 380 VALIDATION, 4 foldy (60,126,123,71); **PASS z jawną kwalifikacją: reconstructed event-time, nie prawdziwy historyczny PIT** |
| Brier, log loss, kalibracja, wersja danych, uruchomienie testów | [Dane i metryki odzwierciedlone w niezależnym raporcie odbioru](../data/audits/STEP13_ORIGINAL_BASELINE_ACCEPTANCE_2026-10-27.json), raport ze źródłowym SHA, [GitHub Actions odbioru #40472267733](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40472267733) PASS |

## Rzeczywiste wyniki z walidacji historycznej (uczciwie retrospektywnej)

| Metryka | EXPANDING | ROLLING_24_CALENDAR_MONTHS |
|---|---:|---:|
| multiclass log loss 1X2 | 1.0326367404 | 1.0343803886 |
| multiclass Brier sum3 1X2 | 0.6185368951 | 0.6196881659 |
| top-class 5-bin ECE ważone osobno z 4 foldów | 0.0739533904 | 0.0733160087 |
| liczba wyników VALIDATION | 380 | 380 |

Testy na rzeczywistych wynikach zostały odtworzone retrospektywnie na danych pobranych w październiku 2026 r. **Nie wolno** nazywać ich PIT z lat 2023–2026. Osobny [sparowany bootstrap](../data/audits/STEP13_REAL_PAIRED_UNCERTAINTY_2026-10-27.json) pokazuje, że 95% interwały różnicy obu metod obejmują 0. [Kontrola stabilności](../data/audits/STEP13_REAL_RETROSPECTIVE_STABILITY_2026-10-27.json) wykrywa zbyt pewne wskazania w I kwartale 2026; wpływ Elo dotyka górnej krawędzi testowanej siatki. Dlatego **nie ma zatwierdzonego mistrza**.

Matematyczna prognoza losowa o równych szansach 1/3 na każdą klasę miałaby log loss ln(3)=1.0986122887 oraz Brier sum3=2/3; to wyłącznie orientacyjna stała odniesienia, a **nie niezależny model wytrenowany na tych danych**.

## Jawne blokady, których ta decyzja nie uchyla

- **Nie zmieniono** starego podpisanego archiwum, raportów ani ich flag `gate13_pass=false`, `training_allowed=false`; są historycznie prawdziwymi deklaracjami określonych badań. Nowy [protokół](../data/audits/STEP13_ORIGINAL_BASELINE_ACCEPTANCE_2026-10-27.json) ustanawia **wyłącznie odbiór zakresu kroku**, bez wstecznego fałszowania raportów.
- Realne źródła z dawnych sezonów nie posiadają niezależnej certyfikacji dostępności przed każdym dawnym meczem. **Brak zgody na trenowanie modelu produkcyjnego na tych niezweryfikowanych historycznych danych**, mimo formalnego zamknięcia etapu M0.
- Dwie grupy po 10 prawdziwych prognoz przedmeczowych są zachowane bez zmian, brak znanych rzeczywistych wyników przyszłych meczów. Ich późniejsza ocena jest **dodatkowym eksperymentem jakościowym**, nie warunkiem pierwotnego odbioru kroku 13.
- **Żadnego doboru parametrów** na VALIDATION/TEST, niedopuszczalne kursy, automatyczne obstawianie, promocja championa i komercyjna produkcja nie zostały zatwierdzone.

## Wynik formalny

**GATE13_ORIGINAL_SCOPE: PASS — KROK13 ZALICZONO (27.10.2026); postęp 13/29.**

**Rozdzielne statusy:** `historical_pit_certified=false`; `training_allowed=false`; `production_eligible=false`; `model_champion_selected=false`. Dane historyczne do przyszłego CatBoost pozostają wymagającą odrębnego udokumentowania blokadą. W przyszłości badań PIT i rozliczeń 10+10 można dokonywać jako kontynuacji audytu jakości, ale nie blokują one formalnego przejścia do kroków zdefiniowanych w pierwotnym planie.

**Krok 14 — otwarty do prac projektowych (27.10.2026), bez rzeczywistego treningu na niedopuszczonych danych.** [Karta startowa](STEP_14_KICKOFF.md).

**Podpis kontroli:** [niezależny raport agregatowy](../data/audits/STEP13_ORIGINAL_BASELINE_ACCEPTANCE_2026-10-27.json), SHA256 `a4d26dc96bf75bf2073007e66c4445f61adcaed22611f5fa21c31d74a36e4718`; testy bez pobierania nowych danych sportowych.
