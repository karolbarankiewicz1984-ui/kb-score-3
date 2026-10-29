# KB Score 3.0 — krok 14: rzeczywiste kroki 1–4, TRAIN 760 / VALIDATION 380 / macierz 1140×159

**Data uruchomienia:** 29 października 2026 r. [Realny audyt GitHub Actions PR #40876429035](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40876429035) — wyniki pracy nie są symulacją.

## 1. Odzyskanie historycznych cech dla TRAIN 760

Wykorzystano **12 wcześniej niezależnie datowanych i SHA-pinned źródeł** FPL/OpenFootball (historyczne wydania 2023/24 oraz 2024/25, poświadczone GH Archive). Oryginalne 760 rekordów `TRAIN` są identyfikowane po `PitchAPI match.id`, UTC, `home_team.id` / `away_team.id` z zamrożonego oryginalnego podziału oraz stronach drużyn — żadnych wyników meczów docelowych.

Warunek rygorystyczny na pozytywny rekord: oryginalny przedmeczowy SHA musi przedstawiać docelowy mecz jako **jeszcze niezakończony**, zawierać dokładnie dopasowane wyniki pięciu poprzednich spotkań obu drużyn, poświadczone publicznie **PRZED** tym meczem. Przedwczesne/wadliwe wyniki nie są naprawiane według danych z 2026, tylko pomijane. **Potwierdzono 10/760 takich rekordów TRAIN**. To mniejszy, ale mocniejszy status niż wcześniejszy wynik 106 potencjalnych 2023/24–2024/25 powiązań z [oddzielnego audytu lineage](../data/audits/STEP14_1140_EXACT_NATIVE_PUBLIC_SOURCE_PIT_SUMMARY_2026-10-28.json), który nie oznaczał 106 kompletów oryginalnych 121+38 wartości treningowych.

Dla rekordów z danymi obliczono z rzeczywistych wcześniejszych wyników FORM5, częściowe FORM10/15, role gospodarz/wyjazd, gole, punkty, liczniki i brakujące flagi. **Nie** zaliczono brakującego xG TRAIN z dawnej tabeli FPL fixture jako `0`, nie podstawiono wartości współczesnego PitchAPI ani nie użyto xG zawodników jako oryginalnego team xG.

## 2. Zagęszczenie historycznych wersji VALIDATION

Do dotychczasowych 14 archiwalnych wersji `olbauday/FPL-Core-Insights` dołączono **11 kolejnych**, razem **25** niezależnie poświadczonych dokładnych SHA na `main` z autentycznymi historycznymi czasami GitHub Actions. Każda nieprawidłowa historyczna kolejka jest jawnie kwarantannowana, żadne przyszłe wyniki nie uczestniczą w obliczeniach.

Wynik źródłowej rekonstrukcji 2025/26: **109/380** oryginalnych docelowych spotkań z kompletnym badawczym FORM5 obu drużyn oraz **107/380** z kompletnymi pięcioma alternatywnymi xG5/xGA5. Wzrost z 57 do 109, czyli **52 nowych** spotkań. Dwa rekordy z niekompletnym xG nie są błędnie zaliczane jako xG5. Jest to **zewnętrzna publiczna historia**, nie pełna semantyczna równoważność natywnego xG PitchAPI.

## 3. Wspólna macierz 1140 × 159

[Skrypt rekonstrukcji](../scripts/step14_train_760_dense_validation_1140_matrix.py) odtwarza jeden badawczy rekord dla **każdego z 760 TRAIN i 380 VALIDATION**. Każdy rekord zawiera oryginalny `fixture_id`, sezon i partycję, źródło, SHA i rzeczywisty historyczny czas dostępności (o ile istnieją), **121 numerycznych pól i 38 flag braków**. Gdy źródło nie dowodzi wartości, jest `null` i nie wymyślamy daty ani statystyki. Ponadto oryginalnie wyliczony na 1140 rzeczywistych poprzednikach **Elo 2026-retrospective w 19 odrębnych polach** pozostaje osobno: nie jest automatycznie awansowany do `original_PIT`.

Plik macierzy używa **gzip** wyłącznie dla kompresji (nie jest szyfrowany). Odtwarzalność i spójność sprawdza rzeczywisty SHA256 pliku. Nie użyto TEST 2026/27, kursów, ani wyników docelowych TRAIN. Zobacz [raport liczb](../data/audits/STEP14_760_TRAIN_DENSE_VALIDATION_121_38_SOURCE_MATRIX_SUMMARY_2026-10-29.json) oraz [macierz](../data/audits/STEP14_760_TRAIN_DENSE_VALIDATION_1140x159_RESEARCH_2026-10-29.jsonl.gz).

## 4. Końcowy audyt oryginalnego CatBoost M1

[Skrypt GATE14](../scripts/step14_train_validation_final_m1_fit_gate.py) wczytuje cały faktyczny plik 1140×159, sprawdza oryginalne ID i split, wszystkie 121 i 38 nazwy, brak połączenia Elo retro z historyczną macierzą, brak nieuprawnionych wartości xG w TRAIN, czas publikacji źródła mniejszy niż kickoff i brak TEST. [Raport końcowy](../data/audits/STEP14_760_DENSE_FINAL_ORIGINAL_M1_FIT_GATE_2026-10-29.json).

**GATE14 = PENDING; formalnie 13/29.** Oryginalne kompletne natywne PIT PitchAPI nadal **0/760 TRAIN i 0/380 VALIDATION**, model **nie wytrenowany**, prawdziwe metryki CatBoost M1 nie istnieją. Potrzebne autentyczne dawne `published_at`/snapshot receipts na konkretne źródłowe natywne wartości i definicję oryginalnego xG. Bez tego nie dopuszczamy treningu oryginalnego kontraktu, choć zewnętrzny research ma już rzeczywiste źródła.

**Brak nowych zakupów, szyfrowania, zmiany wag, matematyki Elo, metodologii M0, oryginalnego splitu czy chronionego TEST.** Zmiana jest oddzielnym torem badawczym.
