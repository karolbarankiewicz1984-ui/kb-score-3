# KB Score 3.0 — Krok 14: audyt matematyki CatBoost M1, wariant bez xG / z xG oraz protokół kalibracji po prognozach

**Data:** 27.10.2026. **Formalnie:** 13/29 kroków; GATE14 PENDING; oficjalny historyczny PIT TRAIN 0/760 i VALIDATION 0/380; żadnego produkcyjnego M1. **Matematyka i obie konfiguracje modelu przetestowane rzeczywiście na SZYBKO GENEROWANYCH FIKCYJNYCH danych**, nigdy na właściwym TRAIN/TEST.

## Zakres i dane

Dwa warianty CatBoostClassifier CPU 1.2.8, `loss_function="MultiClass"`, seed 141027, 36 iteracji, depth 3, learning rate 0.08, single thread, bez zapisu modelu produkcyjnego:
- **BEZ_XG**: Elo gospodarze minus goście; forma punktowa 5 meczów gospodarzy i gości (**3 cechy**).
- **Z_XG**: dokładnie te same 3 plus średnia xG gospodarzy i gości oraz 2 maski brakujących wartości (**7 cech**). Syntetyczny `null` xG przechodzi jako NaN do CatBoost, a nie jako wartość 0. Maska missing jest osobną cechą. Ta demonstracja nie odzwierciedla jeszcze rzeczywistego przypadku częściowego xG z kontraktu Step11.

**W obu wariantach identyczne** chronologicznie rozdzielone 90 fikcyjnych TRAIN i 30 fikcyjnych VALIDATION, identyczne etykiety 1/X/2 i identyczne daty zdarzeń. Brak odds i testu 2026/27, brak płatnych API. Warianty porównujemy **parami na tych samych 30**. Walidacja dodatkowo wydzielona w kolejności czasu na **pierwszych 15 do dobrania temperatury** i **ostatnich 15 tylko do oceny po doborze**.

## Rzeczywiste wyniki uruchomionego technicznego eksperymentu na DANYCH SYNTETYCZNYCH

| Wskaźnik | BEZ xG (3 cechy) | Z xG + missing (7 cech) |
| --- | ---: | ---: |
| Log loss na identycznych 30 syntetycznych meczach | **0,986583** | **0,825654** |
| Wieloklasowy Brier **sum3** na tych samych 30 | **0,596817** | **0,474751** |
| Top-1 accuracy (30) | **50%** | **60%** |
| Top-1 ECE / 10 binów (30) | **0,250242** | **0,192567** |
| T dobrane WYŁĄCZNIE na wcześniejszych 15 | **0,70** | **0,70** |
| Log loss późniejszych 15 — przed kalibracją | **1,023813** | **0,833461** |
| Log loss późniejszych 15 — po kalibracji | **1,010868** | **0,783386** |
| Brier sum3 późniejszych 15 — przed kalibracją | **0,622245** | **0,480276** |
| Brier sum3 późniejszych 15 — po kalibracji | **0,616723** | **0,452543** |

W dodatkowym sparowanym porównaniu późniejszych 15 przykładów `Z_XG - BEZ_XG`: **różnica log loss = -0,190351** (11 z 15 przykładów indywidualnie lepszych dla z xG, cztery gorsze); **różnica Brier sum3 = -0,141968**. Te liczby są **wyłącznie syntetyczne, statystycznie niereprezentatywne i nie stanowią oszacowania realnej przewagi xG ani dowodu skuteczności bukmacherskiej**. Descriptive bootstrap na wymyślonych meczach nie ma wartości jako rzeczywisty przedział ufności przewagi modelu. Nie wybieramy na tej podstawie Championa.

Dla porównania w izolowanym eksperymencie BADAWCZYM na 760 rzeczywistych RETROSPEKTYWNYCH publicznych wynikach OpenFootball i 380 retrospektywnych VALIDATION w [PR #49](https://github.com/karolbarankiewicz1984-ui/kb-score-3/pull/49) wariant bez xG miał log loss **1,03921945**, Brier sum3 **0,62628833**, accuracy **50%**. Jest to **inne źródło danych i inny model bez PIT**, więc nie wolno jego liczb porównywać z syntetycznym Z_XG, wnioskować z tego o rzeczywistej korzyści xG lub oznaczać wyniku jako oficjalny M1.

[Pełny maszynowy raport eksperymentu — WYŁĄCZNIE SYNTETYCZNY](../data/audits/STEP14_SYNTHETIC_M1_NOXG_XG_CALIBRATION_2026-10-27.json). Kod [matematyki](../src/kb3_step14_m1_math_calibration.py) i [dwuwariantowego eksperymentu](../src/kb3_step14_m1_xg_comparison.py).

## Niezależna matematyka 1/X/2 i zakres testów

- Jedyna autoryzowana kolejność klas w raportach i wektorach `("1","X","2")`. Każdy wynik `CatBoost.classes_` jest **jawnie mapowany** do tej kolejności, nie sortowany alfabetycznie.
- Prawdopodobieństwa dla wszystkich 3 klas są skończone, nieujemne, ≤1 i sumują się do 1 z tolerancją 1e-8; nie można dołączyć czwartej klasy / kursów / wyników.
- **Log loss** = `-ln(P[rzeczywista klasa])`, średnia na identycznych spotkaniach; dolne `EPS=1e-15` tylko dla logarytmu (by nie otrzymać nieskończoności).
- **Brier sum3** = `(P1-I1)^2 + (PX-IX)^2 + (P2-I2)^2`, średnia (bez dodatkowego dzielenia przez trzy). Dla perfekcji 0, za w 100% błędną, pewną prognozę 2.
- **Top-1 reliability**: 10 binów z licznością, średnim P maksimum i udziałem trafień; ECE jest średnią ważoną liczebnością. Temperatury zmieniają pewność, ale przy T>0 nie zmieniają klasy o największym P, więc **sam hit-rate nie mierzy jakości kalibracji**.
- **Kalibracja temperaturą**: `softmax(log(max(P,EPS))/T)` na dokładnie tej samej zamrożonej kolejności. Stabilny numerycznie softmax z odjęciem maksimum logits. Wśród kandydatów 0,7; 0,85; 1,0; 1,15; 1,4; 1,8; 2,2 wybierany T minimalizujący log loss **wyłącznie wcześniejszych** prognoz z potwierdzonym wynikiem. T=1 oznacza brak zmiany; dobór temperatury nie obejmuje żadnej późniejszej obserwacji. Każdy kandydat wersjonowany osobno na wariant/model.
- Testy negatywne odrzucają podmianę identyfikatora/hasza zamrożonej prognozy, prognozę późniejszą niż kickoff, etykietę wyniku przed spotkaniem lub dostarczoną po dacie cutoff, podwójne rozliczenie, błędną klasę, ujemne/NaN P i brak niezależnej walidacji.

[GitHub Actions #40579198296 — SUCCESS](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40579198296): **16/16** niezależnych testów matematyki i przyszłej kalibracji plus **5/5** testów rzeczywistego CPU CatBoost na fikcyjnych 90+30. Odczyt oryginalnego TEST 0.

## Mechanizm późniejszej rzeczywistej kalibracji po prognozach — przygotowany, NIEWŁĄCZONY

Zgodnie z pierwotnym planem, **nie kalibrujemy prognoz wstecz na podstawie tego samego meczu**. Gdy przyszła wersja KB Score 3.0 zostanie zatwierdzona, jej system powinien:

1. **Przed kickoff** w istniejącej trwałej, zewnętrznej, append-only ewidencji zamrażać: `forecast_id`, `kickoff_utc`, autentyczny serwerowy czas freeze, `model_version`, wariant `NO_XG` / `WITH_XG_MASKS`, dokładne trzy `P(1),P(X),P(2)` i oryginalny SHA dowodu. Nie przepisywać dawnych prognoz po rozliczeniu. Samodzielny SHA w JSON NIE udowadnia rzeczywistego czasu publikacji — potrzebny jest niezależny serwerowy dowód freeze.
2. **Po zakończeniu meczu**, w innym rekordzie powiązanym przez `forecast_id`, zapisywać rzeczywisty `label_1x2` i wiarygodny `settled_at_utc`. Duplikaty i wyniki po żądanym cutoff są odrzucane.
3. Po zgromadzeniu **co najmniej 100** prawdziwych, zamrożonych, zakończonych wyników danego `model_version+variant` *przed* zadanym `calibration_cutoff_utc` można jedynie wyliczyć propozycję skalarnej temperatury.
4. Wykonać niezależną ocenę na **minimum 50** kolejnych, zakończonych prognozach o kickoff nie wcześniejszym niż cutoff — tych etykiet **nie wolno** użyć do doboru T. Każdy mecz, który przekracza granicę wyniku i cutoff (kickoff przed cutoff, wynik po cutoff), przechodzi do **embargo**, nie jest ani w fit, ani w ocenie.
5. Zmiany Brier sum3, log loss, ECE, próbę N oraz wersję i source SHA przedstawiać jako **propozycję do audytu**. **Zero automatycznego wdrożenia:** nawet niższy błąd nie może uruchomić modelu samodzielnie ani zmienić dawnych prognoz. Sprawdzić, czy zachodzi poprawa na wystarczającej liczbie rzeczywistych spotkań, i dopiero potem decyzja o wersji nowego kalibratora. TEST i etap 14 nie otwierają się automatycznie.

Gotowy interfejs czysto matematyczny: `freeze_forecast(...)`, `audit_frozen_settlements(...)`, `prepare_future_calibration_candidate(...)`, `fit_temperature(...)`, `evaluate_calibrated_holdout(...)`. Aktualny kod NIE jest jeszcze zintegrowany z rzeczywistym append-only backendem prognoz. Sam self-hash i podany w ręku `frozen_at_utc` nie są wystarczającym dowodem. Minimum 100/50 to **proponowana bezpieczna zasada operacyjna modułu**, a nie arbitralna modyfikacja dotychczasowej metodologii GATE14.

**Wynik końcowy:** audyt matematyki technicznej i przygotowanie kalibracji można zakończyć, lecz **formalny krok14 NIE**, bo nie istnieje pełen autentyczny TRAIN PIT. Brak prawdziwych porównywalnych xG, brak zatwierdzenia Championa, brak rzeczywistych wytrenowanych produkcyjnych CatBoost M1, bez zmiany M0, TEST i starych zamrożonych prognoz.
