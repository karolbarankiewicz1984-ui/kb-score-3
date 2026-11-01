# KB Score 3.0 — kroki 1–4 po PR #128, 2026-11-01

## Status przed pracami

- Ostatni autentyczny M0 settle: \`2026-11-01 20:22:12 UTC\`, **60/100 FIT**, 75/75 przedmeczowych host proof, kolejnych 50 HOLDOUT jeszcze nie rozpoczęto. Ostatni native xG: 15 zaobserwowanych meczów, 0/29 komplet last5.
- Dotychczas nie było jeszcze **nowego forecast ani nowego native xG capture po merge 2026-11-01 20:23:03 UTC**. Sukces GitHub Actions na \`push\` nie oznacza nowych próbek, jeśli daily guard wykonał \`skip\`.

## 1 — po-merge kontrola cyklu

Dodano \`scripts/step16_next_cycle_gate.py\` skanujący _tylko rzeczywiste niezmienne_ M0 i xG receipt ze znacznikiem późniejszym niż merge, oraz bazę M0/xG. Wystawia \`PENDING_NEXT_REAL_FORECAST\` lub \`PENDING_NEXT_REAL_CAPTURE\`, aż nowy prawdziwy dzienny raport posiada aktualne \`ned_bel_historical_phase_native_id_review\`, \`real_missing_last5_predecessor_ids\` i \`last5_priority_shadow_comparison\`. Sprawdza limit provider calls oraz brak automatycznego awansu. Nie wywołuje API.

## 2 — dwie metody xG na tych samych danych

Przeniesiono z DRAFT PR #125 tylko **badawczy moduł \`ranked_eight\`** i jego testy, nie część gałęzi zmieniającą aktywny wybór. W \`src/kb3_step17_xg_capture.py\` dotychczasowy \`rank_sources\` pozostaje wyłącznie żywą ścieżką płatnych wywołań. Równocześnie na oryginalnym prawdziwym \`fixture_groups\`, z dokładnie tym samym \`cutoff\`, oblicza się alternatywę. Następny autentyczny receipt zapisze identyfikatory zakresu, pary wspólne, hipotetyczny pułap last5 dla obu wariantów i **faktyczny wynik tylko baseline**. Alternatywne wyniki są nieznane i nie wolno ogłosić ich przewagi bez realnego poboru. Max 33 calls, 0 dodatkowych, bez trenowania CatBoost z xG. PR #125 nadal DRAFT.

## 3 — fazy rozgrywek NED/BEL

Dodano fail-closed \`src/kb3_step16_phase_validation_research.py\`: dokładne ID z nowego niezmiennego M0 forecast weryfikowane SHA256 wobec \`season_shapes\`; duble, sprzeczne / brakujące label \`round/stage/phase\` nie stają się faktem. \`regular\`, \`playoff\`, \`relegation\` są **wyłącznie wskazówkami**, wymagają niezależnej klasyfikacji po ID. Bez nowego raportu pozostaje \`PENDING\`, trening poszerzonych lig **NO-GO**.

## 4 — krok 19, formalnie jeszcze nie rozpoczęty

Stworzono osobne \`src/kb3_step19_odds_research.py\` — kontrakt zapisu zamrożonego przed meczem kursu z dokładnym provider, bookmaker, fixture ID, market, selection, line, ceną dziesiętną, timestamp, SHA źródła. Badawczy SQLite ma triggery blokujące edycję i usuwanie, jednocześnie rygory braku późnego kursu i pełnych stron 1X2/BTTS/TOTAL/AH do no-vig. Nie utożsamia zgłoszonego timestamp z niezależnym serwerowym poświadczeniem. Brak jakiegokolwiek poboru prawdziwych kursów, kosztów, wyliczania EV/ROI, zmian produkcyjnych i awansu. Formalny krok 19 czeka na kroki 17–18.

## Odbiór techniczny i bramki

GitHub Actions Python 3.11: testy negatywne, sprawdzenie oryginalnych baz/receipts, zero provider/API i przegląd śladu \`data/ models/ config/\`. Automatyczne wybranie Championa i oryginalny TEST 2026/27 zabronione; pierwotny M0 SHA \`55310f0e1dd3842e6d876069ef21b1380901b3a6cc6884cf6ec6ea351a5812d1\`. **GATE16 / GATE17 nadal PENDING; 100 FIT + dopiero 50 nowych HOLDOUT bez zmian.**
