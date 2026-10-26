# KB Score 3.0 — krok 11: katalog cech i audyt rzeczywistego czasu dostępności

**26.10.2026 • wersja kalkulatora `kb3-step11-v0.5` + nowa mapa `feature_availability` • GATE11 nadal PENDING (10/29).**

## Co dokładnie zostało sprawdzone

Zbudowano nowy **egzekwowalny walidator** `src/kb3_step11_field_audit.py` podłączony do **wspólnego** `_compose_features` w `src/kb3_features.py`. Walidator odrzuca każdą próbę użycia w trybie `observed`:

- wyniku meczu docelowego, innego przyszłego spotkania, niezakończonego lub sprzecznego wyniku, duplikatu identyfikatora i nieprawidłowego rezultatu;
- rezultatu obserwowanego *po* cutoff albo wcześniej niż trzy godziny od rozpoczęcia spotkania; 3 godziny to polityka ostrożności, **nie dowód rzeczywistego terminu publikacji**;
- xG bez odpowiadającego mu źródła lub ze źródłem bez prawidłowej godziny, xG obserwowanego po cutoff, oraz xG zatwierdzonego po cutoff — approval jest dodatkową, obowiązującą granicą czasu;
- próby przypisania do źródła dwóch różnych zegarów obserwacji, braku rzeczywistego zegara `source_observed_at_utc` albo odczytu późniejszego od cutoff.

Po udanej walidacji każda wyliczona wartość oraz każda flaga missingness dostaje osobny wpis `feature_availability[field]`. Wpis przechowuje: `latest_required_observed_at_utc`, typ dowodu (wyniki, xG lub kompletność), liczbę meczów, SHA-256 posortowanych identyfikatorów źródłowych, `provider_original_published_at_utc=null`, `training_allowed=false`. Jest to konserwatywny znacznik: uwzględnia także godzinę **całego** źródłowego snapshotu oraz czasu zatwierdzenia xG. Nie jest to rekonstrukcja niedostępnej historycznej daty pierwszej publikacji danych dostawcy.

## Katalog cech — wartości, okna, źródło i braki

| Grupa cech | Pola (prefiks `home_` i `away_`) | Podstawa i interpretacja |
|---|---|---|
| ELO | `elo`, `elo_games_available` | Ocena ELO i liczba zakończonych obserwowanych spotkań przed cutoff; bazowe ELO 1500, K 20, przewaga gospodarzy 65 punktów, skala 400, retencja sezonowa 0.85 są **prowizoryczne**, NIE dopasowane do danych |
| Długość historii | `games_available`, `prior_seasons_games_available`, `days_since_last_kickoff`, `venue_games_available` | Liczby i czas jedynie obserwowanych wyników sprzed cutoff; brak historii `days_since_last_kickoff=null` |
| Forma i skuteczność | `all_5/10/15_n`, `all_5/10/15_points_avg`, `gf_avg`, `ga_avg`, `opponent_elo_avg` | Średnie z ostatnich 5/10/15 dostępnych zakończonych spotkań; osobne liczniki, bo seria krótsza niż okno |
| Gra w odpowiedniej roli | analogiczny blok `venue_5/10/15_*` | Dla gospodarzy tylko domowe, dla gości tylko wyjazdowe spotkania, z zachowaniem chronologii |
| Rzeczywiste xG | `all_5/10/15_xg_n`, `xg_avg`, `xga_n`, `xga_avg` oraz `venue_*` | Strzałowe xG z odpowiednio przypisanego `match_id` PitchAPI; pojedyncza niedostępna obserwacja **nie** zamienia się w zero i nie wchodzi do średniej |
| Sygnały jakości próby | `missing_flags[*_history]`, `missing_flags[*_xg]`, `missing_flags[*_xga]`, `missing_flags[*_days_since_last_kickoff]` | Odnotowują brakujące spotkania w oknie oraz niedostępne xG/xGA; każda flaga ma również znacznik dostępności |
| Różnica poziomu | `elo_home_minus_away` | Różnica dwóch prowizorycznych ocen ELO; **nie jest prawdopodobieństwem wygranej gospodarzy** |

`opponent_elo_avg` to średnia oceny przeciwników z chwili ich meczów (przed aktualizacją ELO), a nie ocena tych rywali znana dopiero po kolejnych rundach. Wyniki z identycznym czasem rozpoczęcia są traktowane jako wspólna tura; żaden rywal nie korzysta z ELO z meczu jednoczesnego.

## Jak czytać wpis pochodzenia

Przykładowy **schemat** (to nie są prawdziwe dane konkretnego meczu):

```json
{
  "feature_availability": {
    "home_all_5_xg_avg": {
      "latest_required_observed_at_utc": "2026-10-26T10:30:00Z",
      "evidence_class": "OBSERVED_AT_NOT_PROVIDER_PUBLISHED",
      "kind": "XG_OBSERVATIONS_AND_RESULTS",
      "included_games": 5,
      "fixtures_sha256": "64-znakowy hash SHA256",
      "provider_original_published_at_utc": null,
      "training_allowed": false
    }
  }
}
```

Czas oznacza **najpóźniejszą niezbędną obserwację**; przy obliczeniach obowiązuje zawsze `latest_required_observed_at_utc <= feature_cutoff_utc < kickoff_utc`. SHA obejmuje identyfikatory użytych spotkań, zaś rzeczywiste wpisy źródłowe i czas odczytania każdego meczu są niezależnie zachowane w `lineage` oraz zaszyfrowanym archiwum. Mapy nie zawierają surowych xG w publicznym raporcie testowym. Jeżeli xG jest nieobecne, `xg_avg=null`, `xg_n=0`, flaga `missing_flags[...xg]=true`.

## Kontrole wykonane w tym PR

[GitHub Actions #40325431132](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40325431132): **217/217 PASS** (178 testów Step11 +39 etapów 8–10). Nowe 11 testów dotyczą: kompletnej mapy wszystkich wyjściowych pól i flag, granicy cutoff dla każdego pola, późniejszej obserwacji strzałów, wyboru strony gospodarze/goście, `null` bez xG, blokady niejednoznacznych zegarów źródła, przesuniętego approval, dopisania wyniku lub xG po cutoff, własnego/przyszłego meczu oraz snapshotu późniejszego niż cutoff. Poprzednie testy starego `observed` i natywnego PitchAPI również PASS. **To testy offline, częściowo na danych syntetycznych; nie jest to nowy autentyczny odczyt PitchAPI.**

## Świadome ograniczenia przed odbiorem GATE11

| Warunek | Stan 26.10.2026 |
|---|---|
| Natywna, jednoźródłowa tożsamość meczów i xG PitchAPI | **PASS w przeprowadzonych próbach** |
| Szyfrowane archiwa / niezależny restore / SHA-chain | **PASS** |
| Brak przecieków future/target, późnego wyniku i xG | **PASS w regresjach offline** |
| Timestamp i pochodzenie każdej cechy + brak xG jako `null` | **PASS w regresjach offline** |
| Dwa prawdziwe snapshoty tego samego dnia, 380/380 bez korekt | **PASS** |
| Niezależne prawdziwe obserwacje i ewentualne rewizje **między różnymi datami** | **PENDING** |
| Szerszy audyt reprezentatywności/pokrycia xG poza 5/5 PL i 12/12 LE/LK | **PENDING** |
| Odtworzenie czasowo poprawnych cech na *wielodniowych* autentycznych archiwach i podpisanie GATE11 | **PENDING** |
| Wielosezonowa historia ELO w nowym natywnym builderze (aktualnie `season_start_year=2026`) | **NIEZAIMPLEMENTOWANA** — nie wolno twierdzić, że licznik `prior_seasons_games_available` w PitchAPI-native zawiera sezony 2023–2025 |

Oryginalny moment publikacji dostawcy **nie jest znany**, historyczne sezony 2023–2025 pozostają retrospektywne; ten brak nie może być ukrywany ani zastępowany datą pobrania. Proponowana bramka końcowa powinna dla trybu prospektywnego wymagać *faktycznie zaobserwowanych w czasie* danych, a nie źródeł pobranych dziś dla dawnego meczu.

**GATE11 PENDING; 10/29 kroków formalnie przyjętych.** Bez treningu i prognostycznych typów, bez zmian starszych modeli, bez odpłatnych nowych zakupów. Następny logiczny krok: prawdziwy odczyt PitchAPI w kolejnym dniu i porównanie obu snapshotów, a dopiero następnie decyzja o odbiorze.
