# KB Score 3.0 — Step18 — równoległe przygotowanie bramki dowodów, 02.11.2026

**Status:** research, bez formalnego GATE18, bez zmiany Championa. M0 720 TRAIN oraz 100 FIT + 50 nowych HOLDOUT nietknięte. Właściciel polecił przyspieszyć budowę, więc wykonano element Step18 niezależny od zamknięcia Step16/17.

## Zasady
- Każdego dnia w tym samym bezsieciowym CI co Step16 i Step17 powstaje trzeci raport: `STEP18_GATE_<GITHUB_RUN_ID>.json`.
- `src/kb3_step18_decision_readiness.py` czyta wyłącznie wcześniejszy, poświadczony i policzony na identycznych meczach raport `step17_offline_three_engine_audit` z tego samego runu.
- Dla Elo-only oraz CatBoost bez xG sprawdza liczbę sparowanych rozliczonych spotkań **minimum 100**, **minimum 8 niezależnych tygodni**, i dwa przedziały 95% różnic per-fixture (Brier i log loss). Przedziały muszą wskazywać tę samą, jednoznaczną przewagę nad M0. Mniejsza liczba lub przedział obejmujący zero => brak sygnału.
- Sygnał statystyczny wśród konkurentów jest WYŁĄCZNIE obserwacją badawczą, nie wystarcza nawet do decyzji o wyborze nowego Championa; potrzebne nieużyte okno potwierdzające, formalne osobne odbiory GATE16/17 oraz aprobata właściciela.
- **Bramka nie umożliwia aktywacji produkcyjnej**: `ready_for_human_champion_decision=False`, `candidate_deployment_authorized=False`, `winner_chosen=False`, `formal_step18=PENDING_16_17_AND_OWNER_APPROVAL`. Żaden kod nie odczytuje sealed TEST Premier League 2026/27, nie kontaktuje się z dostawcą, nie dopasowuje modelu ani nie modyfikuje prognoz.
- Testy obejmują obecność kompletnego źródła Step17, 0/42/120 paired, 3 vs 10 niezależnych tygodni, CI z zerem, oraz fałszywy status źródeł i cofnięcie weryfikacji.

**Dlaczego to przyspiesza:** po zebraniu nowych wyników bez kolejnego ręcznego projektowania statystycznego gate z góry otrzymamy widoczną informację o brakujących warunkach. To nie przyspiesza fizycznego upływu czasu ani nie usprawiedliwia przedwczesnego odbioru kroków.

**Status formalny w planie:** 15/29, kroki 16/17 w realizacji, krok 18 przygotowanie techniczne, niezaliczony; nie ma automatycznego awansu.
