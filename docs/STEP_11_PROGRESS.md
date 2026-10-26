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


## 26.10.2026 — rozbudowa ELO o historię między sezonami (GATE11 NADAL PENDING)

- Silnik `src/kb3_features.py` v0.2: poprzednie sezony tej samej **ligi/competition_id** są dopuszczane do historii ELO i cech rolling tylko przy spełnieniu dotychczasowej bramki czasu i mapowania. Sezony z przyszłości i inne ligi nie mogą wejść do cech.
- `EloParameters` to niemutowalna konfiguracja z walidacją zakresów: rating startowy 1500, K=20, przewaga domowa 65, skala 400, zachowanie ratingu między sezonami 0.85. **Wszystkie wartości są PROWIZORYCZNE, nie dopasowane na TRAIN**. Żadne przeszukiwanie K/H, fit ani trening nie odbywają się w kroku 11.
- Korekta sezonowa: `R_new_season = 1500 + (R_old_season-1500) * retention**number_of_seasons`. Dotyczy wyłącznie chronologicznie wcześniejszych sezonów, również gdy klub opuści ligę na kilka lat. Brak historii w lidze nie uprawnia do imputowania meczów rozegranych w innych rozgrywkach.
- Nowe liczności `*_elo_games_available` i `*_prior_seasons_games_available`, jawny `elo_parameters`, `elo_parameter_status`, sezon w `lineage`; hash cech obejmuje wybraną wersję parametrów.
- Sześć dodatkowych testów syntetycznych: kontynuacja ratingu, izolacja konkurencyjnej ligi, przyszły sezon, przerwa wieloletnia, walidacja parametrów, wpływ parametrów na hash.
- Ważne ograniczenie: przy faktycznej bazie pilota nadal **tylko PL 2024/25 / 380 meczów**. Test integracyjny obejmujący **dwa rzeczywiście importowane sezony** oraz ustalenie archiwalnej dostępności informacji pozostają otwarte. Dokładne liczby rzeczywiście sprawdzonych testów CI należy odczytywać z biegu GitHub Actions, nie z tej deklaracji.
- Nie zmieniamy statutu `training_allowed=false`, `verified`/ `replay`, bramek jakości ani wznowienia kroku 12. Bez automatycznego awansu GATE11.

## Potwierdzony pilotaż dwóch sezonów — 26.10.2026

- [GitHub Actions #40289840095](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40289840095) **SUCCESS**: trzy zadania `offline-tests`, `pilot-380`, `pilot-760` zakończone powodzeniem.
- **58/58** testów offline PASS (19 Step11: 11 początkowych + 6 dla ELO + 2 integracyjne; 39 regresyjnych Step08–10). Oddzielnie: **380/380** w dotychczasowym pilocie i **760/760** w nowym teście importu dwóch zakończonych sezonów Premier League (2023/24 i 2024/25).
- Dwa sezony: **23 różne drużyny**, bez dubli przy dwukrotnym imporcie; 3 kontrolne mecze z sezonu 2024/25 miały po 76 wcześniejszych udziałów obu drużyn z poprzedniego sezonu.
- Drugi pilot działał **wyłącznie w tymczasowej przestrzeni GitHub Actions**. **Nie utworzono ani nie zapisano trwałego zaszyfrowanego backupu bazy 760 meczów**. Baza trwale zabezpieczona wcześniej nadal obejmuje jednosezonowy pilot 380. Artefakty GitHub Actions zawierają wyłącznie zliczenia i hashe źródła, nie bazę czy wiersze spotkań.
- `verified`: historyczne mecze bez wiarygodnych timestampów nadal nie są certyfikowane; `replay` to retrospekcja, nie poprawne historyczne zamrożenie przedmeczowe. Brak autentycznych xG historycznych w bazie. **GATE11 nadal PENDING; 10/29, training_allowed=false.**
- Do wykonania przed odbiorem: trwałe bezpieczne archiwum rozszerzonej bazy zgodne z uprawnieniami dostawcy, szersze źródła, realne snapshoty z udokumentowaną dostępnością i sprawdzenie xG/pokrycia, niezależna kontrola GATE11.
