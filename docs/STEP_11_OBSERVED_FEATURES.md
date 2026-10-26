# KB Score 3.0 — Krok 11: wspólny silnik cech z rzeczywistą historią observed-at

**26 października 2026. Status:** wdrożenie i niezależny test częściowy **PASS**, cała bramka **GATE11 PENDING (10/29)**. **Nie trenowano modelu**, nie wyprodukowano typów, żaden starszy model nie został zmieniony.

## Co zmieniono w kodzie

- `src/kb3_features.py`, v0.4: wydzielono wspólną funkcję `_compose_features` dla istniejącego `verified`, `replay` i nowego `observed`. Zachowuje ten sam algorytm ELO oraz okna 5/10/15 dla punktów, goli, siły przeciwnika, xG/xGA, dom/wyjazd i flag braku danych. Robocze `K=20`, `H=65`, `retention=0.85` nie zostały dopasowane z przyszłych danych.
- `src/kb3_observed_features.py`: bierze tylko **rzeczywiście zaobserwowaną** wcześniej pełną odpowiedź z zabezpieczonego dziennika PIT. Odrzuca źródło syntetyczne, niekompletną historię, wynik bez FT/90 minut, nieaktualną rewizję, wynik z cutoff i xG po cutoff. Nie dopisuje żadnych rekordów do historii wstecz. Weryfikuje pełny łańcuch i hashe źródła. `training_allowed=false`.
- Przed wykorzystaniem xG obowiązują **dwie niezależne daty**: obserwacja źródłowych strzałów oraz zatwierdzenie powiązania źródeł. Trzy zweryfikowane pary z 25.10.2026 nie mogą być użyte przed **2026-10-26T09:53:09Z**, tj. czasem scalenia manifestu w [commit GitHub 1f6032d](https://github.com/karolbarankiewicz1984-ui/kb-score-3/commit/1f6032d4562d457e9bcb92381bf28a6cfa56a120). Fikcyjny lub wcześniejszy czas, niezgodny hash źródła oraz brak manifestu blokują xG.
- W `scripts/step11_observed_features_audit.py` można bez połączenia sieciowego odtworzyć audyt cech z **wcześniej odszyfrowanej i niezależnie zweryfikowanej** SQLite; raport jest zanonimizowany do liczników i hashy, nie eksportuje surowych danych ani kluczy.
- Trzy warianty źródła pozostają odrębne: `replay` = retrospekcja; `verified` = rygorystyczne poprzednie reguły; `observed` = autentyczne lokalnie zarejestrowane treści z oznaczeniem `OBSERVED_AT_NOT_CERTIFIED`. Żadna z tych etykiet nie stanowi automatycznej zgody na ML.

## Testy automatyczne i zgodność wsteczna

[GitHub Actions #40306542175](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40306542175): **125/125 PASS** — 86 testów krok 11, 39 testów regresyjnych GATE08–10. W tym nowe testy odmowy backdatingu, przyszłych wyników, użycia xG przed pobraniem i przed *review commit*, niezgodności SHA, zmian wyniku po cutoff, zachowania braków xG jako NULL, niezmienności obliczeń z wcześniejszego cutoff i poprawności ELO. Bez odpłatnych wywołań API.

## Niezależny test na prawdziwym archiwum Google Drive

Źródło: zaszyfrowany dziennik 380 obserwacji Premier League 2026/27, 3 niezmienne historyczne feedy PitchAPI, z którego wydzielono trzy audytowalne mapowania konkretnych meczów. [Oryginalne archiwum na prywatnym Drive](https://drive.google.com/file/d/1eoBQ-71T4J0wsmqEZ9NPLHcWR7rlnXqW/view?usp=drivesdk). Niezależnie pobrany kod [GitHub Actions #40306671705](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40306671705) uruchomiono lokalnie na odszyfrowanej kopii z dotychczasowym kluczem odzyskiwania, **nigdy nie wysłano klucza do GitHub**.

Rzeczywisty kontrolny cel: przyszły mecz **Bournemouth – Leeds**, fixture API-Football `1557448`; cutoff `2026-10-26T10:01:00Z`. Raport:
- **380/380** zweryfikowanych hashy zapisanych spotkań i **3/3** zweryfikowane niezmienne obserwacje xG; `PRAGMA integrity_check = ok`, FK = 0. Sama SQLite pozostała bajtowo niezmieniona po obliczeniach.
- **80** wyników zakończonych spotkań miało dowód obserwacji przed cutoff. Model prawidłowo zbudował ELO i formę.
- **1** zaakceptowane historyczne xG zespołu Leeds w oknie ostatnich pięciu meczów, **0** w analogicznym oknie Bournemouth. Brak xG nie został zastąpiony zerem w średniej.
- W wersji cutoff **09:45 UTC** (przed zatwierdzeniem powiązań 09:53:09 UTC) liczba dopuszczonych xG wynosiła **0**. Bez manifestu review także **0**. Manifest z uszkodzonym hashem archiwum został **odrzucony**.
- Identyfikator meczu docelowego nie znalazł się w `lineage` historii; `training_allowed=false`, `historical_backtest_certified=false` i `provider_original_publication_time_known=false`.
- Dowód: [STEP11_OBSERVED_BUILDER_REAL_DRIVE_2026-10-26.json](../data/audits/STEP11_OBSERVED_BUILDER_REAL_DRIVE_2026-10-26.json) — nie publikuje klucza, surowych xG ani pełnych danych meczów. SHA gotowych cech: `13ba063e280bc099085d375093ea74bc9f0928410da9da35184c91debb9782dc`.

## Co blokuje pełny GATE11

**To nie jest pełny, certyfikowany historyczny backtest.** Źródło poznaliśmy dopiero 26.10.2026; archiwum z 2023–2025 pozostaje `RETROSPECTIVE`. Wartości xG ze trzech meczów są kontrolowaną małą próbką, nie pełnym pokryciem sezonu. Do odbioru bramki potrzebne są kolejne obserwacje z późniejszych dni, większa liczba bezpiecznie przypisanych xG, audyt przypadków braków, walidacja referencyjna i końcowe sprawdzenie przecieków. Nie włączać treningu, nie przechodzić do kroku 12 automatycznie.

**Ważne:** K = 20 i H = 65 to wciąż ustawienia robocze. Optymalizacja wyłącznie po wykonaniu chronologicznego podziału TRAIN/VALIDATION/TEST, zgodnie z planem.
