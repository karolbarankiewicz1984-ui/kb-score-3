# KB Score 3.0 — nowy CatBoost Shadow 6, zgodny z prospektywnym M0 (04.11.2026)

**Zlecenie:** „Przygotuj nową, perspektywiczną wersję Cat boost”. Celem jest prospektywnie zgodny, osobny, nieprodukcyjny kandydat działający docelowo przy *tym samym* rzeczywistym capture cutoff, same fixture i tej samej źródłowej migawce co M0. **Nie mylić przygotowania i symulacji adaptera z uruchomionym rzeczywistym kolektorem.**

## Uzasadnienie przeprojektowania

- Poprzednio wykonano realne dwa badawcze CatBoost 1007 TRAIN / 376 VALIDATION: 14 cech bez xG, 18 z xG. **Obecny forward M0 z PitchAPI pobiera w swoim 16-call zestawie tylko `leagues.matches` za obecny i poprzedni sezon**, następnie w `src/kb3_step16_m0_720_eight_forward.py` tworzy _compose_features z wyników 90-minutowych; `xgh/xga=None`, brak pól z liczbą strzałów/fau­li/rożnych/kartek. Wstawienie braków do starego 14/18-cechowego modelu byłoby dystrybucją odmienną od TRAIN i sztucznym dowodem parytetu.
- Dlatego stworzyć **nowy, odrębny model CatBoost z 6 cechami**: dla gospodarzy i gości *średnie z faktycznych ostatnich pięciu poprzedzających spotkań*, w kolejności `goals_for`, `goals_against`, `points`. W fazie treningu badawczego z `rolling_window` = [home/away]_goals_for, goals_against, points; w realnym forward z *tej samej* istniejącej `_compose_features` = [home/away]_all_5_gf_avg, _ga_avg, _points_avg. Kluczowe jest potwierdzenie identycznych nazw, orientacji home/away i chronologii w prawdziwym teście adaptera. Nie używać xG, kursów ani późniejszych wyników meczu celu.
- Wersja: `KB3_CATBOOST_SHADOW_LAST5_GOALS_6_RESEARCH_V1`, identyfikator kontraktu `KB3_CATBOOST_SHADOW_SIX_ASOF_M0_STEP11_V1`; nie nadpisywać M1-R 85 cech, M0 ani poprzednich 14/18-cechowych modeli. Dotychczasowe wyniki retro 14 i 18 pozostają osobnymi badaniami, nie wolno sumować ich z nowym 6-cechowym modelem.

## Zaimplementowane pliki

- `scripts/kb3_p1_prospective_six_train.py`: **prawdziwy fit** CatBoost na 1007 RECONSTRUCTED_RESEARCH_TRAIN, test 376 RECONSTRUCTED_RESEARCH_VALIDATION (7-dniowe embargo, tylko osiem lig i zakończone historyczne sezony). Stałe hiperparametry (180 iteracji, depth 3, lr .035, L2 8, seed 20261104), klasy 1/X/2, wzór Brier sum3, log loss, accuracy, ECE, analiza per liga. Plik `.cbm`, deterministyczny SHA256, wymuszona lista 6 kolumn i manifest pochodzenia jako **prywatny krótkotrwały artefakt CI**. To trening retrospektywny nie PIT-certified; formalny gate nadal PENDING.
- `src/kb3_p1_prospective_shadow_six_v1.py`: testowalny w istniejącym `make_forecasts()` adapter `ShadowSix.records(feature_state, parent)`. Czyta **bieżącą** gotową migawkę Step11 M0, weryfikuje 6 pełnych średnich last5, identyczność identyfikatora i cutoff oraz oryginalny SHA256 rodzica. Wymaga faktycznej chwili obliczenia shadow nie później niż kickoff −90 min; ponad 45-minutowe opóźnienie względem M0 źródłowego cutoff oznacza NO-GO. Weryfikuje dokładne bajty modelu i jego manifest, zakres 1007/376, brak fałszywych certyfikacji i zgodne klasy.
- `freeze_only_new_m0()` tworzy wyłącznie osobną append-only tabelę `kb3_p1_shadow_six_new_only` **na stagingowym** SQLite z FK do już zamrożonego rodzica M0. Duplikat, modyfikacja lub DELETE są zabronione. Dodaje wyłącznie rekordy rodziców nowo zapisanych *w tym samym uruchomieniu*, a stare M0 nie mogą otrzymać prognozy po fakcie. Każdy shadow i model ma własny SHA i deklaruje `shadow_host_artifact_verified=false` **dopóki nie zostanie przeprowadzona osobna niezależna weryfikacja GitHub-host-created artifact**; sam timestamp programu nie uprawnia do włączenia do formalnej oceny.
- `tests/test_kb3_p1_prospective_shadow_six_v1.py` uruchamia **rzeczywisty, nowo wytrenowany plik CatBoost na testowym, syntetycznym dostawcy** przez ten sam działający kod `make_forecasts()` co M0. Sprawdza poprawne 64 identyczne pary, SHA, osobną bazę, niezmienność starych tabel, brak retro backfillu, modyfikacje prognoz i próby late forecasting. Dane testowe **nie są realnymi nowymi prognozami**.
- `.github/workflows/kb3-p1-prospective-catboost-six-shadow-research.yml`: izolowany workflow PR-only, **permissions contents:read**, bez nowych wywołań PitchAPI, bez odszyfrowywania archiwów, bez zmiany oryginalnego M0, bez prób naprawiania PIT wstecz. Nie ma triggera schedule ani produkcyjnej aktywacji.

## Formalny etap startu LIVE — nie uruchamiać bez odbioru

1. Zweryfikować CI, metryki 6-cechowego modelu, manifest i SHA z *rzeczywistego* runu. Rozstrzygnąć, czy poprawne jest kodowanie 6 wejść M0 dokładnie na tym samym nowym fixture/cutoff i czy brak 5 poprzedników blokuje prognozę.
2. Odseparowany code review i decyzja o integracji: przy **nowych** M0 prognozach można dodać niezależny shadow sink, który korzysta z in-memory `feature_state` w momencie jego wytworzenia. Wdrożenie wymaga **jawnej modyfikacji orkiestracji M0** i sprawdzania modelu z trwałymi SHA; sama gałąź **nie zmienia aktualnego zada­nia cyklicznego**. Nie dopisywać starych M0.
3. W każdej przyszłej rzeczywistej próbie wygenerować append-only shadow w tym samym stagingowym źródle co M0 oraz archiwum oryginalnych bajtów i osobny host proof. Dowód powstania artefaktu GitHub przed kickoff−90 min to oddzielna bramka; bez niego nie zaliczać do porównań.
4. Rozliczanie tylko **na tych samych** host-attested fixture IDs i horyzontach; na początku diagnostycznie Brier/log loss/top1/ECE i braki per liga. Prawdziwa ilość wspólnych nowych meczów na starcie = 0. Formalne porównanie po wymaganym minimum 100 par / 8 tygodni oraz niezależnych GATE16, GATE17.
5. Jeśli model wyniesiony z retrospekcji okaże się słaby lub nie ma trwałych bajtów modelu i niezależnej walidacji źródła: **NO-GO live**, pozostawić M0.

**Bramki i ochrony:** P1-01 nadal częściowy, 100 FIT + 50 niezależnych HOLDOUT M0 bez zmian, oryginalny ENG Premier League TEST nieodczytany. Nie ma automatycznej promocji Championa, nie ma prawa przedstawiać tej nowej wersji jako pełnej cechowej wersji v2 wytrenowanej na certyfikowanych historycznych danych.

## Odbiór CI

Do uzupełnienia rzeczywistym numerem runu, testami, SHA, metrykami i statusem po zakończonym GitHub Actions. Nie wpisywać PASS przed odczytem.
