# KB Score 3.0 — protokół realizacji punktów 1–3 z 1 XI 2026

Punkt 1 — poprawiony harmonogram M0 na \`06:21,09:21,12:21 UTC\` zamrożenia (zapasowe próby) i \`08:17,14:17,22:17 UTC\` rozliczenia. Moduł \`scripts/step16_m0_mode_guard.py\` zapobiega duplikatom: wybiera tryb \`skip\` jeżeli istnieje zapis dzienny lub świeże rozliczenie. PR #127 MERGED: https://github.com/karolbarankiewicz1984-ui/kb-score-3/pull/127. CI #41306434527 i #41306434501 PASS; produkcyjno-badawcza kontrola #41306504012 PASS z komunikatem \`skip NO_NEEDED_PAID_PROVIDER_REQUEST\`. GitHub schedule nie ma gwarancji punktualności.

Punkt 2 — rzeczywisty run https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/41305979888 PASS: 75/75 M0 poświadczonych przed spotkaniem, 4/4 challengery poświadczone SHA i timestampem GitHub hosta; po meczu 39 kwalifikowanych rozliczeń M0, 61 do pierwszej 100. Wspólnie rozliczonych trójek jeszcze 0. Dowód: \`data/pit_sidecar/m0_720_eight/2026-11-01/settle-122115107601/RECEIPT.json\`.

Punkt 3 — PR #122, #123, #127 scalone po testach. PR #124 NO-GO Codex R1–R6, #125 research xG i #126 research TRAIN-only pozostają draft. Żaden model, parametry M0, historyczny TEST ani reguły kalibracji 100+50 niezmienione. Formalny krok 16/17 nadal PENDING.

Niniejszy protokół nie udaje pełnego rozliczenia jeszcze niezakończonych meczów; wynik porównania trzech silników powstanie dopiero po zakończeniu tych meczów.
