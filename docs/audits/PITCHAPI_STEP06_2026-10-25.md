# KB Score 3.0 — Audyt PitchAPI, krok 06

Odczyt UTC: 2026-10-25T21:23:31.948304+00:00
Stan testu: AUDIT_COLLECTED; odbiór GATE 06 wymaga kontroli raportu.

## Wyniki zbiorcze

| Pozycja | Wynik |
|---|---:|
| target_rows | 30 |
| listed_rows | 24 |
| played_matches_sum | 7301 |
| shots_examined | 48 |
| complete_xg_samples | 48 |
| partial_or_missing_xg_samples | 0 |
| strict_verified_api_football_matches | 14 |
| candidate_alias_matches | 6 |
| provider_errors_total | 0 |
| PitchAPI calls | 73 / 110 |
| API-Football crosscheck calls | 24 / 45 |

## Liga × sezon — historia i xG próbek

| Liga | Sezon | W katalogu | Mecze rozegrane | Sprawdzono xG | Pełne xG | Sparowane dokładnie |
|---|---|:---:|---:|---:|---:|---:|
| Premier League | 2021/2022 | TAK | 380 | 2 | 2 | 1 |
| Premier League | 2022/2023 | TAK | 380 | 2 | 2 | 1 |
| Premier League | 2023/2024 | TAK | 380 | 2 | 2 | 0 |
| Premier League | 2024/2025 | TAK | 380 | 2 | 2 | 0 |
| Premier League | 2025/2026 | TAK | 380 | 2 | 2 | 0 |
| Premier League | 2026/2027 | TAK | 80 | 2 | 2 | 0 |
| La Liga | 2021/2022 | NIE | BRAK | 0 | 0 | 0 |
| La Liga | 2022/2023 | NIE | BRAK | 0 | 0 | 0 |
| La Liga | 2023/2024 | NIE | BRAK | 0 | 0 | 0 |
| La Liga | 2024/2025 | NIE | BRAK | 0 | 0 | 0 |
| La Liga | 2025/2026 | NIE | BRAK | 0 | 0 | 0 |
| La Liga | 2026/2027 | NIE | BRAK | 0 | 0 | 0 |
| Serie A | 2021/2022 | TAK | 380 | 2 | 2 | 1 |
| Serie A | 2022/2023 | TAK | 381 | 2 | 2 | 1 |
| Serie A | 2023/2024 | TAK | 380 | 2 | 2 | 1 |
| Serie A | 2024/2025 | TAK | 380 | 2 | 2 | 1 |
| Serie A | 2025/2026 | TAK | 380 | 2 | 2 | 1 |
| Serie A | 2026/2027 | TAK | 79 | 2 | 2 | 1 |
| Bundesliga | 2021/2022 | TAK | 306 | 2 | 2 | 0 |
| Bundesliga | 2022/2023 | TAK | 306 | 2 | 2 | 0 |
| Bundesliga | 2023/2024 | TAK | 306 | 2 | 2 | 1 |
| Bundesliga | 2024/2025 | TAK | 305 | 2 | 2 | 0 |
| Bundesliga | 2025/2026 | TAK | 306 | 2 | 2 | 0 |
| Bundesliga | 2026/2027 | TAK | 63 | 2 | 2 | 0 |
| Ligue 1 | 2021/2022 | TAK | 380 | 2 | 2 | 1 |
| Ligue 1 | 2022/2023 | TAK | 380 | 2 | 2 | 0 |
| Ligue 1 | 2023/2024 | TAK | 306 | 2 | 2 | 1 |
| Ligue 1 | 2024/2025 | TAK | 306 | 2 | 2 | 1 |
| Ligue 1 | 2025/2026 | TAK | 306 | 2 | 2 | 1 |
| Ligue 1 | 2026/2027 | TAK | 71 | 2 | 2 | 1 |

## Przykłady konkretnych meczów i mapowania

| Liga | Sezon | Pitch ID | Mecz | xG | Strzały | API-Football ID | Pairing |
|---|---|---|---|---|---:|---|---|
| Premier League | 2021/2022 | m_3nXDAl | Watford – Southampton | 1.05/1.75 | 22 | 710654 | EXACT_NAMES_DATE_SCORE |
| Premier League | 2021/2022 | m_1LLkxq | Aston Villa – Arsenal | 0.45/1.35 | 18 | BRAK | NOT_CHECKED |
| Premier League | 2022/2023 | m_2mXJPL | Aston Villa – Chelsea | 1.83/0.87 | 26 | 868046 | EXACT_NAMES_DATE_SCORE |
| Premier League | 2022/2023 | m_2vZSJE | West Ham United – Newcastle United | 0.98/3.28 | 22 | BRAK | NOT_CHECKED |
| Premier League | 2023/2024 | m_1tklpw | West Ham United – Everton | 0.68/0.81 | 22 | BRAK | AMBIGUOUS_OR_UNMATCHED |
| Premier League | 2023/2024 | m_2CzI3M | Chelsea – Burnley | 4.12/1.66 | 51 | BRAK | NOT_CHECKED |
| Premier League | 2024/2025 | m_4YzxPS | Liverpool – Brighton & Hove Albion | 1.66/1.0 | 29 | BRAK | AMBIGUOUS_OR_UNMATCHED |
| Premier League | 2024/2025 | m_1bWubG | AFC Bournemouth – Brentford | 1.66/0.83 | 28 | BRAK | NOT_CHECKED |
| Premier League | 2025/2026 | m_27nHGA | Tottenham Hotspur – Chelsea | 0.11/3.69 | 18 | BRAK | AMBIGUOUS_OR_UNMATCHED |
| Premier League | 2025/2026 | m_0Z4lMM | Brighton & Hove Albion – Arsenal | 0.82/0.46 | 18 | BRAK | NOT_CHECKED |
| Premier League | 2026/2027 | m_1rqNHl | Ipswich Town – Liverpool | 0.73/0.66 | 24 | 1557393 | ALIAS_CANDIDATE_UNVERIFIED |
| Premier League | 2026/2027 | m_3fEVzy | Everton – Chelsea | 0.42/1.47 | 24 | BRAK | NOT_CHECKED |
| Serie A | 2021/2022 | m_2VVIN1 | Sampdoria – Atalanta | 1.36/1.32 | 22 | 731680 | EXACT_NAMES_DATE_SCORE |
| Serie A | 2021/2022 | m_4VGhNd | Sassuolo – Spezia | 1.94/0.3 | 21 | BRAK | NOT_CHECKED |
| Serie A | 2022/2023 | m_3cPC20 | Lazio – Udinese | 0.8/0.86 | 20 | 881874 | EXACT_NAMES_DATE_SCORE |
| Serie A | 2022/2023 | m_3tptad | Sampdoria – Cremonese | 2.08/1.3 | 30 | BRAK | NOT_CHECKED |
| Serie A | 2023/2024 | m_23sPne | Monza – Udinese | 0.53/1.11 | 20 | 1052350 | EXACT_NAMES_DATE_SCORE |
| Serie A | 2023/2024 | m_1FJzB3 | Juventus – Genoa | 1.03/0.18 | 22 | BRAK | NOT_CHECKED |
| Serie A | 2024/2025 | m_4XSCYv | Atalanta – Monza | 1.24/0.1 | 20 | 1223685 | EXACT_NAMES_DATE_SCORE |
| Serie A | 2024/2025 | m_0vKJRS | Venezia – Napoli | 0.73/1.68 | 27 | BRAK | NOT_CHECKED |
| Serie A | 2025/2026 | m_3yTSEh | Torino – Pisa | 0.92/1.54 | 26 | 1377961 | EXACT_NAMES_DATE_SCORE |
| Serie A | 2025/2026 | m_1Uoard | Pisa – Cagliari | 2.49/1.22 | 24 | BRAK | NOT_CHECKED |
| Serie A | 2026/2027 | m_2We4l6 | Atalanta – Bologna | 0.17/1.34 | 22 | 1550098 | EXACT_NAMES_DATE_SCORE |
| Serie A | 2026/2027 | m_0dRaIx | Torino – Udinese | 2.51/0.71 | 27 | BRAK | NOT_CHECKED |
| Bundesliga | 2021/2022 | m_4cygKg | RB Leipzig – Greuther Fürth | 2.34/1.43 | 22 | 719422 | ALIAS_CANDIDATE_UNVERIFIED |
| Bundesliga | 2021/2022 | m_0m6qWu | Eintracht Frankfurt – Bochum | 1.89/1.09 | 22 | BRAK | NOT_CHECKED |
| Bundesliga | 2022/2023 | m_4dPD7D | Bochum – Eintracht Frankfurt | 0.61/0.88 | 24 | 871241 | ALIAS_CANDIDATE_UNVERIFIED |
| Bundesliga | 2022/2023 | m_3xeXZs | Schalke 04 – Bayer Leverkusen | 1.13/2.75 | 30 | BRAK | NOT_CHECKED |
| Bundesliga | 2023/2024 | m_3qHADt | Werder Bremen – Union Berlin | 0.79/0.58 | 18 | 1048958 | EXACT_NAMES_DATE_SCORE |
| Bundesliga | 2023/2024 | m_25Maiy | Mainz 05 – Bochum | 2.47/0.8 | 26 | BRAK | NOT_CHECKED |
| Bundesliga | 2024/2025 | m_4NVq7V | Holstein Kiel – FC Heidenheim | 1.1/1.28 | 28 | 1224055 | ALIAS_CANDIDATE_UNVERIFIED |
| Bundesliga | 2024/2025 | m_3s7rsD | Augsburg – Wolfsburg | 0.74/0.78 | 23 | BRAK | NOT_CHECKED |
| Bundesliga | 2025/2026 | m_3GpAxp | Union Berlin – Freiburg | 1.01/1.18 | 24 | 1388387 | ALIAS_CANDIDATE_UNVERIFIED |
| Bundesliga | 2025/2026 | m_4R8veJ | Borussia Dortmund – Augsburg | 2.57/0.84 | 23 | BRAK | NOT_CHECKED |
| Bundesliga | 2026/2027 | m_1GBuep | Schalke 04 – Bayern München | 0.21/2.1 | 19 | 1575156 | ALIAS_CANDIDATE_UNVERIFIED |
| Bundesliga | 2026/2027 | m_23lRyI | Schalke 04 – Mainz 05 | 0.44/2.03 | 19 | BRAK | NOT_CHECKED |
| Ligue 1 | 2021/2022 | m_2GU8Gn | Strasbourg – Saint-Étienne | 2.09/0.99 | 17 | 718449 | EXACT_NAMES_DATE_SCORE |
| Ligue 1 | 2021/2022 | m_1zILYV | Rennes – Metz | 3.75/0.7 | 23 | BRAK | NOT_CHECKED |
| Ligue 1 | 2022/2023 | m_3M6KxB | Nice – Troyes | 2.64/1.48 | 31 | BRAK | AMBIGUOUS_OR_UNMATCHED |
| Ligue 1 | 2022/2023 | m_2dxUUK | Brest – Toulouse | 1.8/1.24 | 26 | BRAK | NOT_CHECKED |
| Ligue 1 | 2023/2024 | m_2X67AH | Toulouse – Reims | 0.81/1.35 | 26 | 1044954 | EXACT_NAMES_DATE_SCORE |
| Ligue 1 | 2023/2024 | m_2PnPiH | Monaco – Lorient | 2.65/0.78 | 35 | BRAK | NOT_CHECKED |
| Ligue 1 | 2024/2025 | m_49yzrC | Lyon – Auxerre | 2.02/1.54 | 31 | 1213822 | EXACT_NAMES_DATE_SCORE |
| Ligue 1 | 2024/2025 | m_206Gsw | Lyon – Le Havre | 3.98/1.68 | 30 | BRAK | NOT_CHECKED |
| Ligue 1 | 2025/2026 | m_16dPEj | Lille – Metz | 2.91/1.31 | 33 | 1387774 | EXACT_NAMES_DATE_SCORE |
| Ligue 1 | 2025/2026 | m_1RwY2t | Strasbourg – Paris FC | 1.14/0.5 | 23 | BRAK | NOT_CHECKED |
| Ligue 1 | 2026/2027 | m_1WMWmb | Monaco – Marseille | 1.49/1.22 | 24 | 1552742 | EXACT_NAMES_DATE_SCORE |
| Ligue 1 | 2026/2027 | m_2U09kV | Troyes – Marseille | 1.14/1.27 | 20 | BRAK | NOT_CHECKED |

## Zastrzeżenia

- League catalog seasons and played match counts do not prove shot-xG availability for every fixture.
- Shot xG is a post-match label/history input for LATER matches only, not a prematch snapshot.
- Missing/null shot xG is never a legitimate numeric zero.
- Score/date and fuzzy team matches are suggestions, not verified one-to-one linkage.
- Historical fixture lists queried today do not prove data was available prematch.
- This is source audit, NOT a trained predictive model.

**Brak danych to nie zero.** xG dotyczy zakończonych historycznych spotkań, do budowy cech dla późniejszych spotkań używać tylko wcześniejszej historii.

**GATE 06: DO ODBIORU / PENDING** do czasu niezależnego potwierdzenia wyników.
