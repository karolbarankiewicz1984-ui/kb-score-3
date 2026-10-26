# KB Score 3.0 — KROK 11 / START / GATE11 PENDING

**Data:** 26.10.2026. **Status:** W REALIZACJI, NIE ZALICZONO. **Postęp zatwierdzony:** 10/29.

## Pierwsza implementacja

- src/kb3_features.py: ELO (roboczo start 1500, K=20, przewaga gospodarzy 65), forma ostatnich 5/10/15 gier, osobno dom/wyjazd; punkty, gole, ELO dawnych przeciwników, liczba dni od poprzedniego meczu, realne xG/xGA.
- tests/test_step11_features.py: negatywne testy cutoff, przyszłych wyników, danych docelowego meczu, spóźnionej publikacji, niezatwierdzonego mapowania, konfliktu xG, błędnego jednoczesnego meczu.
- scripts/step11_features_audit.py: porównanie trybów dla 380 meczów pilotażu z eksportem wyłącznie zliczeń.
- .github/workflows/kb3-step11-features.yml: testy offline i kontrolny import 380 meczów z aktywnego GitHub Secret API-Football. Bez wycieku bazy do artefaktów.

## Katalog cech i czasu dostępności

| Cecha | Źródło i bramka | Brak danych |
|---|---|---|
| home/away_elo | wcześniejsze zaakceptowane wyniki 90 minut, status STRICT+APPROVED | prior 1500 i games_available=0 |
| all/venue_5/10/15_points_avg | wcześniejsze wyniki w tym sezonie | NULL, n i missing_flags |
| all/venue_5/10/15_gf_avg / ga_avg | wcześniejsze bramki zdobyte / stracone | NULL, n i flaga |
| all/venue_5/10/15_opponent_elo_avg | ELO rywala przed dawnym meczem | NULL, flaga |
| all/venue_5/10/15_xg/xga_avg | wyłącznie rzeczywiste obserwacje xG z pochodzeniem i czasem | NULL, nie 0; xg_n i xga_n |
| days_since_last_kickoff | data ostatniego dopuszczonego meczu | NULL |
| elo_home_minus_away | poprzedni rating dwóch drużyn | roboczy prior, licznik historii |

Tryb **verified** dopuszcza wcześniejsze wyniki tylko z dowodem publikacji i
odczytu przed cutoff oraz zatwierdzonym ID. Bez certyfikacji samego snapshotu
meczu docelowego cały wynik ma klasę NOT_VERIFIED; training_allowed=false.

Tryb **replay** jest wyłącznie retrospektywną symulacją dla poprzednich
meczów starszych o minimum 48 godzin. RETROSPECTIVE nie oznacza realnej
historycznej dostępności danych. training_allowed=false. Oba tryby mają
SHA-256, lineage i flagi NULL; nie uwzględniają kursów ani wyniku docelowego.

## Co nadal blokuje odbiór

W SQLite obecnie tylko **380 rzeczywiście importowanych meczów** PL 2024/25;
**10 679** to dotychczas liczba w źródłowym katalogu API, nie liczba
rekordów w treningowej bazie. Brak archiwum point-in-time, pełnych statystyk
i xG. ELO K i przewaga gospodarzy są robocze i nie zostały wytrenowane.

Wymagany niezależny audyt GitHub Actions (11 testów syntetycznych + regresja
i realny pilot), zapis dowodów w PLAN/ZMIANY oraz źródłowym Google Docs.
**Na razie START, NIE PASS.** Bez dodatkowych zakupów, bez zmian w KB2.1,
API Market i MultiModel, bez modeli ML i automatycznych typów.
