# KB Score 3.0 — decyzja 2026-11-23: FORWARD FIRST, rygor PIT bez blokowania badań

**Decyzja właściciela:** realizujemy wariant B: priorytet dla nowych, rzeczywiście zamrożonych prognoz i ich późniejszych rozliczeń. Nie uzależniamy prac badawczych nad M0 i CatBoost Challenger od odzyskania kompletnej historii pierwszej publikacji cech PitchAPI 2023–2025. **Nie rezygnujemy z kontroli przecieków danych.** Ten dokument nie zatwierdza nowego Championa ani produkcyjnego M1.

## Punkt wyjścia i rozróżnienie bramek

- [Audyt oryginalnego PIT 2026-11-22](../data/audits/STEP14_INDEPENDENT_RECHECK_2026-11-22.json): 1140/1140 native fixture identity, ale 0/760 certyfikowanych wierszy oryginalnego TRAIN, 0/380 oryginalnej VALIDATION; brak oryginalnej pierwszej publikacji PitchAPI team-xG oraz niezależnego PASS wszystkich 159 pól (121 cech + 38 flag). `GATE14_ORIGINAL_STRICT_NATIVE_PIT=PENDING`.
- Osobna [decyzja i odbiór GATE14-B z 2026-10-29](STEP_14_GATE_B_FORMAL_ACCEPTANCE_2026-10-29.md) pozostaje ważna: badawczy CatBoost M1-R BASE z retrospektywną rekonstrukcją, **bez** twierdzenia o pełnym oryginalnym PIT i **bez** promocji do produkcji. Formalny etap 14 według wariantu B został wcześniej zaliczony. Nie mieszać tego faktu ze statusem rygorystycznej historycznej certyfikacji.
- [Audyt M0/HOLDOUT 2026-11-23](KB3_HOLDOUT50_MODEL_DECISION_AUDIT_2026-11-23.md): 268 host-attested prognoz M0, 208 rozliczeń, FIT100 + 50 rozłącznych HOLDOUT, osobny audyt read-only. M0/Champion oraz chroniony Premier League 2026/27 TEST bez zmian. Formalne GATE16/17 pozostają do niezależnego odbioru.

## Kolejność operacyjna od 2026-11-23

**P0 — nieprzerwane prognozy prospektywne:**
1. Zachować istniejące harmonogramy forecast/settlement M0, bieżące snapshots i serwerowe potwierdzenie `feature_snapshot/captured_at/frozen_at < cutoff < kickoff`. Utrwalać wersję modelu, mapowanie ID, SHA źródła, missingness, embargo oraz wyniki dopiero po meczu.
2. Nie blokować **całego** procesu z powodu *opcjonalnego* brakującego xG, strzałów, fauli, kart czy rożnych. Zapisywać `NULL + reason/mask`, kontynuować wyłącznie rynki i modele posiadające komplet ich **obowiązkowych** danych. Nigdy nie zamieniać `NULL` na 0 ani nie dopisywać statystyk po cutoff do starej migawki.
3. Dla dowolnego Challengera CatBoost prowadzić osobne wersjonowane prognozy `research/shadow` i porównania na **identycznych rzeczywistych spotkaniach** z M0. Sam retrospektywny fit nie uprawnia do oznaczenia wyniku jako forward ani do awansu.

**P1 — jakość, porównanie i kalibracja:**
1. Nadal prowadzić niezależny, read-only przegląd FIT100/HOLDOUT50; Brier sum3, log loss, ECE, trafność 1X2, podział na ligi i chronologiczne tygodnie. Nie dostrajać na HOLDOUT i nie dobierać zwycięzcy na podstawie pojedynczej małej próbki.
2. Utrzymywać ochronę ENG TEST, nie zmieniać samoczynnie Championa ani progów modelu; ewentualna promocja tylko po osobnym audycie, dowodzie przewagi i akceptacji właściciela.

**P2 — archiwalna pierwsza publikacja PitchAPI:**
1. Zakończyć cykl bezterminowych prób certyfikacji tych samych starych pól bez **nowych** dowodów. Zachować dotychczasowe źródła, SHA, historyczne raporty FAIL/PENDING i możliwość powrotu.
2. Historyczny badawczy backfill `kb3-historical-pitchapi-backfill.yml` ograniczyć z dwóch automatycznych uruchomień dziennie do **jednego w tygodniu: środa 03:15 UTC**. Pozostawić `workflow_dispatch`, regresje offline i możliwość szybkiej kontroli, gdy pojawi się rzeczywisty nowy dowód lub pilna potrzeba badawcza. To jest *zbieranie/historyczny research*, nie potwierdzenie oryginalnego `published_at`.
3. Pierwotną certyfikację `first_published_at` wznowić intensywniej tylko przy wiarygodnym nowym materiale od PitchAPI lub niezależnej wersjonowanej archiwizacji (oryginalne bajty, SHA, semantyka, match/team/period, czas dostępności przed historycznym cutoff). FPL/Opta player-xG i współcześnie pobrany PitchAPI team-xG nie stanowią zamiennych dowodów.
4. Badania retrospektywne oznaczać `RETROSPECTIVE_RESEARCH_NOT_PIT` (lub obowiązującym równoważnym statusem); nigdy nie przyznawać na tej podstawie oryginalnego `PIT PASS`.

## Twarde ograniczenia / koszty

- Brak zmiany kodu M0, wagi CatBoost, ustawień forecast/settlement, FIT/HOLDOUT, chronionego TEST, formalnych bramek odbioru i istniejących dowodów.
- Brak zakupu usług API i brak nowej zgody na wydatek. Ograniczenie harmonogramu backfillu oszczędza powtarzalne pobrania historyczne, ale nie gwarantuje liczby wywołań przy manualnych uruchomieniach.
- Nie twierdzić, że powstały już nowe prognozy, że cięcie harmonogramu poprawiło metryki, ani że historyczne `published_at` zostały zdobyte. Zmiana harmonogramu wymaga sprawdzenia po commicie; skutki mierzyć w następnych rzeczywistych runach.

## Weryfikacja

Po zmianie sprawdzić w `.github/workflows/kb3-historical-pitchapi-backfill.yml`: dokładnie jeden cron `15 3 * * 3`, pozostawione `workflow_dispatch` i badawcze, chronione joby; niezależnie sprawdzić, że nie zmieniono pliku `kb3-step16-m0-720-eight-forward.yml`. W audycie następnego tygodnia porównać nowo zamrożone, kwalifikowane prognozy M0/Challenger, settlements, błędy danych i koszty API. To jest **decyzja priorytetów plus zmiana jednego harmonogramu**, nie odbiór produkcyjny modelu.
