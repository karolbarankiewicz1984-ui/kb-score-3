# KB Score 3.0 — GATE 06: PitchAPI, pełny audyt po zmianie klucza

**Data:** 25.10.2026, Europe/Warsaw. **WYNIK: PASS / ZALICZONO** dla audytu źródła, nie dla gotowej bazy treningowej ani silnika ML.

## Historia prób i dowody

- Wcześniejsze błędy HTTP 401 i SDK AuthError: [historia blokady](STEP_06_BLOCKER.md). Użytkownik zaktualizował klucz w GitHub Secrets. Nigdzie nie kopiowano ani nie drukowano jego wartości.
- Po zmianie klucza [uruchomienie #40235222337](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40235222337) zakończyło się **SUCCESS**: 24 kombinacje liga–sezon i xG 48/48; brak La Liga był skutkiem wyszukiwania nazwy z odstępem.
- [Diagnostyka hiszpańskiego katalogu #40235454793](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40235454793) wykazała **`LaLiga` / ESP / `l_0ErfuF`**, sześć sezonów. Poprawiono regułę normalizacji i dodano test przeciw regresji.
- **Ostateczny test #40235545588:** [Actions SUCCESS](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40235545588): zarówno **collect**, jak i **publish** zakończyły się sukcesem. Dane zapisano na gałęzi `main` jako [pełny raport](audits/PITCHAPI_STEP06_2026-10-25.md) i [zagregowany JSON](../data/audits/PITCHAPI_STEP06_2026-10-25.json).
- Równoległa wcześniejsza próba [#40220569321](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40220569321) miała **collect SUCCESS**, ale ogólny status failure wskutek konfliktu publikacji `git push`. Historyczne logi i wcześniejsza kopia 48 próbek pozostają zachowane. Nie używamy tej częściowej próby jako końcowego dowodu 30/30.

## Wyniki ostateczne, odczytane z archiwum JSON

| Miernik | Wynik |
|---|---:|
| Ligi oferowane w katalogu PitchAPI | 77 |
| Nasze główne ligi | 5/5 |
| Dostępne kombinacje liga × sezon 2021/22–2026/27 | 30/30 |
| Rekordy rozegranych spotkań w listach | 9297 |
| Próbki meczów ze strzałami | 60 |
| Kompletne strzałowe xG obu drużyn | 60/60 |
| Próbki częściowe/niewiarygodne | 0 |
| Ścisłe pary ID API-Football (z 30 pierwszych próbek) | 20/30 |
| Kandydaci aliasów, wymagają potwierdzenia | 6/30 |
| Niejednoznaczne / niedopasowane | 4/30 |
| Drugie próbki nieweryfikowane w API-Football | 30/30 |
| Zużyte wywołania PitchAPI | 91/110 |
| Zużyte wywołania API-Football | 30/45 |
| Błędy usług | 0 + 0 |
| Nowe zakupy | 0 zł |

**Przykłady xG zakończonych meczów:** Watford–Southampton (2021/22) PitchAPI `m_3nXDAl`, API-F `710654`, xG 1,05 / 1,75; Getafe–Celta Vigo (2021/22) PitchAPI `m_07LdyJ`, API-F `720833`, xG 0,46 / 1,67. Więcej przykładów i ID w [raporcie](audits/PITCHAPI_STEP06_2026-10-25.md).

## Warunki odbioru i granice wiarygodności

- [x] Autoryzacja PitchAPI po zmianie klucza potwierdzona — prawdziwe odpowiedzi z konta.
- [x] Katalog pięciu lig i 30 sezonów, każda kombinacja z własną listą zakończonych meczów.
- [x] Reprezentatywne próbki: 2 zakończone mecze na każdą kombinację, pełne xG **60/60**.
- [x] Porównanie z API-Football na jednej próbie na sezon, dokładne nazwy+data+wynik: 20 zweryfikowanych par; pozostałe przypadki nie są automatycznie dopasowane.
- [x] Brakujący xG zachowuje status BRAK, nie 0; 60/60 prób to nie dowód pokrycia wszystkich 9297 spotkań.
- [x] Archiwum JSON i MD na main, wyniki testów i limity zapytań w GitHub Actions; bez nowych opłat i bez wycieku klucza.

**Ograniczenia:** xG pobrane z końcowych zdarzeń strzałowych jest statystyką **po meczu**, możliwą do wykorzystania jako cecha **przed późniejszymi spotkaniami** z zachowaniem chronologicznego cutoff. Krok 07 ma uwiarygodnić aliasy i parowanie ID; kroki 09–12 mają przetestować kompletność, pochodzenie i brak przecieków wiedzy z przyszłości. Nie oceniano jeszcze przewagi predykcyjnej xG ani nie trenowano modelu.

**DECYZJA GATE 06: PASS / ZALICZONO — 6/29.** Następny **KROK 07 — wiarygodne dopasowanie ID drużyn i meczów**, nie rozpoczęty w tym odbiorze.

**Źródło prawdy statusów:** [Plan KB Score 3.0 na Dysku Google](https://docs.google.com/document/d/10wjHL3r3OAuxtezwcIeWztxS8lwjhYon5GM3BLhI0xE/edit).
