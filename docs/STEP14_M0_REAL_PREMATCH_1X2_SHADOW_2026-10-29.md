# KB Score 3.0 — realne M0 Elo + Poisson: pierwsze zamrożone prawdopodobieństwa 1/X/2 (29.10.2026)

**Wykonane: [PR #83](https://github.com/karolbarankiewicz1984-ui/kb-score-3/pull/83), [GitHub Actions #40836191816](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40836191816) SUCCESS.** Jest to **pilotaż SHADOW, nie prognozy produkcyjnego Championa, nie typy bukmacherskie**. Oryginalny plan 29 kroków i `GATE14=PENDING` pozostają bez zmian.

## Faktyczny pierwszy przebieg

* Źródło: **rzeczywiste, zamrożone wcześniej 12× (121 cech numeric/nullable + 38 flag)** z prywatnej `data/forward_m0/kb3_forward_m0.sqlite`, utrwalone 29.10.2026 około **07:19 UTC**; po 4 przyszłe mecze LaLiga (`ESP`), Serie A (`ITA`) i Bundesliga (`GER`). Wszystkie 159 wejściowych pól podlegają kontroli rzeczywistych przedmeczowych zegarów. Brak xG oznacza `null+missing`, nie wymyśloną wartość.
* Silnik: **oryginalny** `src/kb3_step13_baseline.py::forecast(home_elo,away_elo,BaselineParameters())`, czyli Elo kroku 11 i niezależny Poisson z **ilustracyjnymi, NIE trenowanymi** `base_home_goals=1.45`, `base_away_goals=1.15`, `elo_goal_elasticity=0.35`. Ten wariant **nie korzysta z xG bezpośrednio w prawdopodobieństwach** (gromadzi je dla przyszłego M1).
* Wytworzenie rzeczywistych prognoz: **29.10.2026, 07:33:48 UTC**, 12/12 wygenerowanych **przed kickoff** z marginesem minimum 90 minut, zweryfikowane 6 testami i dodatkowym niezależnym GitHub Actions testem rzeczywistego zegara. Każda z wartości `P(1)+P(X)+P(2)=1`, wszystkie >0 i <1.
* Wersjonowanie: `migrations/003_m0_1x2_shadow_freeze.sql` tworzy **append-only `m0_shadow_1x2_forecasts`**, powiązane FK z konkretnym `feature_snapshot_id`, zamrożonym SHA oryginalnego zestawu wejściowego, SHA parametrów matematyki i SHA konkretnej prognozy. `UPDATE` i `DELETE` zablokowane. Jeden `EARLY` forecast dla każdej pary kraj + oryginalny native fixture ID. Oryginalne `predictions` pozostają puste i wciąż wymagają certyfikowanego oryginalnego PIT; **nie fałszowano ich statusu źródła**.
* Rzeczywisty plik: [`data/forecasts/m0_shadow_1x2/2026-10-29/FROZEN_M0_SHADOW_1X2.json`](../data/forecasts/m0_shadow_1x2/2026-10-29/FROZEN_M0_SHADOW_1X2.json), **12 prawdziwych prognoz**, z pełną minutą kickoff, zespołami, `p_1x2`, λ home/away, Elo i potwierdzeniem niekalibrowania. SHA raportu `67ce451834039f1c4334e213621734c2906aba9c8321fd3035c1879bda7aadf2`. Zapis potwierdzony rzeczywistym odczytem z głównej gałęzi.
* Zasady bezpieczeństwa: **żadnego wyniku docelowego**, żadnego historycznego xG po meczu docelowym, żadnych kursów bukmacherów, żadnego `TEST` Premier League 2026/27, żadnego treningu M0/M1, żadnego `GATE14 PASS` i żadnej kalibracji na 12 próbkach.

## Reprezentatywne wyniki 1/X/2 (wyłącznie SHADOW, nie typy)

| Spotkanie | Kickoff UTC | P(1) | P(X) | P(2) |
|---|---|---:|---:|---:|
| Frosinone – Lecce | 29.10 17:30 | 48,1% | 25,4% | 26,5% |
| Fiorentina – Atalanta | 29.10 19:45 | 40,5% | 26,4% | 33,1% |
| Elversberg – Mainz 05 | 30.10 19:30 | 44,8% | 25,9% | 29,3% |
| Villarreal – Espanyol | 30.10 20:00 | 49,8% | 25,1% | 25,1% |
| Levante – Atlético Madrid | 31.10 13:00 | 37,3% | 26,5% | 36,2% |
| Bologna – Monza | 31.10 14:00 | 46,4% | 25,7% | 27,9% |
| Werder Bremen – Hoffenheim | 31.10 14:30 | 41,0% | 26,3% | 32,7% |
| Borussia Mönchengladbach – Paderborn | 31.10 14:30 | 41,1% | 26,3% | 32,5% |
| Schalke 04 – RB Leipzig | 31.10 14:30 | 39,9% | 26,4% | 33,7% |
| Rayo Vallecano – Celta Vigo | 31.10 15:15 | 43,4% | 26,1% | 30,5% |
| Udinese – Roma | 31.10 17:00 | 35,2% | 26,5% | 38,3% |
| Real Betis – Málaga | 31.10 17:30 | 50,3% | 25,0% | 24,7% |

**Wszystkie wartości są szacunkami niefitowanego M0**. Pytania o trafność, przewagę bukmacherską albo sens stawiania zakładów nie mają na tym etapie statystycznego rozstrzygnięcia.

## Cykliczne zbieranie i zamrażanie

[Trójligowy cron na main](../.github/workflows/kb3-pitchapi-three-league-daily.yml) o **06:17 UTC** przygotowuje po cztery kolejne `feature_snapshot` na ligę i zapisuje źródła RSA/AES-GCM do prywatnego repo. Nowy krok dołączony do tego samego cyklu wywołuje `src.kb3_m0_shadow_1x2_live_freeze`: wybiera tylko **pierwsze nieprognozowane** przyszłe spotkania, generuje `EARLY` 1X2 z ich ostatniej przedmeczowej migawki, utrwala w SQLite i tworzy dzienny raport tylko gdy rzeczywiście powstały nowe prognozy. W ten sposób każdy target ma tylko jeden pierwotny nieedytowalny prognozowy stan; przy braku nowego targetu nie wymyśla się „dodatkowych 12”.

**Odrębna ocena wymagana:** najbliższy kolejny prawdziwy dzienny przebieg i zapis jego prognoz trzeba zweryfikować po wykonaniu, a nie z góry ogłaszać sukcesem. Nadal **brak automatycznego `settlement`, metryk log loss/Brier, kalibracji 100/50 i niezależnego backup Google Drive**, więc nienagannie zamrożone wyniki nie są jeszcze systemem samouczącym.

**Źródła stałych ustaleń:** [ADR](ADR_2026-10-29_FORWARD_M0_PIT_CALIBRATION_STORAGE.md), [oryginalny plan](PLAN.md), [dokument realnego 121+38](STEP14_LIVE_M0_SQLITE_121_38_FORWARD_FREEZE_2026-10-29.md).
