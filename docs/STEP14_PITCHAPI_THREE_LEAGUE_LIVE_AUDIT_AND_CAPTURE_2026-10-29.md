# KB Score 3.0 — rzeczywisty audyt PitchAPI i trzy ligi do bieżącego zbierania danych (29.10.2026)

**Zastosowanie:** wdrożenie przygotowania pilotażu M0 zgodnie z [ADR-2026-10-29-01](ADR_2026-10-29_FORWARD_M0_PIT_CALIBRATION_STORAGE.md), **bez treningu CatBoost M1, kalibracji, typowania i naruszania Premier League 2026/27 TEST**. To etap gromadzenia źródeł, a nie certyfikacja 121 cech + 38 flag.

## Sprawdzono przez prawdziwe SDK, a nie tylko dokumentację

[Rzeczywisty GitHub Actions #40831173189](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40831173189) **SUCCESS, 8/8 testów, 13 autentycznych API requestów** przez istniejący sekret `PITCHAPI_API_KEY`, w tym rzeczywiste `matches.shots` i `matches.stats` dla już rozegranego spotkania z każdej ligi.

| Liga | Sezon 2026/27 w katalogu | Poprzedni 2025/26 | Obecne pozostałe mecze w tym odczycie | Dostępna wynikowa historia >=15 na 8 stron dla czterech najbliższych spotkań |
|---|---|---|---:|---:|
| Hiszpania LaLiga (`ESP`) | 380 terminarz | 380 | **280** | **7/8** |
| Włochy Serie A (`ITA`) | 380 terminarz | 380 | **292** | **6/8** |
| Niemcy Bundesliga (`GER`) | 306 terminarz | 306 | **243** | **5/8** |

**Pozostałe** oznacza w tym jednorazowym odczycie jeszcze nierozpoczęte spotkania, nie trwałą prognozę liczby meczów po późniejszym terminie. Dostępna historia 15 oznacza dopasowane **poprzednie wyniki po natywnym `team_id` i `fixture_id`**, wliczając sezon poprzedni i wymuszając odczekanie min. 3 godzin od kickoff zakończonego spotkania. Brak wymaganych 15 oznacza poprawną maskę missingness, **nigdy zero**. Z tego wyniku **nie wynika**, że dla wszystkich historycznych 15 poprzedników pobrano i zweryfikowano xG — osobno potwierdzono po jednej parze `shots/stats` z każdej ligi.

**Każda z trzech lig ma autentyczne odczytane xG strzałowe i meczowe**; walidator `src/kb3_step14_pitchapi_xg_semantics.py` odrzuca niezgodne `match_id/home_team.id/away_team.id`, duplikaty i inne rodzaje xG (xGOT/npxG). Nie wolno stawiać `provider_first_published_at` na podstawie dzisiejszego czasu odczytu.

## Zbieranie przyrostowe — koncepcja i implementacja

- Kod audytu: `scripts/step14_three_league_pitchapi_actual_audit.py` i [workflow](../.github/workflows/kb3-pitchapi-three-league-audit.yml). Łącznie **13 żądań** (katalog + aktualne/poprz. mecze 3 lig + po 1 shots/stat pair każdej). Oryginalne 13 źródeł szyfrowane istniejącym **publicznym** kluczem RSA/AES-GCM, obsługiwane bez prywatnego PEM na GitHub.
- Przyrostowy kolektor: `scripts/step14_three_league_pitchapi_daily_asof.py` i [workflow](../.github/workflows/kb3-pitchapi-three-league-daily.yml). Harmonogram **06:17 UTC codziennie** (przyjęty rozkład techniczny, niezależny od starego PL collector **04:42 UTC**). **43 zapytania/dzień maksymalnie**, w tym 1 katalog, 3×2 sezonowe terminarze i **maks. 6 jeszcze nieodczytanych poprzednich spotkań na ligę**, każde `shots` + `stats`. Cel: stopniowo uzupełniać prawdziwe poprzednie xG/xGA dla czterech najbliższych meczów ligi i ich dwudziestu czterech team-sides; cztery mecze = osiem stron na ligę, razem 24 strony. Mecz sprawdzony w poprzedniej dacie jest rozpoznawany po SHA256 `country|match_id`, unika się powtórek przy sukcesie.
- Magazyn: prywatne repo `data/pit_sidecar/pitchapi_three_league_daily/YYYY-MM-DD/` (`.enc`, `.manifest.json`, `THREE_LEAGUE_DAILY_RECEIPT.json`) — `append-only`; pełny payload i wartości xG tylko w zaszyfrowanym oryginale. GitHub Actions artefakt dodatkowo (30 dni), ale nie jedyny trwały magazyn. Dzienny raport jawny zawiera zagregowane statystyki, znaczniki czasu, SHA i stany, **nie wyniki ani wartości xG poszczególnych spotkań**.
- Odpytywanie jest ograniczone z zapasem; z oficjalnej strony PitchAPI wynika brak stałego dziennego allowance, ale dostawca stosuje `429` fair-use burst guard — dlatego łagodny pacing i twardy limit w naszym kodzie. Nie zakupiono nowych subskrypcji.

**Uwaga o gotowości:** stworzenie i zaliczenie kodu kolektora nie jest samo w sobie dowodem, że jego prawdziwe wykonanie dzienne zostało zapisane w `main`. Status pierwszego uruchomienia i link dopisać dopiero po realnym sukcesie i odczycie zapisanego pliku. W tym dokumencie nie należy twierdzić, że działają M0 prognozy, 121+38 obliczonych cech, SQLite produkcyjne, Google Drive offsite ani kalibracja.

## Dalszy zakres przed uruchomieniem M0

(1) Obserwować przyrost realnych, poprawnych xG 5/10/15; (2) połączyć zaszyfrowany ledger z czytelną dla uprawnionego procesu ewidencją SQLite i kontrolą SHA/pre-match cutoff; (3) budować wersjonowane `feature_snapshot` tylko z danych uzyskanych przed kickoff; (4) zintegrować model M0, niezależny serwerowy freeze i raportowanie; (5) dopiero później settlement + kalibracja **100/50 niezależnych meczów**, nigdy oryginalnym TEST PL 2026/27. Oryginalne kryteria 29-etapowego planu i `GATE14=PENDING` bez zmian.

## Uwaga metodologiczna o ID i historii

Dostawca potrafi zmienić identyfikatory przy zmianie upstream feed, zwłaszcza dla części dodanych lig. Do synchronizacji różnych wersji wymagany audyt tożsamości, nie cicha zamiana historycznych zespołów. W tej wersji przechowujemy oryginalne pełne payloady i SHA, a wyniki `>=15` raportujemy tylko przy zgodnym, stabilnym `team_id` w obu sezonach.
