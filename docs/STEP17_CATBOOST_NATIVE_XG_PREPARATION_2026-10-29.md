# KB Score 3.0 — krok 17: CatBoost z xG — rzeczywisty native shadow i bramka treningu

**29.10.2026 | status: INTAKE LIVE / CATBOOST xG NOT FITTED | GATE17 PENDING, formalnie 15/29**

## Rozpoznanie z rzeczywistych raportów

Dotychczasowy `M1-R BASE` jest rzeczywiście wytrenowany na 720 TRAIN i oceniony na 374 VALIDATION, **bez xG**. Historyczny audyt 74 rewizji FPL/Opta wykazał **40/760** rekordów TRAIN z pełną alternatywną formą xG5 obu drużyn i **107/380** w VALIDATION; nie ma pewności, ile z nich pokrywa się z dokładnymi 720/374 BASE. Jest to suma xG zawodników z FPL/Opta, **a nie oryginalne PitchAPI All-team expected_goals**; 2023–25 provider first-published-at jest nadal nieustalony. Zatem `native-PitchAPI M1 exact-PIT TRAIN = 0` i `VALIDATION=0` w oryginalnej bramce. Nie wolno ogłaszać pełnoprawnego CatBoost z xG ani porównywać go tak, jakby 40 przykładów zastępowało 720 TRAIN. Nie otwierano chronionego TEST Premier League 2026/27.

Źródła: [historyczny raport FPL/Opta](../data/audits/STEP14_FPL74_2024_MIXED_XG_CORRECTED_V2_RESEARCH_SUMMARY_2026-10-29.json), [orzeczenie o historycznej dostępności natywnego xG](../data/audits/STEP14_FPL74_2024_MIXED_XG_CORRECTED_V2_ORIGINAL_M1_GATE_2026-10-29.json), [zamrożona bramka treningowa kroku 17](../data/audits/STEP17_CATBOOST_XG_TRAINING_GATE_2026-10-29.json) (po pierwszym udanym workflow na main).

## Rzeczywisty plan poboru natywnego xG — bez naruszania prognoz

Utworzono **oddzielny** kolektor `src/kb3_step17_xg_capture.py` oraz `scripts/step17_native_xg_eight_run.py`. Korzysta z istniejącego klucza PitchAPI i dokładnie tych samych ośmiu lig: ESP, ITA, GER, FRA, NED, BEL, TUR, POL, bez ENG i chronionego 2026/27 TEST. Start GitHub Actions `.github/workflows/kb3-step17-native-xg-eight-daily.yml` przy zmianie `main` i **codziennie 06:41 UTC**.

- 17 wywołań (katalog + poprzedni i bieżący sezon każdej ligi) + **co najwyżej 16** dodatkowych wywołań (jeden rzeczywiście zakończony, nieprzebadany, istotny dla przyszłych spotkań mecz w każdej lidze: `matches.shots` i `matches.stats`), razem **maksymalnie 33 wywołania na cykl**. Jest to zwiększenie liczby wywołań obecnego klucza, **bez zakupu abonamentu**, nie jest to obietnica nielimitowanego dostępu. W razie błędu API jest jawny raport, bez dopisywania fikcyjnego xG.
- Zapis tylko `finished`, minimum **3 godziny od kickoff**, poprzednik drużyny występującej w spotkaniu z następnych 96 godzin. Identical `match_id`, `home_team.id`, `away_team.id`. Akceptacja wyłącznie `shots[].expected_goals` 0..1 sumowanych po poprawnych `team_id` oraz `stats.period=All` / `Expected goals (xG)` / `expected_goals`; odrzucone xGOT, npxG, połowy i duplikaty. |shot sum − All stats| nie większa niż 0,15 na każdą stronę.
- Surowe odpowiedzi z timestampami i SHA są **szyfrowane RSA-OAEP + AES-GCM**, bez wystawiania API key lub niezaszyfrowanej odpowiedzi provider. Własny, niezmienny `data/forward_step17_xg_eight/observed_xg.sqlite` i `data/pit_sidecar/step17_native_xg_eight/YYYY-MM-DD/`. Blokady `UPDATE/DELETE`, dopasowanie po rzeczywistym ID, przechowywanie daty *obserwacji*, bez wymyślania daty pierwszego opublikowania przez dostawcę.
- Ocena pokrycia dla przyszłego celu bierze **dokładnie pięć rzeczywiście ostatnich zakończonych spotkań każdej drużyny**, niezależnie od tego, czy znamy w nich xG. **Nie wolno pominąć meczów bez xG** i zebrać pięciu innych dających korzystniejszy wynik; brak nigdy nie oznacza 0 xG. Do pełnej formy home/away xG i xGA muszą istnieć xG dla obu drużyn z każdego z tych rzeczywistych pięciu poprzedników i być obserwowane przed cutoff.
- Nowe źródła są badawcze i mogą służyć jako przedmeczowe obserwacje względem **przyszłego** celu po dacie pobrania. Nie dają historycznego oryginalnego dowodu pierwszej publikacji PitchAPI dla meczów 2023–2025.

## Warunki aktywacji rzeczywistego CatBoost z xG

Obecny CatBoost bez xG ma stałą binarkę TRAIN720, 85 oryginalnych cech i niezmienione prawdopodobieństwa. **CatBoost z xG nie ma jeszcze nowej wytrenowanej binarki, nie generuje prawdopodobieństw i nie jest Championem.** Nie będziemy dodawać xG z nowego źródła do starszych zamrożonych prognoz, dotykać 374 walidacyjnych etykiet do treningu ani brać wyników chronionego TEST. Aby ruszyć z osobnym CatBoost z xG, trzeba zbudować wystarczająco liczny i zgodny zbiór 720 TRAIN / niezależny 374 VALIDATION lub formalnie uzgodnioną odseparowaną przyszłą kohortę z tym samym provider/definicją, dowodami źródła, oddzielnymi etykietami 90 min i faktycznie zamrożonymi wartościami xG przed kickoff, oraz wykazać pokrycie po ligach i koszt braków. Model pozostanie `RESEARCH` do prawdziwego porównania z bazowym M0/CatBoost no-xG.

## Odbiór techniczny

Testy sprawdzają dokładne 8 lig, budżet 33, szyfrogram, prawdziwy schemat `shots/stats`, 1 mecz/ligę, zakaz spóźnionej obserwacji, duplikatów/zmian SQLite i wybierania wyłącznie obserwowanych spotkań zamiast ostatnich pięciu. W raporcie z pierwszego prawdziwego GitHub runu trzeba podać rzeczywiste `new_shots_stats_xg_verified`, `cumulative_verified_xg_matches` oraz `future_form5_coverage`. Sam udany offline test nie jest dowodem na pobrane xG. Formalnie krok 17 w realizacji, `GATE16/GATE17 PENDING`, ukończonych 15/29.
