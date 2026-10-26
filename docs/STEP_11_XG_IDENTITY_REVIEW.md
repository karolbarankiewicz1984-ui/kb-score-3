# KB Score 3.0 — GATE11: korekta mapowania 3 prawdziwych meczów PitchAPI (26.10.2026)

**Status: PARTIAL PASS / GATE11 PENDING (10/29)**. Trening zablokowany. Żadnych zmian w KB2.1, API Market i MultiModel.

## Problem i dowód

W pierwotnym ograniczonym audycie xG 25.10.2026 PitchAPI udostępniło kompletne strzałowe xG dla trzech meczów Premier League, lecz dokładne porównywanie nazw odrzucało je jako **2 × NAME_DISAGREEMENT_OR_AMBIGUITY i 1 × ALIAS_REVIEW_REQUIRED**. Powód to różnice nazw na zewnętrznych źródłach:

| PitchAPI (25.10.2026) | API-Football | ID API-Football | Status |
|---|---|---:|---|
| Sunderland – Leeds United | Sunderland – Leeds | 1557446 | CURATED_SOURCE_IDS |
| Liverpool – Brighton & Hove Albion | Liverpool – Brighton | 1557444 | CURATED_SOURCE_IDS |
| Crystal Palace – Newcastle United | Crystal Palace – Newcastle | 1557441 | CURATED_SOURCE_IDS |

[Źródłowe pobranie #40301238526](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40301238526): jedna aktualna lista 380 meczów API-Football + 3 strzałowe feedy xG PitchAPI w max 5 wywołaniach PitchAPI. Pełne rekordy identyfikacyjne dostawców zapisano **wyłącznie w szyfrowanej kopii**. [Prywatna kopia Google Drive](https://drive.google.com/file/d/1eoBQ-71T4J0wsmqEZ9NPLHcWR7rlnXqW/view?usp=drivesdk). Z poprzedniej wersji posiadaliśmy same strzały, bez identyfikatorów z listy PitchAPI — ten brak został usunięty.

## Dokładna, ograniczona metoda zatwierdzania

- `src/kb3_identity_review.py` wymaga jednego dopasowania w pełnym zestawie: kickoff UTC (normalizacja stref), **FT**, bramki 90', tożsamość obu drużyn. Sama zbieżność daty, wyniku albo podobieństwo nazw **nie** dopuszcza automatycznego mapowania.
- `config/step11_reviewed_pitch_fixture_crosswalk_20261026.json` zawiera dokładnie trzy **meczowe, nie ligowe** powiązania, z identyfikatorami PitchAPI i API-Football obu uczestników oraz identyfikatorem i hashem oryginalnej obserwacji. Nie stosuje ogólnych aliasów na wszystkie mecze, a późniejsze mecze tych samych klubów wymagają nowych dowodów.
- `src/kb3_xg_pit.py` od nowego pobrania archiwizuje oryginalne metadane meczu PitchAPI oraz oryginalne kandydatury API-Football wraz z surowymi strzałami w zaszyfrowanym `raw_json`. Podczas audytu przelicza ponownie zarówno xG, jak i przyczyny odrzucenia powiązania.
- `src/kb3_reviewed_xg.py` jest **osobną warstwą pochodną**. Sprawdza źródłowy hash całego szyfrogramu i hash-chain odpowiedzi 380 meczów, identyfikatory obu drużyn, oryginalną odpowiedź, dokładną datę UTC, FT, wynik, potwierdzenie wyniku zaobserwowane **przed pobraniem xG**, kompletność strzałów i pierwotny timestamp odczytu xG. Pozycje oryginalnego źródła **pozostają niezmienione i w statusie kwarantanny**; dopuszczamy jedynie wyliczony lookup o ograniczonym zakresie.

## Wynik na prawdziwym archiwum

Na lokalnie odszyfrowanej kopii z Google Drive uruchomiono dokładnie kod pochodzący z gałęzi GitHub, z niezależnie pobranego artefaktu źródłowego [#40302357607](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40302357607). Klucz prywatny **nie był przesyłany do GitHub**.

- `PRAGMA integrity_check=ok`, brak naruszeń kluczy obcych, poprawne hashy szyfrogramu i hash-chain.
- **3/3** konkretne pary otrzymały zewnętrzny, audytowalny status `CURATED_MATCH_BOUND_SOURCE_EVIDENCE`, z autentycznymi xG strzałowymi.
- **3/3** przeszły test udostępnienia jako historia przed **późniejszym** terminem prognozy. Własnego meczu **nie da się prognozować jego xG po końcu**, a cutoff sprzed pobrania xG **nie może** użyć tych danych.
- **0** wierszy oryginalnego dziennika zmieniono; **0** ogólnych aliasów automatycznie zatwierdzono. `provider_published_at` nadal **NULL**, bez certyfikacji historycznej daty publikacji.
- Dowód zbiorczy: [STEP11_XG_MATCHBOUND_REVIEW_2026-10-26.json](../data/audits/STEP11_XG_MATCHBOUND_REVIEW_2026-10-26.json).

## Testy i dalsze ograniczenia

[GitHub Actions #40302235918](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40302235918) **111/111 PASS** — 72 testy kroku 11, 39 testów regresyjnych. Testy obejmują naruszenie hashy, błędną tożsamość dwóch drużyn, duplikaty fixture, wyniki i terminy, aliasy bez weryfikacji, błędny cutoff, próby użycia własnego pomeczowego xG do prognozy, przedwczesną aprobatę.

**To nadal nie jest gotowy zestaw cech całej ligi.** Potwierdzono tylko trzy starannie wybrane mecze. Aby zamknąć GATE11: trzeba rozszerzyć pokrycie oraz powtarzalną kontrolę dopasowania xG, zintegrować bezpieczny `asof` z głównym builderem `kb3_features.py`, udowodnić stabilność źródeł w kolejnych dniach i wykonać końcowy test no-lookahead. Historyczne sezony 2023–2025 pozostają w trybie `RETROSPECTIVE`. Nic nie włączyło treningu.
