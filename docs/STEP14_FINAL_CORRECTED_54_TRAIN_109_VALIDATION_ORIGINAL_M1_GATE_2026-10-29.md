# KB Score 3.0 — Krok 14 / REAL 760 TRAIN + 380 VALIDATION, korekta FPL FT „3.0”, 1140×159, GATE14

**Raport ostateczny v2 — 29.10.2026.** [Rzeczywisty test GitHub Actions #40877358785](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40877358785) **SUCCESS**. Zmiana [PR #95](https://github.com/karolbarankiewicz1984-ui/kb-score-3/pull/95). To uzupełnia [pierwotny audyt kroków 1–4](STEP14_REAL_TRAIN_760_DENSE_VALIDATION_109_AND_FINAL_M1_GATE_2026-10-29.md), który zaniżył liczbę TRAIN do 10 ze względu na nieprawidłowy parser archiwalnych FPL wyników zapisanych jako tekstowe `3.0`.

## Korekta potwierdzona na oryginalnych starych plikach

12 archiwalnych niezależnie datowanych i przypiętych SHA źródeł sezonów 2023/24 i 2024/25 używa często `"0.0"`, `"1.0"`, `"3.0"` dla prawdziwej **całkowitoliczbowej liczby goli**. Wersja v1 przyjmowała wyłącznie `int("3")` i omijała tysiące poprawnych wyników, fałszywie sygnalizując brak źródła. Wersja v2 akceptuje tylko źródłowe liczby skończone `0–30`, które matematycznie są całkowite: `3.0 → 3`. Nadal odrzuca `2.5`, `NaN`, brakujące i błędne wartości. Odczytano prawidłowo **4100 komórek goli w starym formacie .0**; nie zaokrąglano wartości ułamkowych ani nie przypisywano żadnych wyników z 2026 do historycznej publikacji.

## Wynik rzeczywisty etapów 1–4

| Element | Potwierdzony wynik |
|---|---:|
| Oryginalny TRAIN 2023/24–2024/25 z pełnym źródłowo potwierdzonym FORM5 obu drużyn | **54 / 760** |
| Oryginalny VALIDATION 2025/26 z historycznie potwierdzonym FORM5 | **109 / 380** |
| Oryginalny VALIDATION z kompletnymi pięcioma alternatywnymi xG/xGA dla obu drużyn | **107 / 380** |
| Archiwalne źródła TRAIN ze zweryfikowanym niezależnym zegarem | **12** |
| Archiwalne źródła VALIDATION ze zweryfikowanym niezależnym zegarem GitHub Actions | **25** |
| Matematyczny, retrospektywny Elo 2023/24–2025/26 | **1140 / 1140** |
| Oryginalne natywne PitchAPI rekordy 121+38 ze wszystkimi `as-of` receipts | **0 / 760 TRAIN oraz 0 / 380 VALIDATION** |

Wynik jest wyznaczony na oryginalnych `match.id` PitchAPI i zamrożonym podziale TRAIN/VALIDATION, dokładnych parach drużyn i UTC. Historyczne źródło FT nie może być nowsze niż docelowy kickoff i nie może pokazywać docelowego meczu jako już zakończonego. Gdy nie ma pełnego wcześniejszego wyniku, rekord pozostaje niekompletny. Źródłowe FPL fixture CSV **nie jest natywnym team-xG** i nie wolno z niego wnioskować zerowego xG.

Została nowa, odrębna **macierz 1140×159**, obejmująca wszystkie oryginalne nazwy cech (121 liczb, 38 flag), dokładne ID/split, realny dawny SHA oraz czas dostępności i `null` dla wartości nierozstrzygniętych. **19 wartości Elo ze współczesnej retrospektywnej rekonstrukcji** trzymamy w odrębnych polach; nie przedstawiamy ich jako źródłowo poświadczonych wartości modelu dostępnych wtedy.

## Artefakty i decyzja M1

- [Zaktualizowany audyt TRAIN 760 / VALIDATION 380](../data/audits/STEP14_760_TRAIN_FPL_WHOLE_DECIMAL_CORRECTED_SUMMARY_2026-10-29.json)
- [Poprawiona macierz 1140×159 w gzip](../data/audits/STEP14_760_TRAIN_FPL_WHOLE_DECIMAL_CORRECTED_1140x159_2026-10-29.jsonl.gz)
- [Końcowy audyt GATE14 po korekcie](../data/audits/STEP14_760_TRAIN_FPL_WHOLE_DECIMAL_CORRECTED_M1_FINAL_GATE_2026-10-29.json)
- [Skrypt odczytu i ponownej kontroli](../scripts/step14_train_760_decimal_FPL_FT_corrected_v2.py)

**Werdykt kroku 4: GATE14 = PENDING, 13/29**. Dostępne są realne publiczne dane historyczne do badania, ale nie wystarczają do treningu oryginalnego CatBoost M1 zgodnie z niezmienionym kontraktem: brak dowodów `first_published_at` oryginalnego natywnego xG PitchAPI dla całych 760 TRAIN i brak kompletnych oryginalnych 121+38 PIT. **Nie przeprowadzono oryginalnego treningu ani nie wymyślono metryk.** Oryginalny split, TEST 2026/27, prognozy i pozostałe modele nietknięte. Nie dodawano szyfrowania ani płatnych usług.

**Uwaga historyczna:** poprzedni raport v1 zawierający `TRAIN=10` pozostaje zachowany jako ślad audytu, ale **do decyzji i kolejnych prac obowiązuje skorygowany v2 `TRAIN=54`**.
