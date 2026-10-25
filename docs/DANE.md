# KB Score 3.0 — DANE (specyfikacja źródeł i rejestrów)

**Status 25.10.2026:** audyty źródeł 05–06, mapowanie 07 i infrastruktura bazy 08 ZALICZONE. Import prawdziwej historii i analiza jakości każdego spotkania nadal należą do kroków 09–10.

**Źródło prawdy projektu:** [Plan Google Docs](https://docs.google.com/document/d/10wjHL3r3OAuxtezwcIeWztxS8lwjhYon5GM3BLhI0xE/edit) · [29 bramek odbioru](PLAN.md) · [metodologia](MODEL.md) · [dziennik](ZMIANY.md)

## 1. Cel i bezwzględne zasady

Baza KB3.0 ma pozwolić odtworzyć, **jakie informacje były dostępne przed konkretnym meczem**, wytrenować model na starszej historii i niezależnie sprawdzić prognozy na nowszych spotkaniach. Dozwolone jest używanie końcowego wyniku **jako etykiety uczącej** po meczu; niedozwolone jako cechy dostępnej przed meczem. Pustych statystyk nie zastępujemy zmyślonym zerem. Zachowujemy źródła, statusy, czas odczytu i pochodzenie danych.

Osobno oznaczamy `event_time` (kiedy coś się wydarzyło), `source_published_at` / `observed_at` (kiedy dane stały się dostępne) i `ingested_at` (kiedy je zapisaliśmy). Brak historycznego `observed_at` oznacza **niepotwierdzoną dostępność przed meczem**; nie wolno wtedy udawać autentycznego przedmeczowego snapshotu.

## 2. Dostawcy danych — status rzeczywisty i kolejne testy

| Źródło | Przewidziane zastosowanie | Co już potwierdzono | Do sprawdzenia |
|---|---|---|---|
| API-Football / API-SPORTS | Kalendarz, ligi, wyniki, statystyki, dostępne kursy | Aktywny dostęp Pro; w nowym repo pozytywny test odczytu 25.10.2026 | Krok 05: faktyczne pokrycie liga×sezon×pole, historię, limity wywołań i zasady retencji |
| PitchAPI | xG/strzały/zaawansowany kontekst jako źródło uzupełniające | Pozytywny odczyt autoryzowany 25.10.2026 | Krok 06: które sezony, które mecze, kompletność xG i możliwość prawidłowego odtworzenia historii |
| Historyczne kursy | Porównanie P(model) z ceną i CLV | Niepotwierdzone pełne archiwum historycznych ofert | Krok 19: dostawca, rynek, linia, bukmacher, timestamp i czas retencji |
| Dotychczasowe KB2.1 / API Market / MultiModel | Benchmarki tylko na porównywalnych spotkaniach | Istnieją wcześniejsze rejestry i raporty | Nie dopuszczać odzyskanych po meczu wierszy jako dowodu zamrożonej prognozy przed meczem |

**Nigdy nie logować kluczy API, tokenów ani surowych prywatnych danych kont.** Sekrety pozostają wyłącznie w GitHub Secrets.

## 3. Wersja v0.1 katalogu pól (do dalszego doprecyzowania)

### Encje i identyfikatory

| Obiekt | Pola obowiązkowe | Istotna kontrola |
|---|---|---|
| `providers` | provider_id, nazwa, wersja API, warunki retencji | Ślad źródła dla każdego rekordu |
| `competitions` | competition_id, provider_competition_id, kraj, nazwa, strefa czasu, sezon | Nie mieszać sezonów i rozgrywek |
| `teams` | team_id, provider_team_id, nazwy i aliasy, daty ważności | Zmiana nazwy nie tworzy nowej drużyny bez powodu |
| `fixtures` | match_id (wewnętrzne), IDs dostawców, gospodarze, goście, liga, sezon, kickoff_utc, status, home_goals, away_goals | Unikat, prawidłowe terminarze, przełożenia, 90 min vs ET |
| `fixture_provider_map` | match_id, provider, provider_fixture_id, match_quality, verified_at | Nie zgadywać niejednoznacznych dopasowań |
| `team_match_stats` | match_id, team_id, stat_name, stat_value, unit, provider, data_version, observed_at | Null to brak danych; zero tylko rzeczywiste zero |
| `match_events` | match_id, provider, type, minute, team_id, player_id?, extra_time_flag | Walidacja formatu i czasu zdarzenia |
| `prematch_snapshots` | snapshot_id, match_id, source, observed_at, feature_cutoff_utc, checksum | Zamrożony stan informacji, brak przyszłości |
| `odds_snapshots` | match_id, provider, bookmaker, market, selection, line, odds_decimal, observed_at, market_status | Dokładna linia i bukmacher, bez mieszania cen |
| `model_versions` | model_id, family, model_version, code_sha, training_data_hash, created_at, approved | Historia konfiguracji i decyzji |
| `feature_snapshots` | match_id, model_version, feature_cutoff, feature_version, feature_values_hash, missing_flags | Możliwość ponownego odtworzenia P |
| `predictions` | prediction_id, match_id, market, selection, line, P_raw, P_cal, model_id, feature_cutoff, generated_at, published_at?, freeze_hash | Nie zmieniać po publikacji, EARLY i FINAL oddzielnie |
| `settlements` | prediction_id, outcome WIN/LOSS/PUSH/VOID/PENDING, score_source, settled_at, result_version | Wynik dopisywany osobno, bez poprawiania P |
| `training_runs` | run_id, timestamp, code_sha, data_hash, split_hash, seed, hyperparameters, metrics, artifact_hash | Trening odtwarzalny |
| `data_quality` | dataset_version, league, season, coverage, duplicates, rejected, critical_errors | Blokowanie treningu przy błędach krytycznych |

Pola są **projektową listą logiczną**, nie deklaracją, że istnieją już takie tabele w bazie.

## 4. Import i walidacja

1. W kroku 05 sprawdzić rzeczywiste ligi i zakres danych API-Football; w 06 sprawdzić PitchAPI.
2. W kroku 07 ustalić mapowanie drużyn i spotkań, wykryć aliasy, przełożenia, mecze o tych samych nazwach, odmienne ID i strefy czasu.
3. W kroku 08 zatwierdzić schemat SQLite + Parquet i **trwały backup** z próbą odtworzenia, zamiast polegania tylko na artefaktach GitHub Actions.
4. W kroku 09 najpierw jedna liga i jeden sezon; drugi import tego samego zakresu **nie może duplikować meczów**. Przerwany import musi dawać się wznowić.
5. W kroku 10 kontrolować błędny kickoff, brak statusu, duplikaty, niezgodne wyniki, puste xG, zamianę home/away i przyszłe rekordy. Krytyczny błąd powinien zatrzymać trening.

### Weryfikacja jakości

- Raport liga×sezon: liczba meczów, odsetek z wynikiem, dostępność xG, statystyk, kursów oraz braków i odrzuceń; liczebności zamiast ogólnych określeń.
- Brak informacji o kontuzji lub xG **nie oznacza 0**; model musi znać brakującą cechę lub wariant bez tej cechy.
- Nie używać końcowej tabeli sezonu ani dzisiejszego ELO do odtwarzania meczu sprzed lat.
- Wartości historycznego kursu odczytane dziś nie są automatycznie autentycznym snapshotem kursu przed meczem.
- Dane liczymy zgodnie ze strefą `Europe/Warsaw` na potrzeby raportu, lecz czasy trwałe przechowujemy w UTC.
- Rozdzielić `scheduled`, `postponed`, `abandoned`, `finished`, `extra_time` i `penalties` zgodnie z dostępnością dostawcy i definicją rynku.

## 5. Zasady przechowywania i kosztów

- Repo GitHub: kod, dokumentacja, konfiguracja bez sekretów, metadane i manifesty niewielkiej wielkości.
- Baza danych i duże pliki Parquet: trwały magazyn wybrany po kroku 08, kopie testowane przez **restore**; nie deklarujemy dziś docelowego magazynu jako już gotowego.
- PDF: archiwum raportów po kroku 23; dane treningowe nie powinny istnieć wyłącznie w PDF.
- Każdy zbiór z zewnętrznego API podlega warunkom licencji i retencji dostawcy, które trzeba zweryfikować przed wieloletnim składowaniem.
- Preferencja: zero nowych zakupów na start; nie powiększać abonamentu bez zgody.

## 6. Klasy rynków i warunki włączenia

- **Wersja początkowa:** 1X2, Over/Under bramkowe, BTTS, team totals.
- **Później:** faule Under, kartki, rożne, handicap; osobna baza danych i definicja każdej linii.
- Dla porównań EV: `provider` + `bookmaker` + `market` + `selection` + `line` + `odds timestamp` muszą być identycznie interpretowane po stronie prognozy i kursu.
- Każda rodzina ma osobne metryki, walk-forward i testy rozliczeń. Jeśli brak danych — brak oficjalnego wyniku.

## 7. Bramki odbioru dotyczące danych

| Krok | Dowód obowiązkowy przed PASS |
|---|---|
| 05 | tabela liga×sezon×typ danych + liczebności, próbki, koszty zapytań |
| 06 | raport xG, próbka meczów, braki/coverage |
| 07 | ręcznie sprawdzone mapowanie, raport niejednoznacznych przypadków i duplikatów |
| 08 | schemat bazy, manifest backupu, test restore |
| 09 | manifest importu, checksumy, idempotencja, wznowienie |
| 10 | testy negatywne i pozytywne jakości danych oraz no-lookahead |
| 11 | katalog cech z czasem dostępności i testem odcięcia przyszłości |
| 12 | chronologiczny manifest TRAIN/VALIDATION/TEST i odtwarzalny walk-forward |
| 19 | przykładowe migawki kursów i test exact-market + no-vig/EV |
| 21 | przedmeczowy freeze ID, niezmienność P, odmowa zapisu po kickoff |
| 22 | wynik settlement WIN/LOSS/PUSH/VOID bez mutowania prognozy |

**Następny etap:** KROK 09 — import pierwszej ligi i sezonu, test idempotencji i wznawiania.


## 8. Wyniki rzeczywistego audytu źródła API-Football — GATE 05 PASS, 25.10.2026

Pełne dane [liga×sezon](audits/API_FOOTBALL_STEP05_2026-10-25.md), [JSON z liczbami](../data/audits/API_FOOTBALL_STEP05_2026-10-25.json), [protokół GATE 05](STEP_05_ACCEPTANCE.md).

**Potwierdzono bez nowych zakupów:** aktywny plan Pro, limit 7500/dzień i 300/min.; 30/30 kombinacji (5 lig × 2021–2026) udostępnia terminarze, 10 679 wpisów w terminarzach, 60/60 dwuzespołowych próbek statystyk zwróciło dane. Dwa niezależne przebiegi (112 + 131 zapytań) osiągnęły zgodność liczby meczów i statusów 25/25 wspólnych wierszy. Skład, wydarzenia i lista zawodników dostępne w pięciu przykładach 2025. Bieżący endpoint kursów działa, jednak jego archiwum przedmeczowe ma wąskie okno retencji; to nie są historyczne ceny z lat 2021–2025.

**Jakość wymaga dalszego sprawdzenia:** w jednej z 60 próbek brak kompletnych żółtych kartek, Ligue 1/2025 ma 307 zakończonych z 308 wpisów; występują niestandardowe wielkości niektórych sezonów (np. Serie A 2022 — 381 meczów w API). Weryfikacja danych per każdy mecz, deduplikacja i analiza dokładnego pochodzenia odbędą się w krokach 09–10. **Nie mylić** poprawnych próbek 60/60 z pokryciem kompletnych statystyk wszystkich 10 679 wpisów.

**Status:** KROK 05 ZALICZONY; KROK 06 PitchAPI pozostaje NIE ROZPOCZĘTY. Nie trenowano modelu.

## 11. Stan fizycznej bazy po GATE 08 PASS (25.10.2026)

- [Migracja SQLite v1](../migrations/001_initial_schema.sql) istnieje, tworzy transakcyjny schemat. [Protokół odbioru](STEP_08_ACCEPTANCE.md) zawiera mapę tabel i ograniczenia.
- [Narzędzie](../src/kb3_storage.py) uruchamia migrację, sprawdza integralność, tworzy kontrolowany syntetyczny backup i weryfikuje restore. Niezmienność prognoz sprawdzono 9 testami.
- [Trwała kopia testowa w Drive](https://drive.google.com/file/d/1DkaIfH24qf7z_KDuwbMzRuUd_iORbFxb/view) zawiera tylko fikcyjne dane. Zweryfikowano ją po ponownym pobraniu; [manifest SHA i ID](../data/audits/STEP08_BACKUP_MANIFEST_2026-10-25.json).
- **UWAGA:** to nie jest ani wypełniona baza historyczna, ani bezpieczny produkcyjny system kopii. Przed zapisaniem prawdziwych danych na Drive potrzebne są szyfrowanie i kontrola zasad dostawców; automatyczna retencja jeszcze nie powstała.
