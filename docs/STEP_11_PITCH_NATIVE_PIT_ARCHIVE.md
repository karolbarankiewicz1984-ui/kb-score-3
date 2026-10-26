# KB Score 3.0 — krok 11: pierwsza trwała obserwacja wyłącznie PitchAPI

**26 października 2026 r.** Stan: **PIT OBSERVED-AT PARTIAL PASS; GATE11 PENDING (10/29)**. To rzeczywisty zapis obserwacji wykonanej dziś, **nie** certyfikacja tego, kiedy PitchAPI pierwszy raz opublikowało dane historyczne. Nie uruchomiono żadnego treningu, prognoz ani nowych zakupów.

## Wykonanie rzeczywiste

[GitHub Actions #40315374235](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40315374235), zakończone SUCCESS. Z jednego źródła pobrano natywne dane Premier League 2026/27, bez API-Football:

| Zdarzenie | Wynik |
|---|---:|
| Czas startu/końca obserwacji | 2026-10-26 11:29:09.681040 — 11:29:10.322396 UTC |
| Pełna lista ligowa | 380 meczów: 80 finished, 300 not_started |
| Autentyczne feedy strzałowe xG | 5 zakończonych spotkań, **5/5 COMPLETE_SHOT_XG** |
| Wywołania PitchAPI | 7 (katalog, full season, 5 shots) |
| Wywołania API-Football | **0** |
| Zapisane sesje | 6 (jeden pełny sezon, pięć odczytów strzałowych) |
| Zapisane rekordy z własnym SHA-256 | 385 |

Dane źródłowe zachowują oryginalne identyfikatory `PitchAPI.match_id` i `PitchAPI.team_id`, bez mapowania do nazw lub ID innego dostawcy. Każda sesja zawiera autentyczny przedział czasu odczytu, całą odpowiedź źródłową, hashe rekordów i łańcuch hashy kolejnych pobrań. Brak dowodu daty pierwszej publikacji `published_at=NULL`. SQLite odrzuca UPDATE i DELETE sesji oraz rekordów.

## Trwała zaszyfrowana kopia + niezależne przywrócenie

[Kopia ZIP na prywatnym Google Drive](https://drive.google.com/file/d/18AeQOY7it5F58S4EqHKk8GDpqOD_TtUg/view), plik `KB3_PITCH_NATIVE_2026-27_PIT_20261026.zip`, 67 874 B. Archiwum zawiera **wyłącznie zaszyfrowaną bazę, manifest i agregatowy receipt**. Klucz prywatny nie został przekazany do GitHub ani do kopii Drive; do szyfrowania wykorzystano publiczny klucz dotychczasowego odbiorcy.

- AES-256-GCM + RSA-3072 OAEP-SHA256 z osobnym kontekstem kryptograficznym `KB3PN1`, aby nie pomylić archiwum PitchAPI z dawnym `KB3PIT1` API-Football.
- ZIP SHA-256: `1260442238b8b1b94bcc6d5d99ce7be5ea01ed51736df8289fefc85b4da7b5de`.
- Szyfrogram SHA-256: `396826389a58a07ca7366c81b437b111c9fded27143a2bf1b130e3579752bb50`.
- Końcowy hash-chain: `4afd5a6e697f13b36170854e0f3816506ca04e3742dd29491293f88785b33a4e`.
- Archiwum **pobrano ponownie z Google Drive**, niezależnie odszyfrowano kluczem właściciela, porównano hashe zaszyfrowanego i nieskompresowanego SQLite, sprawdzono `PRAGMA integrity_check=ok`, `foreign_key_check=0`, **385/385** hashy rekordów i **6/6** odtworzonych hashy sesji. Weryfikacja **PASS**.
- [Publiczny manifest wyłącznie zbiorczych dowodów](../data/audits/STEP11_PITCH_NATIVE_FIRST_OFFSITE_2026-10-26.json).

## Zmiany w kodzie

- `src/kb3_pitch_native_ledger.py`: osobny append-only ledger PitchAPI, `record("matches")` oraz `record("shots")`, `verify`, `latest_asof`, `shots_asof`. Jeżeli nowszy snapshot zmienia status meczu, wcześniejszy wynik FT ani pomeczowe xG nie są niejawnie przywracane. Przy próbie backdatingu zapisu NETWORK_OBSERVED, niezgodności ID meczu czy czasu przed końcem meczu następuje odmowa.
- `src/kb3_pitch_native_archive.py`: szyfrowanie nowego własnego typu archiwum, osobny MAGIC/AAD, zakaz nadpisywania, kontrola warstw hash-chain i struktury SQLite; dopuszcza wydanie rzeczywistego archiwum wyłącznie `NETWORK_OBSERVED`, bez danych syntetycznych.
- `scripts/step11_pitch_native_capture_once.py`: **jeden** pobór pełnego terminarza PL 2026/27 i **pięć** odczytów strzałów, maksymalnie 7 wywołań PitchAPI. Żadne surowe rekordy nie trafiają do logów lub zwykłego artefaktu.
- `src/kb3_pitch_native_observed_features.py`: realne źródło `observed` dla **tego samego** silnika Elo/formy 5/10/15, bazujące tylko na natywnych PitchAPI ID i obserwacjach przed cutoff, z xG dostępnym nie wcześniej niż rzeczywisty moment pobrania strzałów. Nie korzysta z API-Football.
- `tests/test_step11_pitch_native_ledger.py` oraz `tests/test_step11_pitch_native_observed.py`: **15** dodatkowych testów — niezmienność, hash-chain, próba zmiany rekordu, backdating, analogiczny algorytm formy, cofnięcie wyniku przez nową obserwację, wykluczenie przyszłości i kontrolny restore kryptografii.

[GitHub Actions #40316210520](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40316210520) — **175/175 PASS**, w tym 136 Step11 i 39 testów starszych etapów. Zwykły push/PR nie pobiera odpłatnych danych; jedno realne pobranie zostało wykonane osobnym workflow.

## Ograniczenia i następny etap

Ten snapshot udowadnia czas rzeczywistego odczytu z hosta 26.10.2026, **ale nie** moment oryginalnej publikacji historycznych wyników i xG przez dostawcę. Snapshot historycznych sezonów 2023–2025 nadal należy traktować jako RETROSPECTIVE. Nowy licznik danych PitchAPI obejmuje tylko PL i pięć próbek xG, nie pełne 77 lig. Rygorystyczny test sezonowego xG w Lidze Europy i Lidze Konferencji oraz porównanie rewizji rzeczywistego terminarza w kolejnych dniach nadal pozostają do wykonania. Nie można wstecznie „wyprodukować” drugiego dnia obserwacji.

**GATE11 nadal PENDING (10/29), `training_allowed=false`, produkcyjne przełączenie niezatwierdzone.** Gdy uzyskamy wiarygodne dłuższe okno obserwacji, wykonamy ostateczny audyt completeness/no-lookahead i dopiero ocenimy formalne zaliczenie kroku. Starszych archiwów ani KB2.1, API Market, MultiModel nie zmieniano.
