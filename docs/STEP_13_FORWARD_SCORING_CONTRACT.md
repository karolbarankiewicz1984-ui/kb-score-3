# KB Score 3.0 — krok 13: zamrożona metoda oceny pierwszych 10 prognoz forward

**Protokół zapisany 27.10.2026, zanim zaczną się mecze (31.10–02.11.2026).** To część **oryginalnego kroku 13**, NIE nowy punkt w 29-etapowym planie. Żadnego strojenia na wynikach ani rozpoczęcia CatBoost.

## Przedmiot i dowód

Dokładnie 10 prognoz 1X2/Poisson z [pierwszego autentycznego snapshotu prematch](../data/forecasts/STEP13_FIRST_PROSPECTIVE_PREMATCH_2026-10-27.json), zamrożonego `2026-10-27T06:12:08.707287Z`:

- Niepodmienialny podpis oryginalnego JSON: `9c346f79b1868fd1cb0d4d4ffa066f6f1629e09bbc6ce0454c5c8901e7645389`.
- TRAIN: 760, dotychczasowa retrospektywna VALIDATION: 380 (nie odczytywana przez pierwotny forward snapshot).
- Meczów do oceny **dokładnie 10**. Są w chronionym holdoucie `TEST 2026/27`; po obejrzeniu tych 10 wyników staną się one otwartym *podzbiorem oceny*, nie całkowicie nietkniętym TEST. Pozostałych **370 meczów TEST nie wolno pobierać ani włączać do tego audytu**, nawet jeśli już się odbyły. Nie używać nowo otwartych 10 wyników do strojenia lub wyboru modelu.
- Pierwszy rzeczywisty raport nie używał zakończonych meczów TEST do cech ELO. Celowo nieaktualne ratingi kończą się na czerwcu 2025 — ograniczenie jakości pozostaje niezmienione.

## Co wolno dopiero PO meczach

**Bezpieczny najwcześniejszy cutoff:** `2026-11-02T23:00:00Z`, czyli 3 godziny po planowanym ostatnim kickoff 02.11 20:00 UTC; w praktyce bezpieczniej 3.11 po potwierdzeniu zakończenia wszystkich 10 spotkań. Samo upłynięcie 3 godzin nie dowodzi, że mecz rzeczywiście się odbył: każdy musi mieć status `finished` i wynik 90 minut. Postponed/cancelled/incomplete -> **fail closed**, brak częściowego raportu.

Po zakończeniu wymagane jest **osobne źródłowo udokumentowane pobranie** dokładnie 10 wyników z PitchAPI; każdy rekord ma mieć: `fixture_id`, `home_team_id`, `away_team_id`, `kickoff_utc`, `status='finished'`, `goals_home_90`, `goals_away_90`, `observed_at_utc`, `source='PitchAPI'`, `capture_sha256`. Jeden `fixture_id` może wystąpić dokładnie raz. Najpóźniejszy odczyt nie może wyprzedzać czasu uruchomienia oceny. Rekordy inne niż tych 10 meczów są zabronione.

**UWAGA:** Kod [`src/kb3_step13_forward_score.py`](../src/kb3_step13_forward_score.py) jest czystą funkcją matematyczną i kontrolą wejść, **nie pobiera dziś ani później żadnych wyników i nie jest automatem harmonogramowym**. Czas podany przez przyszłego kolektora i jego hash to jeszcze nie niezależnie zweryfikowane źródło; przy faktycznym pobraniu należy zapewnić autentyczny ledger `observed_at`, integralność/archiwizację źródła i identyfikację dokładnie tych 10 ID. Dopiero wtedy funkcja może policzyć realne metryki.

## Zamrożone miary (bez możliwości późniejszej zmiany pod wynik)

1. `top1_1x2_accuracy` i liczba poprawnych wskazań klasy z największym P.
2. `multiclass_1x2_logloss`: `-mean(log(P rzeczywistego 1/X/2))`; mniej = lepiej.
3. `multiclass_1x2_brier_sum3`: średnia sumy kwadratów odchyleń trzech P od one-hot; mniej = lepiej.
4. `top_class_1x2_ece_5bins_exploratory`: 5 koszyków najwyższej prognozowanej szansy; **n=10 jest za małe do wiarygodnego wnioskowania o kalibracji**.
5. `goal_poisson_nll_per_match_two_teams` i `goal_mae_per_team`: dodatkowa diagnostyka rozkładu goli Poissona na wynikach 90 min. **Oczekiwane gole Poissona nie są prawdziwym dostarczonym xG ze strzałów.**

Funkcja musi porównać **dokładne stare prawdopodobieństwa** z podpisanego pliku (a nie nowe prognozy obliczone po meczu). Zmiana pliku, choćby jednej szansy, kolejności dopuszczanych ID, godzin, statusu, nazwy drużyny pod innym ID, nieprawidłowego wyniku albo wstrzyknięcie kursów kończy się odmową. Nie ma automatycznego zastępowania brakujących wyników czy przeliczania tylko udanej części.

## Bezpieczeństwo i status

- Dziś (27.10) uruchamiamy **wyłącznie sztuczne unit testy** z fikcyjnymi rezultatami. Żadne etykiety TEST nie są otwierane.
- W przyszłości wynik będzie **wyłącznie zagregowany**: log loss, Brier, n=10, poprawne wskazania, ECE opisowe, bramki dowodowe. Bez surowych wyników w publicznym raporcie, bez indywidualnych etykiet i bez zmiany oryginalnego snapshotu.
- **Nie** wystarczy 10 meczów, by wiarygodnie wybrać EXPANDING vs ROLLING, ani by ogłosić stabilną dokładność ELO+Poisson. Nawet po ocenie nadal mogą pozostawać ograniczenia PIT i kalibracji.
- Formalnie `training_allowed=false`, `gate13_pass=false`, `step14_started=false`; **12/29** ukończonych, KROK13 W REALIZACJI.

`<SOURCE_HASH 9c346f79b1868fd1cb0d4d4ffa066f6f1629e09bbc6ce0454c5c8901e7645389>` jest dodatkowo przypięty bezpośrednio w kodzie scorera.
