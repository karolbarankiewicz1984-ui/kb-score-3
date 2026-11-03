# KB Score 3.0 — Historyczny PitchAPI multi-stat backfill, 3 XI 2026

## Cel i decyzja

Na polecenie właściciela przyspieszyć budowę KB3 poprzez równoległe pobieranie **rzeczywistych statystyk historycznych**, a nie czekanie wyłącznie na nadchodzące spotkania. Priorytet: sezony **2024/25, 2025/26 i obecny 2026/27**. Dodatkowy **2023/24** to wyłącznie materiał rozgrzewkowy dla rekonstrukcji formy na początku 2024/25, jeśli występuje w katalogu. Nie wymyślamy niedostępnych meczów ani statystyk.

## Zakres fizycznego kolektora

- Odrębny skrypt `scripts/kb3_historical_pitchapi_backfill.py`, baza SQLite `data/research/historical_multistat/observations.sqlite` oraz szyfrowane paczki `data/pit_sidecar/historical_multistat/YYYY-MM-DD/run-ID/`.
- Osiem dotychczasowych lig z izolowanego M0: ESP/ITA/GER/FRA/NED/BEL/TUR/POL, a **dodatkowo odrębnie UEFA Champions League**, jeżeli jest jednoznacznie dostępna w źródłowym katalogu i `is_free`. Brak odczytu angielskiej Premier League 2026/27 TEST; brak domyślnego przenoszenia wskaźników LM z lig krajowych.
- Katalog dostawcy → terminarze rzeczywistych sezonów → zakończone mecze → `matches.stats(match_id)` i `matches.shots(match_id)`. Jedno uruchomienie maksymalnie **48 wcześniej nieprzetworzonych meczów** / **150 zapytań**. Naprzemienne kolejki liga–sezon zapewniają postęp zarówno danych z bieżącego sezonu, jak i 2024/25 oraz 2025/26.
- Zachowujemy statystyczne klucze i wartości źródłowego pełnego meczu (`period=All`) z podziałem gospodarze/goście, **także poza xG**. Nie deklarujemy natomiast pobierania składów, kontuzji ani kursów: do tego są potrzebne dodatkowe osobno zweryfikowane endpointy i kontrole czasu.
- Natywne `expected_goals` akceptujemy tylko po kontroli identyfikatora `match_id` i stron `home_team_id` / `away_team_id`, pełnego okresu oraz zgodności sumy `shots.expected_goals` ze `stats.expected_goals` (tolerancja 0.15 na każdą stronę). **Brak to NULL, nie zero.** Pozostałe statystyki mogą być zachowane niezależnie od niekompletnego xG, ze stanem braku.
- Każda udana odpowiedź dostawcy ma `observed_at`, SHA256 i łańcuch dowodowy. Kompletny surowy pakiet otrzymany z provider przechowywany **wyłącznie w RSA/AES-GCM** z istniejącym kluczem publicznym właściciela; odrębny SQLite ma zweryfikowane pola do przyszłej analizy, a raport publiczny tylko liczebności, kategorie i nazwy kluczy. Baza odmawia aktualizowania i kasowania starych obserwacji. Każde uruchomienie ma oddzielne ID i nie nadpisuje poprzedniego pakietu.
- Dane mają `RECONSTRUCTED_FROM_LATER_OBSERVATION`, a NIE historycznie certyfikowany `provider_first_published_at`. Szczególnie dla lat 2023–2025 nie możemy twierdzić, że dzisiejsze pobranie dowodzi daty publikacji 2024 r. Nie używać bieżącego wyniku docelowego spotkania jako jego dawnej cechy.
- W tym etapie **nie trenujemy CatBoost i nie zmieniamy M0 ani kalibratora**. Historię trzeba dopiero przekształcić w chronologiczny zbiór 5/10/15 i osobny eksperyment CatBoost xG vs bez xG; backtest oznaczyć jako retrospektywny, z brakami źródłowego PIT. Formalne FIT100/HOLDOUT50 i GATE16/17 pozostają bez zmian.

## Harmonogram i granice

GitHub Actions `.github/workflows/kb3-historical-pitchapi-backfill.yml`:
- PR: wyłącznie offline, zero odczytów płatnego API i sekretów.
- `main` po zmianie skryptu/workflow: pierwszy rzeczywisty, izolowany przebieg po PASS CI, bez ingerencji w inne workflow.
- Codziennie 02:15, 10:15 i 18:15 UTC oraz `workflow_dispatch`, jeden writer naraz; zapis zaszyfrowanych źródeł i SQLite w prywatnym `main`. Są to rzeczywiste procesy GitHub Actions, a nie obietnica pracy asystenta w tle.
- Ograniczamy liczbę zapytań jednego uruchomienia z powodów niezawodności i przerwania pracy; zgodnie z dyspozycją właściciela nie traktujemy dawnych 33 jako budżetowego limitu tego nowego strumienia. Obowiązują realne zasady dostawcy, blokady dostępu i brak zgody na nowe opłaty.
- Brak niezależnego szyfrowanego offsite backupu i brak formalnego odtworzenia (restore) tego strumienia: do osobnego odbioru.

## Bramki odbioru i rzeczywiste dowody

1. Testy offline potwierdzają 8 lig + izolowane UCL, brak ENG/TEST, status finished co najmniej 3h, brak wyników przyszłego meczu, brak duplikatów, kontrolę tożsamości, xG shots/stats, obecność pozostałych statystyk, niezmienność SQLite i niepoświadczoną historyczną publikację.
2. Przed opisaniem pobranych liczb jako **REAL** trzeba odczytać zakończony GitHub Actions job na `main` i jego `HISTORICAL_BACKFILL_REPORT.json`, przechowany `HISTORICAL_SOURCE.enc`, manifest oraz rzeczywistą liczbę nowych wierszy bazy.
3. Nie wolno interpretować `48` jako 48 pomyślnie pobranych w każdym cyklu: może być mniej, mogą wystąpić braki provider/API, niepowtarzalne kursy i inne błędy jakości.
4. Przed szkoleniem z xG: wyliczyć pokrycie faktycznych **ostatnich** 5/10/15 meczów każdego zespołu na konkretny `cutoff`; nie wybierać pięciu dowolnych meczów z xG i nie dopowiadać braków. Potem stworzyć chronologiczny TRAIN/VALIDATION oraz niezmieniony TEST i porównać Brier/log loss.

**Status przy przygotowaniu dokumentu:** IMPLEMENTACJA W PR, rzeczywiste pobranie i parametry należy potwierdzić osobnym odbiorem; GATE16 i GATE17 nadal PENDING.
