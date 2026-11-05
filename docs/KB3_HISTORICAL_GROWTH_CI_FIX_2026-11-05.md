# KB Score 3.0 — naprawa błędów CI przy wzroście archiwum (2026-11-05)

**Status odbioru:** trzy niezależne kontrole GitHub Actions PASS na SHA `5b28361c05e409d04ebe6a71f64445c15d0f72e2` (gałąź PR #159). Zmiany badawcze; **nie** oznaczają zatwierdzenia produkcyjnego nowego modelu.

## Przyczyna i decyzja

- Wczorajszy zamrożony eksperyment historyczny miał **1525** obserwacji (1520 ligowych, 5 UCL), **1007** RESEARCH_TRAIN / **376** RESEARCH_VALIDATION / 56 wykluczonych przez embargo. Są to wartości **historycznego konkretnego źródła**, a nie stałe limity rosnącej bazy.
- Po dodatkowym backfill historycznym aktualna SQLite zawiera **1761** obserwacji (1756 w ośmiu ligach, 5 UCL); nowy *hipotetyczny*, wyłącznie badawczy podział to **1172 TRAIN / 423 VALIDATION**. Oryginalny binary CatBoost Shadow Six SHA `58c5a7fc35afe942893a25b96233689d1f7814ec8a93ed689a7b46f553dbbbc5` i jego manifest pozostają bez zmian.
- Stare warunki `==1525`, `==1520`, `==1007`, `==376`, `==56` były porównywane z *bieżącym* materiałem i powodowały `HISTORICAL_PIT_BASELINE_DRIFT` i `RESEARCH_SPLIT_DRIFT`. Nie należy ograniczać nowych obserwacji ani usuwać danych, aby przejść CI.

## Wykonane zmiany

1. `scripts/kb3_p1_archived_source_recovery_audit.py`: liczniki historyczne są wyłącznie **dolną historyczną bazą porównawczą**, a różnica jest raportowana. Kontrole oryginalnego PIT, dat publikacji, cutoff i braku oficjalnych próbek nadal wymagają **0** i odrzucają naruszenia. M0 oraz bazy niezwiązane z research pozostały niezmienione.
2. `scripts/kb3_p1_retro_catboost_1007_376.py`: badawczy split jest liczony wyłącznie w oparciu o bieżące rzeczywiste obserwacje i selektory, bez podmiany wersji dawnego modelu; sprawdzane są zgodność liczników, brak chronionego ENG/UCL/current season, siedmiodniowe embargo, unikalne ID i brak leaku target. Raport każdej nowej eksperymentalnej kohorty dostaje nazwę z jej rzeczywistym rozmiarem.
3. Testy poprawione i rozszerzone: zgodność bieżącego zbioru z raportem, niezależność istniejącego zapieczętowanego Shadow, odrzucenie próby nadpisania źródłowego `provider_first_published_at_utc` przez SQLite `IMMUTABLE_HISTORICAL_SOURCE`. Testowanie tylko na osobnej kopii, bez omijania triggerów.
4. Workflow research-only sprawdza nowy, jawnie oznaczony zbiór i zachowuje ochronę oryginalnego M0, 0 formal PIT-certified TRAIN, 0 official FIT, GATE16/GATE17 PENDING i brak promocji Championa.

## Potwierdzone dowody testów

- [GitHub Actions #41987086779](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/41987086779): **SUCCESS** — kontrola bezpieczeństwa M0, chronologii i integralności; realny job provider/forecast na PR **SKIPPED zgodnie z polityką**.
- [GitHub Actions #41987086775](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/41987086775): **SUCCESS** — audyt historyczny, 7/7 testów źródłowych, 7/7 testów historycznego splitu, prawdziwy badawczy fit dwóch odseparowanych wariantów CatBoost na nowych 1172/423. Brier no-xG=0.6418824, z-xG=0.6399945; log loss 1.0642216 vs 1.0621424. Bootstrap tygodniowy obejmuje zero — brak podstaw do promocji nowego wariantu.
- [GitHub Actions #41987086753](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/41987086753): **SUCCESS**, pełna offline regresja: **1259 testów, 0 błędów, 0 niepowodzeń, 2 pominięte**. Oryginalne zapieczętowane audyty przeliczone, brak zapisów do modelu lub SQLite.
- Zgłoszenie przyczyny: [issue #160](https://github.com/karolbarankiewicz1984-ui/kb-score-3/issues/160), poprawki w [PR #159](https://github.com/karolbarankiewicz1984-ui/kb-score-3/pull/159).

## Granice decyzji

- To **usunięcie regresji testów historycznych**, nie potwierdzenie pierwszej prawdziwej pary M0/Shadow Six; CI używało danych offline, a żadne uruchomienie `workflow_dispatch forecast` nie było częścią naprawy.
- Nie podwyższać FIT/HOLDOUT, nie aktywować kalibracji ani produkcyjnego CatBoost; brak historycznego niezależnego źródłowego first-publication proof nadal blokuje formalny historyczny PIT.
- Kolejny etap: pierwszy rzeczywisty scheduled/manual `forecast` na `main`, potem GitHub host-attestation i rozliczenie tych samych przyszłych meczów.
