# KB Score 3.0 — niezależny audyt oryginalnego archiwum 23 prognoz M0/Shadow Six — 05.11.2026

**Status audytu oryginalnych bajtów:** 23/23 zgodne i bez anomalii integralności; **formalna rejestracja host-proof w SQLite:** PENDING (0/23). Wynik badań nie stanowi promocji CatBoost ani formalnej kalibracji.

## Identyfikacja autentycznego źródła

- GitHub Actions, ręczny `workflow_dispatch`, `main`, tryb `forecast`: [run #41993470337](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/41993470337), 2026-11-05 od 08:18:40 UTC, **SUCCESS**.
- Oryginalny artefakt `KB3_STEP16_M0_720_EIGHT_LEAGUE_FREEZE_SETTLEMENT_SOURCE_EVIDENCE`: GitHub **ID 13399481158**, server `created_at=2026-11-05T08:20:19Z`. GH API deklaruje SHA-256 archiwum `fc0661496b20e452d86547045c54b40e68ef78ef29d17da5442eb6f8ddb078ff`; **pobrano oryginalny ZIP przez połączenie GitHub, niezależnie policzono SHA-256 rzeczywistych bajtów i wynik jest identyczny**.
- Kopia oryginalnego 1 815 386-bajtowego ZIP zawiera 63 elementy, w tym pojedynczy plik `forward_m0_720_eight/kb3_forward_eight.sqlite` o rozmiarze 1 032 192 bajtów, oryginalny `pit_sidecar/.../forecast-082014439916/RECEIPT.json`, `SOURCE.enc`, `SOURCE.manifest.json` i zamrożony forecast.
- Weryfikacja bezpośrednio na oryginalnym ZIP: `RECEIPT.json` bajt-w-bajt identyczny z `forecasts/m0_720_eight/2026-11-05/forecast-082014439916/FROZEN_M0_720_EIGHT.json`; SHA-256 zaszyfrowanego `SOURCE.enc` zgadza się jednocześnie z `SOURCE.manifest.json.ciphertext_sha256` i `RECEIPT.json.source_cipher_sha256`; `final_chain_sha256` zgadza się z raportem. Nie odszyfrowywano danych i nie zmieniano źródeł.
- Trwały niezależny zapis na `main`: [commit `ae7a54f51782f1d21bd509a6dbfd7bba65fca00e`](https://github.com/karolbarankiewicz1984-ui/kb-score-3/commit/ae7a54f51782f1d21bd509a6dbfd7bba65fca00e), po zakończeniu uploadu artefaktu.

## Audyt SQLite i wszystkich 23 par

Odczyt wyłącznie z oryginalnych bajtów SQLite z archiwum, przez tymczasową kopię w trybie `immutable=1`:

- `PRAGMA integrity_check=ok`; `PRAGMA foreign_key_check` zwróciło pustą listę błędów.
- Baza: **149** prognoz M0 (w tym **23 nowe**), **23** rzeczywiste prognozy CatBoost Shadow Six i **75** dotychczas rozliczonych M0; brak istniejącej tabeli `kb3_p1_shadow_six_host_proofs` w tej wersji archiwalnej.
- Każdy Shadow ma istniejącego rodzica M0. **23 unikalne ID rodzica, 23 unikalne ID Shadow, 23/23** hash SHA-256 kanonicznych JSON poprawny po obu stronach, identyczne `feature_sha256`, `source_chain_sha256`, fixture, league i `feature_cutoff_utc`, poprawny przypięty hash CBM `58c5a7fc35afe942893a25b96233689d1f7814ec8a93ed689a7b46f553dbbbc5`.
- **23/23** lokalne zegary generowania Shadow zgodne z cutoffem; **23/23** niezależny czas utworzenia oryginalnego ZIP przez serwer GitHub jest **przed kickoff−90 min**. Najmniejszy rzeczywisty odstęp: **4 719,68 min (~78 h 40 min)**; największy **5 019,68 min (~83 h 40 min)**. Pierwszy kickoff `2026-11-08T15:00:00Z`, ostatni `2026-11-08T20:00:00Z`.
- Wszystkie 23 wektory M0 i 23 wektory Shadow 1/X/2 mają wartości w [0,1] i sumę 1 w tolerancji 1e−6. To kontrola *poprawności matematycznej*, nie skuteczności bukmacherskiej.
- Różnice predykcyjne między modelami: mediana największej bezwzględnej zmiany pojedynczej składowej `P(1),P(X),P(2)` na jednym meczu **0,1016**; największa **0,2631**. Brak zakończonych, dopasowanych meczów Shadow w tym źródłowym ZIP, więc **nie wolno wnioskować o przewadze żadnego modelu**.
- Podział nowych 23 par: **ESP 4, ITA 2, GER 2, FRA 5, NED 3, BEL 3, POL 2, TUR 2**. Użyto wyłącznie 8 dozwolonych lig; ENG/TEST wyłączone.
- Pierwotny `RECEIPT.json` jawnie potwierdza `catboost_shadow_six_research.added=23`, `missing_features_new_m0=0`, `official_fit_increment=0`, `gate16=PENDING`, `production_approved=false`.

## Ścisłe rozróżnienie: dowód hosta istnieje, ale oficjalny proof jeszcze nie jest wpisany

**Potwierdzono zewnętrzny timestamp GitHub API i autentyczny zgodny SHA ZIP**, co dowodzi przechwycenia oryginalnych bajtów przed kickoff. Jednak źródłowa SQLite sprzed następnego `settle` nie miała jeszcze tabeli niezależnych per-row proof. To **nie** jest `github_host_verified_shadow_pairs=23`; licznik oficjalny na dzień audytu pozostaje **0**.

Istniejący kod `github_actions_artifact_proofs` w `src/kb3_step16_m0_720_calibration.py` w rzeczywistym trybie `settle` sprawdza autentyczny original ZIP, serwerowy `created_at`, SHA i rodzica M0, a `audit_shadow` w `src/kb3_p1_shadow_host_provenance.py` odczytuje oryginalny ZIP i zapisuje osobną niezmienną tabelę `kb3_p1_shadow_six_host_proofs`. **Nie wykonywano** ręcznego zapisu do chronionej binarnej SQLite poza tym oryginalnym procesem; brak odtwarzania prognoz lub sztucznego zwiększania FIT.

## Kolejne kontrole odbiorcze

1. Po następnym rzeczywistym `settle` sprawdzić `publication_proof_audit.actions_artifact_audit`, `catboost_shadow_six_host_audit`, `KB3_FIRST_REAL_SHADOW_CHECKPOINT` i trwały commit; upewnić się, że wynik ponownie wskazuje dokładnie oryginalny artifact **13399481158** i jego timestamp. Warunek sukcesu: **23 nowe, prawdziwe per-row host-proofs** w niezmiennej tabeli oraz **0 errors**, inaczej zbadać przyczynę i pozostawić PENDING.
2. Po 8 listopada — i po oficjalnym potwierdzeniu pełnych wyników — rozliczyć dokładnie te same mecze i policzyć sparowane Brier/log loss `M0 vs Shadow Six`; nie podstawiać znanych po fakcie danych do predykcji.
3. Pozostawić oryginalny M0, 100 FIT + 50 przyszłych HOLDOUT, GATE16/17, historyczny PIT i produkcyjny Champion **bez zmian**; żadnej promocji modelu na podstawie tylko 23 rekordów.

**Zastrzeżenie:** liczby odnoszą się do niezależnego audytu *konkretnego oryginalnego ZIP* run #41993470337, a nie do dowolnych przyszłych snapshotów. Daty kickoff są datami z archiwum PitchAPI i nie stanowią niezależnego potwierdzenia kalendarza rozgrywek.
