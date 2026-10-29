# KB Score 3.0 — M1-R / faktyczna rekonstrukcja 1140 spotkań historycznych według łagodniejszych kryteriów

**29.10.2026.** Nowa odizolowana wersja badawcza M1-R zgodna z [propozycją](STEP14_PROPOSAL_M1_R_RELAXED_HISTORICAL_AND_FUTURE_ASOF_2026-10-29.md). Wynik potwierdzony na **rzeczywistym oryginalnym PitchAPI** w [przebiegu CI #40906166102](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40906166102) i chronionym zamrożonym podziale.

## Wynik policzony, nie szacowany

| Partycja | Spotkania oryginalne | M1-R BASE min. 3 wcześniejsze zakończone mecze na każdą stronę | Cold start | Pokrycie |
| --- | ---: | ---: | ---: | ---: |
| TRAIN, sezon 2023/24 + 2024/25 | 760 | **720** | 40 | **94,74%** |
| VALIDATION, sezon 2025/26 | 380 | **374** | 6 | **98,42%** |
| **Razem** | **1140** | **1094** | **46** | **95,96%** |

**Tak, wszystkie 1140 wierszy są w nowej, rzeczywiście utworzonej macierzy badawczej**, także 46 cold start, żeby nie zgubić oryginalnych danych. 1094 kwalifikują się tylko pod względem dostępności podstawowych **FORM/Elo**, bez obietnicy skuteczności ani automatycznej gotowości do trenowania starego M1.

## Co dokładnie przeliczono

- Cztery rzeczywiste odczyty SDK PitchAPI: katalog oryginalnej ligi English Premier League oraz trzy oryginalne sezony 2023/24, 2024/25, 2025/26. 380 rzeczywistych meczów na sezon, po dokładnie tych samych natywnych ID, UTC, drużynach i niezmienionym podziale `TRAIN=760` / `VALIDATION=380`.
- **48-godzinny odstęp**: wynik wcześniejszego spotkania jest uwzględniany w feature snapshot dopiero od `kickoff_previous + 48h <= kickoff_target`. To konserwatywna rekonstrukcja chronologiczna **z danych pobranych obecnie**, nie twierdzenie, że posiadamy historyczne `PitchAPI published_at`.
- Wyliczono komplet nazw **121 cech numerycznych i 38 flag braków** dla każdego spotkania. Elo 1500 / K20 / home advantage65 / sezon retention0.85, licznik wcześniejszych spotkań, ostatni mecz, venue, FORM5/10/15, punkty, GF/GA, Elo przeciwników. Okna liczą 0–5/10/15 rzeczywistych wcześniejszych zdarzeń, bez dopisywania fikcyjnych meczów. Braki xG w BASE to `xg_avg=null`, `xg_n=0`, `missing=true`, **a nie** wartość xG=0.
- Gdy oba zespoły mają minimum po 3 wcześniejsze mecze po 48h, `m1r_base_eligible=true`. Jeśli któryś klub ma mniej, rekord zostaje `COLD_START`, nie jest usuwany. Dla przeciwnych wyników z tych samych timestampów nie wczytuje się aktualnego wyniku celu jako cechy. W VALIDATION wcześniejsze zakończone mecze VALIDATION mogą dostarczać historycznych form/Elo **dopiero 48h po swoim rozpoczęciu**. Nie służą do dopasowywania wag.
- Oryginalna, niezależnie sprawdzona [macierz FPL74 v2](../data/audits/STEP14_FPL74_2024_MIXED_XG_CORRECTED_V2_RESEARCH_SUMMARY_2026-10-29.json) została połączona **tylko jako osobny xG-overlay badawczy**, przy zachowaniu SHA źródła, oryginalnego source clock, definicji FPL/Opta player-xG w TRAIN i FPL-Core alternatywnego xG w VALIDATION. **Pełnych xG5: TRAIN 40, VALIDATION 107.** Odrębne źródła nie są semantycznie równoważne, a 48h chronologia wszystkich poprzedników w starszych agregatach xG nie została osobno dowiedziona. Dlatego xG nie jest włączony do bazowych 121 wartości BASE.

## Co będzie dalej, a czego świadomie nie zrobiono

Dla **M1-R-BASE** mamy technicznie odtworzone wejścia dla 720 TRAIN i 374 VALIDATION. Zanim zaczniemy eksperymentalny trening, trzeba wykonać dodatkowy **audyt granicy czasowej wyników** (symulowane 48h po kickoff nie jest rzeczywistym znacznikiem końca) i zgodności mapowania Elo/średnich, a następnie osobno zamrozić listę używanych pól, sposób liczenia braków, hiperparametry modelu i procedurę chronologicznej oceny. Wyniki 1/X/2, log loss, Brier i kalibracji **nie zostały wyliczone**, ponieważ M1-R **nie został jeszcze wytrenowany**. Dopiero walidacja oddzielnego modelu (nie produkcyjnego) może wykazać przewagę nad M0.

Nie wykorzystano sezonu TEST 2026/27, wyników celowych w cechach, wyniku VALIDATION do `fit`, danych live ani kursów. Oryginalny CatBoost M1 nie został zmieniony ani wytrenowany. Formalny stary `GATE14=PENDING` pozostaje taki sam.

### Artefakty

- [Raport 1140 rekordów — liczby TRAIN/VALIDATION, cold start, xG-overlay i SHA256](../data/audits/STEP14_M1R_RELAXED_1140_48H_121x38_SUMMARY_2026-10-29.json)
- [Pełna macierz 1140 × (121 numeryczne + 38 braków), dane xG źródłowo rozdzielone](../data/audits/STEP14_M1R_RELAXED_1140_48H_121x38_RESEARCH_2026-10-29.jsonl.gz)
- [Powtarzalny kod rekonstrukcji](../scripts/step14_m1r_recompute_1140_relaxed_48h.py)
- [Testy bezpieczeństwa danych](../tests/test_step14_m1r_relaxed_1140.py)

**Status końcowy:** `M1_R_BASE_FEATURES_RECONSTRUCTED`, oryginalny `GATE14=PENDING`. Bez zmian w oryginalnych wagach, metodologii M0, oryginalnym M1 i chronionym TEST.
