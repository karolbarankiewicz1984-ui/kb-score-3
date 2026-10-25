# KB Score 3.0 — Etap 05: audyt API-Football

Wykonano: 2026-10-25T17:49:30.142971+00:00
**Stan:** DATA_COLLECTED — samo wykonanie nie oznacza GATE PASS.

## Limity i odczyt konta (bez danych osobowych)

- Plan: Pro, active=True
- Zapytania tego testu: 112/125
- Dzienny limit / pozostałe po teście: 7500 / 6816
- Maksymalny limit na minutę: 300
- Błędy API: 0
- Przebadane kombinacje z terminarzem: 30 / 30
- Liczba meczów na pobranych listach: 10679
- Próbki statystyk (2 drużyny): 60 / 60

## Pokrycie liga × sezon (liczby z API, nie estymacje)

| Liga | Sezon | Zgłoszono statystyki | Mecze | Zakończone | Wyniki | Próbki statystyk | Faule/rożne/kartki/strzały — obie drużyny |
|---|---:|:---:|---:|---:|---:|:---:|---|
| Premier League | 2021 | TAK | 380 | 380 | 380 | 2/2 | 2/2/2/2 |
| Premier League | 2022 | TAK | 380 | 380 | 380 | 2/2 | 2/2/2/2 |
| Premier League | 2023 | TAK | 380 | 380 | 380 | 2/2 | 2/2/2/2 |
| Premier League | 2024 | TAK | 380 | 380 | 380 | 2/2 | 2/2/2/2 |
| Premier League | 2025 | TAK | 380 | 380 | 380 | 2/2 | 2/2/2/2 |
| Premier League | 2026 | TAK | 380 | 79 | 79 | 2/2 | 2/2/2/2 |
| La Liga | 2021 | TAK | 380 | 380 | 380 | 2/2 | 2/2/2/2 |
| La Liga | 2022 | TAK | 380 | 380 | 380 | 2/2 | 2/2/2/2 |
| La Liga | 2023 | TAK | 380 | 380 | 380 | 2/2 | 2/2/2/2 |
| La Liga | 2024 | TAK | 380 | 380 | 380 | 2/2 | 2/2/2/2 |
| La Liga | 2025 | TAK | 380 | 380 | 380 | 2/2 | 2/2/2/2 |
| La Liga | 2026 | TAK | 380 | 96 | 96 | 2/2 | 2/2/2/2 |
| Serie A | 2021 | TAK | 380 | 380 | 380 | 2/2 | 2/2/2/2 |
| Serie A | 2022 | TAK | 381 | 381 | 381 | 2/2 | 2/2/2/2 |
| Serie A | 2023 | TAK | 380 | 380 | 380 | 2/2 | 2/2/2/2 |
| Serie A | 2024 | TAK | 380 | 380 | 380 | 2/2 | 2/2/2/2 |
| Serie A | 2025 | TAK | 380 | 380 | 380 | 2/2 | 2/2/2/2 |
| Serie A | 2026 | TAK | 380 | 78 | 78 | 2/2 | 2/2/2/2 |
| Bundesliga | 2021 | TAK | 308 | 308 | 308 | 2/2 | 2/2/2/2 |
| Bundesliga | 2022 | TAK | 308 | 308 | 308 | 2/2 | 2/2/2/2 |
| Bundesliga | 2023 | TAK | 308 | 308 | 308 | 2/2 | 2/2/2/2 |
| Bundesliga | 2024 | TAK | 308 | 308 | 308 | 2/2 | 2/2/2/2 |
| Bundesliga | 2025 | TAK | 308 | 308 | 308 | 2/2 | 2/2/2/2 |
| Bundesliga | 2026 | TAK | 306 | 62 | 62 | 2/2 | 2/2/2/2 |
| Ligue 1 | 2021 | TAK | 382 | 382 | 382 | 2/2 | 2/2/2/2 |
| Ligue 1 | 2022 | TAK | 380 | 380 | 380 | 2/2 | 2/2/1/2 |
| Ligue 1 | 2023 | TAK | 308 | 308 | 308 | 2/2 | 2/2/2/2 |
| Ligue 1 | 2024 | TAK | 308 | 308 | 308 | 2/2 | 2/2/2/2 |
| Ligue 1 | 2025 | TAK | 308 | 307 | 307 | 2/2 | 2/2/2/2 |
| Ligue 1 | 2026 | TAK | 306 | 66 | 66 | 2/2 | 2/2/2/2 |

## Kontrole szczegółowe — próbki 2025

| Liga | Rodzaj | Odpowiedź | Rekordy |
|---|---|---|---:|
| Premier League | fixtures/lineups | RETURNED_LIST | 2 |
| Premier League | fixtures/events | RETURNED_LIST | 17 |
| Premier League | fixtures/players | RETURNED_LIST | 2 |
| La Liga | fixtures/lineups | RETURNED_LIST | 2 |
| La Liga | fixtures/events | RETURNED_LIST | 16 |
| La Liga | fixtures/players | RETURNED_LIST | 2 |
| Serie A | fixtures/lineups | RETURNED_LIST | 2 |
| Serie A | fixtures/events | RETURNED_LIST | 17 |
| Serie A | fixtures/players | RETURNED_LIST | 2 |
| Bundesliga | fixtures/lineups | RETURNED_LIST | 2 |
| Bundesliga | fixtures/events | RETURNED_LIST | 18 |
| Bundesliga | fixtures/players | RETURNED_LIST | 2 |
| Ligue 1 | fixtures/lineups | RETURNED_LIST | 2 |
| Ligue 1 | fixtures/events | RETURNED_LIST | 24 |
| Ligue 1 | fixtures/players | RETURNED_LIST | 2 |

## Kursy — wyłącznie obecne

Bieżący endpoint: CURRENT_SNAPSHOT_ONLY; wynik strony: 10; liczba stron: 3.

**NIE oznacza to dostępności historycznych kursów**. Dostawca opisuje historię kursów przedmeczowych około 7 dni.

## Znane ograniczenia

- League-season declared coverage is not per-fixture completeness.
- Per-fixture statistics are sampled; they are not an exhaustive count of statistical completeness.
- An absent provider field means NOT_AVAILABLE, never an actual zero.
- Historical odds older than the provider's retention window are not authenticated prematch snapshots.
- Fixture results retrieved now do not establish that earlier snapshots existed before kickoff.
- The project has not trained a model; this is only a read-only source audit.

## Decyzja odbioru

**GATE 05: DO ODBIORU / PENDING**, dopóki nie zweryfikowano liczebności, próbek i dowodów.
Następny krok po PASS: 06 — audyt PitchAPI. Brak kodu modelu i brak treningu.
