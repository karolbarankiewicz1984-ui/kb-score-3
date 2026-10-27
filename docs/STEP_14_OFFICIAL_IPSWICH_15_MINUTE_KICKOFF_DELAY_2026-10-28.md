# Krok 14 — wyjaśniona jedyna rozbieżność czasu w 1140 historycznych meczach

**Ustalenie z 28 października 2026, na podstawie jednego autentycznego lokalnego audytu właściciela oraz oficjalnych źródeł.**

## Co zostało potwierdzone?

- Premier League, **Ipswich Town – Everton**, **19.10.2024**, 2024/25, TRAIN.
- Pierwotny termin przedmeczowy: **15:00 BST = 14:00 UTC**, zapisany jako termin w zamrożonej publicznej referencji `OpenFootball`.
- Rzeczywisty początek po opóźnieniu: **15:15 BST = 14:15 UTC**, zapisany przez oryginalny PitchAPI.
- Powód: **lokalny problem elektryczny/IT na Portman Road, który zakłócił pracę bramek wejściowych dla kibiców**. Klub ogłosił przesunięcie rozpoczęcia meczu o dokładnie 15 minut.

Dowody z niezależnych źródeł:

1. Ipswich Town, oficjalny komunikat klubowy, **19.10.2024**, informuje o nowym początku o 15:15 BST i przyczynie: https://www.itfc.co.uk/news/2024/october/19/everton-kick-off-delayed/
2. Premier League, oficjalny raport spotkania, wprost podaje 15-minutowe opóźnienie spowodowane awarią IT: https://www.premierleague.com/en/news/4149676/ipswich-town-fc-v-everton-fc-premier-league
3. Premier League, opublikowany **06.08.2024** oryginalny terminarz z meczem Ipswich–Everton w grupie 15:00 BST: https://www.premierleague.com/en/news/4076999
4. Reuters, niezależny raport **19.10.2024**, potwierdza termin 15:00 przesunięty na 15:15 z powodu problemu z wejściem na stadion: https://www.reuters.com/sports/soccer/ipswich-v-everton-delayed-due-turnstile-issue-2024-10-19/

Klasyfikacja: **`DOCUMENTED_SCHEDULED_KICKOFF_VS_ACTUAL_KICKOFF_DELAY`**, a nie błędny zespół, native fixture_id, UTC DST lub niezgodna tożsamość.

## Konsekwencja dla 1140 i dla zabezpieczeń PIT

W oryginalnym audycie lokalnym porównano 1140 prawdziwych rekordów PitchAPI ze źródłem zewnętrznym. **1139/1140** miało jednocześnie te same zespoły i dokładny czas, **1/1140** miał tę samą parę i czas rozpoczęcia przesunięty o 15 minut. Odtąd ta jedna rozbieżność posiada niezależne wyjaśnienie, ale **nie zmieniamy** żadnego z oryginalnych plików danych, hashów, ich redakcji ani starych prognoz. Nie wolno przerabiać 1139/1140 dokładnych UTC na fikcyjne 1140/1140 bezwarunkowych identycznych godzin. Otrzymujemy **1139 identycznych godzin i 1 zweryfikowane przesunięcie czasu**, razem **1140 zweryfikowanych tożsamości historycznych par**.

Dla odtworzenia przedmeczowych cech historycznych w tym jednym meczu zalecana reguła jest **konserwatywna i bardziej restrykcyjna niż rzeczywisty późniejszy kickoff**: do badań `as-of` przyjmujemy jedynie dowody o `observed_at_utc < 2024-10-19T14:00:00Z`. Nie dopuszczamy automatycznie danych pozyskanych między 14:00 a 14:15 UTC, ponieważ pierwotny zakres i możliwość wiedzy o opóźnieniu wymagają odrębnego niezależnego dowodu czasu. Sam fakt przesunięcia rozpoczęcia nie certyfikuje żadnego brakującego źródłowego wejścia Elo, formy lub xG. Zasada ma charakter **technicznego bezpiecznika dla przyszłych badań**, nie zmienia formalnej oryginalnej metodologii.

Zamrożony [bezpieczny dokument dowodowy](../data/audits/STEP14_IPSWICH_EVERTON_VERIFIED_KICKOFF_DELAY_2026-10-28.json), [weryfikator wyjątku i ograniczenia cutoff](../src/kb3_step14_verified_kickoff_delay.py), [7 testów](../tests/test_step14_verified_kickoff_delay.py). Weryfikator odmówi podmianie drużyn, godzin, stałego źródła oraz bezprawnej zmianie `training_allowed`; **nie odszyfrowuje klucza RSA w CI**, a autentyczne nazwy obu klubów i różnica 15 minut pochodzą z wcześniejszego wyniku lokalnego właściciela.

**Formalnie nadal 13/29, krok 14 W REALIZACJI, GATE14 PENDING, pełny PIT TRAIN 0/760 i VALIDATION 0/380.** Nie użyto TEST, brak treningu produkcyjnego M1, bez zmian M0 i 20 zamrożonych prognoz, zero płatnych wywołań PitchAPI.
