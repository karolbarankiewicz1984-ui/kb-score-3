# KB Score 3.0 — KROK 13 / W REALIZACJI: Baseline ELO + Poisson

**Rozpoczęcie:** 2026-10-26. **Status:** M0 matematyka i testy referencyjne PASS, **GATE13 PENDING** (brak wiarygodnego historycznego testu i metryk). **Postęp projektu:** nadal **12/29 odebranych**; kroku 13 nie uznajemy za ukończony. Nowe koszty zewnętrzne: 0 zł.

## Zakres i definicja M0

- **ELO drużyn:** standardowa oczekiwana punktacja Elo `1/(1+10^((R_away-R_home-65)/400))`, start 1500, K=20; wynik W/D/L aktualizuje obie drużyny o przeciwnych znakach, bez kursów bukmacherskich. **Elo expected points NIE jest prawdopodobieństwem zwycięstwa.**
- **Poisson:** niezależne bramki 90 minut, proste niezfitowane `mu_home=1.45`, `mu_away=1.15`. Prematch Elo różnica modyfikuje stawki `lambda_home=1.45*exp(0.35*(R_home-R_away)/400)`, `lambda_away=1.15*exp(-0.35*(R_home-R_away)/400)`. Przy przewadze gospodarzy zawartej już w średnich bramkowych **nie dodajemy drugi raz +65 Elo do Poissona**; parametr +65 jest tylko dla aktualizacji oceny Elo. Parametry to ilustracja/test — NIE dane wytrenowane na KB3.
- Z jednej macierzy Poissona obliczane są **P(1), P(X), P(2)**, over 1,5 / 2,5 / 3,5, BTTS TAK, pięć najwyżej prawdopodobnych dokładnych wyników. Usuwanie ogona Poissona jest kontrolowane z tolerancją, P(1X2) sumuje się do 1.
- **Bez ingerencji w inne modele:** bez KB2.1, API Market i MultiModel, kursów/odds, tokenów API, danych z przyszłości, dopasowywania parametrów, losowych prognoz historycznych.

## Referencja matematyczna — wymyślone drużyny i niezatwierdzone parametry

| Przykład sztuczny | Elo gospodarzy | Elo gości | P(1) | P(X) | P(2) | Średnie gole H/A |
|---|---:|---:|---:|---:|---:|---|
| Syntetyczna A/B | 1500 | 1500 | 43.98% | 26.04% | 29.98% | 1.450 / 1.150 |
| Syntetyczna C/D | 1600 | 1500 | 49.62% | 25.11% | 25.27% | 1.583 / 1.054 |
| Syntetyczna E/F | 1400 | 1600 | 33.23% | 26.38% | 40.39% | 1.217 / 1.370 |

**Uwaga:** nie są to typy bukmacherskie, prawdopodobieństwa dla realnych drużyn ani dowód trafności. Sztuczne przykłady sprawdzają wyłącznie matematyczną spójność wzorów.

[Zamrożony raport referencyjny, tylko syntetyczny](../data/audits/STEP13_M0_REFERENCE_2026-10-26.json), SHA256 `38e08689a8d7ca81b96c9b4a8fa4ed8c6e75d5eef617f3f421bb839711c989ff`.

## Formuły miar błędu (syntetyczna kontrola, nie historyczna skuteczność)

- **Multi-class log loss:** średnia `-ln(P prawdziwej klasy)`.
- **Multi-class Brier (sum3):** średnia sumy trzech kwadratów `(p_k - y_k)^2`, zakres 0..2, bez dzielenia przez trzy.
- **Kalibracja:** kontrolna top-class ECE na 5 z góry zadanych koszykach; mała próba syntetyczna nie daje wiarygodnej miary kalibracji.
- Raport zawiera matematyczny test tych funkcji na **3 zmyślonych etykietach**. Wartości log loss, Brier i ECE z raportu NIE SĄ wynikami HISTORYCZNYMI; realne Brier/log loss i kalibracja są nadal niedostępne.

## Bramki jakości i co pozostało do zaliczenia

| Kryterium z PLAN.md | Stan |
|---|---|
| Poisson 1X2 sumuje się do 100% | **PASS** — offline testy 1X2 dla różnic ELO |
| Brak kursów jako wejść modelu | **PASS** — jawne wejścia Elo/parametry, testy odrzucenia nieznanych pól |
| Wzorcowe przykłady | **PASS** — trzy jawnie syntetyczne, deterministyczne przykłady |
| Test HISTORYCZNY na wcześniejszych danych | **BLOCKED** — z kroku12 wiemy 0/1520 dopuszczonych próbek PIT |
| Prawdziwe wieloklasowe Brier, log loss, kalibracja historyczna | **PENDING** — niczego nie fabrykowano |
| Odbiór właściciela pierwszych wyników referencyjnych | **PENDING** |

**Dane:** Step12 niezmienny metodologiczny PASS; w realnej bazie 1220 wstecznych rekordów historycznych i 300 terminarzowych, bez pełnego certyfikatu prematch. Nie wolno wstecznie fałszować historycznego `observed_at` ani traktować odczytu pobranego w październiku 2026 jako źródła przedmeczowego z 2023.

**Następny fragment kroku 13:** opracować zasady rzeczywistego odtworzenia statystyk meczowych/rezultatów (retrospective replay) ze ścisłym oznaczeniem różnicy `reconstructed event-time` kontra `verified provider observed-at`, przepuścić je przez niezależne bramki jakości; dopiero potem ustalać parametry na TRAIN, wybierać EXPANDING vs ROLLING na VALIDATION i mierzyć metryki bez podglądania TEST.

## Dowody

- [Silnik bazowy M0](../src/kb3_step13_baseline.py).
- [Formuły miar referencyjnych](../src/kb3_step13_reference_metrics.py).
- [Wersjonowany generator raportu](../src/kb3_step13_reference_report.py).
- [Testy ELO/Poisson](../tests/test_step13_baseline.py) i [metryk](../tests/test_step13_reference_metrics.py).
- [CI Step13 (offline)](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40375744613).

**GATE13: PENDING. training_allowed=false.** Zamrożony raport syntetyczny nie zastępuje prawdziwego testu historycznego.

## 26.10.2026 — Drugi fragment kroku 13: bezpieczny walk-forward ELO (v0.2)

Dodano rzeczywiście wykonujący obliczenia ELO w czasie [silnik kwartalnego replay](../src/kb3_step13_fold_replay.py) — na **wyłącznie sztucznych danych**. W każdej strategii TRAIN zamraża stan na granicy folda i wylicza z tych ratingów niezależne prognozy VALIDATION. Wyniki ze sprawdzanego kwartału trafiają do oceny **po** zapisaniu wszystkich prognoz, nie do uczenia. Wprowadzono 48-godzinne konserwatywne embargo po kickoff oraz warunek rzeczywistego receipt wcześniejszego od cutoff; to jest syntetyczny test bezpieczeństwa, **nie dowód historycznych godzin publikacji w PitchAPI**. Brak choć jednego wyniku blokuje syntetyczne metryki całego folda. TEST i kursy są blokowane.

Zamrożono [realny audyt gotowości samych terminarzy na 1520 ID](../data/audits/STEP13_REAL_FOLD_READINESS_2026-10-26.json), SHA `814b58950a387ec206673203c51a494b1b82a3a199ab1f9b28f77dac4e84e29b`. Walidacja 60/126/123/71, TRAIN-kandydaci EXPANDING 760/820/946/1069 oraz ROLLING 760/753/750/776, ale **każdy fold: 0 certyfikowanych danych do prawdziwego treningu.** Nie czytano żadnych historycznych etykiet ani nie liczono prawdziwych wyników i metryk modelu. Testy [CI PASS](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40377868431) weryfikują w szczególności, że zmiana etykiety meczowej walidacji nie może zmienić zamrożonej prognozy. [Pełny kontrakt rozróżnienia PIT i retrospektywnego replay](STEP_13_REPLAY_CONTRACT.md).

**GATE13 PENDING; postęp 12/29; training_allowed=false.**

## 26.10.2026 — Uzupełniający test wyników dostępnych w trakcie folda (kontrola prequential)

W odróżnieniu od istniejącego `kb3_step13_fold_replay.py`, który na potrzeby **głównego porównania** zamraża ELO na początku każdego kwartału, przygotowano odrębny **syntetyczny wariant badawczy prequential** `src/kb3_step13_replay.py`. Tu każdą prognozę oblicza się na aktualny kickoff, a wyniki poprzednich spotkań można uwzględnić **dopiero po znanym czasie ich otrzymania**. Dzięki temu testujemy kontrolę lookahead również *wewnątrz kwartału*, bez zmiany oficjalnego protokołu porównawczego z kroku12.

14 testów syntetycznych kontroluje: 2 metody okna historii, opóźnione wyniki, identyczne kickoff, zmianę późniejszych etykiet (nie zmienia wcześniejszych P), wykluczenie TEST, kursów, duplikatów i realnych identyfikatorów, odrzucanie wyników poznanych po datach analizy, SHA freeze. [Implementacja](../src/kb3_step13_replay.py), [testy](../tests/test_step13_replay.py), [niezmienny raport wyłącznie demonstracyjny](../data/audits/STEP13_M0_SYNTHETIC_REPLAY_2026-10-26.json), SHA `68849afe0389e994b51e7ee2f55927fe9e875ca69d3e0d9433a3a8f232ec6d2e`, [CI PASS](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40387731556). W przykładzie występują tylko **2 sztuczne wyniki walidacyjne** i 2/1 sztucznych kandydatów do historii; metryki są jedynie testem kodu i nie wskazują skuteczniejszej metody dla rzeczywistej Premier League.

**Rozróżnienie wariantów:** podstawowy zamrożony kwartalny fold = protokół główny. Prequential = niezależny wariant techniczny, potencjalny eksperyment do osobnej przyszłej oceny, a **nie jego zamiennik**. Nie wybieramy go na podstawie syntetycznych wyników. Nadal `GATE13 PENDING`, `training_allowed=false`, **12/29**.

## 26.10.2026 — Trzeci fragment kroku 13: dobór parametrów Poissona na TRAIN (v0.3)

**Wdrożono kod rzeczywistej optymalizacji matematycznej, ale wykonano go dotąd WYŁĄCZNIE na sztucznym TRAIN.** [Moduł](../src/kb3_step13_poisson_train.py) wybiera parametry intensywności bramek gospodarzy i gości z analitycznego maksimum wiarygodności rozkładu Poissona; parametr wrażliwości bramek na różnicę Elo przeszukuje na stałej z góry zadanej siatce 0.0–0.6 ze skokiem 0.1. Minimalizuje całkowity **Poisson negative log-likelihood na TRAIN**, nie na VALIDATION/TEST. Nie optymalizuje jeszcze K=20 ani przewagi domowej ELO=65; te pozostają niezweryfikowanymi ustawieniami początkowymi.

**Źródło treningu:** wyłącznie rekordy syntetyczne z jawnym `source_type=SYNTHETIC_REFERENCE_ONLY`, ID `SYN-MATCH-*`, wynikami 90 minut, godziną kickoff, godziną wcześniejszego odcięcia cech, godziną rzeczywiście deklarowanego otrzymania wyniku i `partition=TRAIN`. Program zatrzymuje się, gdy wynik otrzymano po zamrożeniu folda, cutoff cech wypada po kickoff, etykieta jest błędna, pojawia się VALIDATION/TEST, kurs bukmacherski, dodatkowa kolumna, niezgodny lub zduplikowany identyfikator. Ze względu na sztuczne źródło testy **nie certyfikują niezależnie autentyczności momentu odczytu ELO**.

**Wykonany referencyjny przykład:** 12 wyłącznie ZMYŚLONYCH wyników TRAIN, optymalizator otrzymał `mu_home=2.0`, `mu_away=0.5`, `elo_goal_elasticity=0.0`; to parametry przykładowej, sztucznej próbki, NIE parametry KB Score 3.0 i NIE prognoza sportowa. Wartość treningowego NLL 27.462977349072986 jest wyłącznie matematycznym sprawdzianem optymalizatora, NIE historycznym log loss na 1X2. Twardy status `SYNTHETIC_FITTED_REFERENCE_ONLY_NOT_FOR_BETTING`. [Niepodmienialny raport referencyjny](../data/audits/STEP13_SYNTHETIC_POISSON_FIT_V03_2026-10-26.json), SHA256 `55c28c220c140c00be0b3272c87053e2be13a580d3c58740e8fd506c9e9d3523`.

**Testy i bramki:** [15 testów parametrów i anty-leakage](../tests/test_step13_poisson_train.py); [CI PASS](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40395088065). Generator sprawdza dodatkowo podpisaną wersję raportu rzeczywistej luki PIT ze Step12: nadal 1520 realnych ID, **0 rzeczywistych meczów dopuszczonych do fit**, historyczny Brier, log loss i kalibracja nadal NIEOBLICZONE. Nie wygenerowano rekomendacji, nie pobierano API, nie wykorzystano TEST.

**Warianty, które odblokują dalszą pracę:**
1. Formalnie zatwierdzone źródło historycznie dostępnych cech i wyników z wiarygodnym niezależnym `observed_at` — umożliwia pełny backtest PIT.
2. Osobno uzgodniony badawczy, wyraźnie opisany replay z wyników archiwalnych dostępnych obecnie, oparty wyłącznie na historycznej kolejności zdarzeń — może służyć do badań wstępnych, lecz **nie** daje dowodu historycznej wiedzy przed meczem i nie może automatycznie zaliczyć GATE13.

**GATE13 PENDING**: nadal brak rzeczywistych historycznych metryk. **Stan projektu 12/29; produkcyjne training_allowed=false**.
