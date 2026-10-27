# KB Score 3.0 — Krok 14: audyt zawartości 25 archiwalnych blobów i powiązanie kandydatów z PitchAPI

**Data wykonania:** 27.10.2026 (GitHub Actions [#40492184278](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40492184278))  
**Rezultat:** **PASS dla sprawdzenia zawartości historycznych wersji**, **PENDING dla rzeczywistego niezależnego czasu publikacji oraz natywnej identyfikacji obu drużyn PitchAPI**. **0** rekordów uprawnionych do oficjalnego TRAIN. **GATE14 PENDING, 13/29**.

## Metoda

1. Wzięto tylko podpisaną i zamrożoną [listę 40 TRAIN + 20 VALIDATION](../data/research/STEP14_PIT_PILOT_40_TRAIN_20_VALIDATION_2026-10-27.json), której 60 rekordów zawiera identyfikator `m_XXXXXX` PitchAPI i dokładny kickoff UTC, **bez** końcowych wyników, kursów ani danych TEST.
2. Dla każdego rekordu pobrano z historii GitHub najbliższy commit dotyczący danego sezonu, którego **deklarowany czas committera** był wcześniejszy niż kickoff-48h. Przeczytano z konkretnego SHA rzeczywisty historyczny `en.1.json` (`raw.githubusercontent.com/openfootball/football.json/SHA/SEASON/en.1.json`), a nie aktualny `master`. Pobrano i sprawdzono **25 odrębnych blobów**. W raporcie utrwalono pełne SHA commitów i SHA256 każdego pobranego pliku.
3. Dokładną godzinę `date+time` z oryginalnego angielskiego terminarza przekonwertowano z **Europe/London** (DST BST/GMT) na UTC. Dla każdej `PitchAPI.fixture_id` policzono kandydatów OpenFootball mających identyczny kickoff. Sprawdzono także, czy w **dopasowanym** historycznym wpisie był już wynik FT — żaden z 17 pojedynczych kandydatów go nie zawierał. Wynik nie jest przenoszony do cech M1.
4. Niezależnie wykonano żądania do indeksu [Internet Archive CDX](https://github.com/internetarchive/wayback/tree/master/wayback-cdx-server) dla surowych plików obu sezonów. Nie uzyskano użytecznego potwierdzenia czasu archiwizacji i **nie pobrano niezależnej migawki o porównanym hash SHA256**. Kategoryczny wniosek „nie istnieją żadne archiwa” byłby nieuzasadniony; weryfikacja pozostaje *niezakończona*. Podobnie brak historycznych zarejestrowanych GitHub Actions lub commit statuses dla przykładowych SHA nie dowodzi daty publikacji; komity są `unsigned`.

## Rzeczywiste wyniki 60 rekordów

| Typ rezultatu | TRAIN 2023/24 | TRAIN 2024/25 | VALIDATION 2025/26 | Razem |
| --- | ---: | ---: | ---: | ---: |
| Jeden publiczny mecz o dokładnym kickoff | 0 | 9 | 8 | **17** |
| Wiele publicznych meczów o dokładnym kickoff | 0 | 10 | 7 | **17** |
| Historyczny blob bez meczu o dokładnym kickoff | 0 | 0 | 5 | **5** |
| Brak kandydującego commita przed cutoff | 20 | 1 | 0 | **21** |
| **Razem** | **20** | **20** | **20** | **60** |
| **Potwierdzone natywne IDs obu drużyn i publikacja przed kickoff** | **0** | **0** | **0** | **0** |

**17 to jednoznaczne parowanie terminarza wyłącznie po dacie i godzinie — nie pełny zweryfikowany crosswalk.** Nie dowodzi, że publiczny mecz to faktycznie ten sam natywny rekord PitchAPI, jeżeli brak źródłowych ID i nazw obu drużyn. Wśród 17 pozycji z niejednoznaczną godziną nie wolno wybierać meczu na podstawie wyniku lub prawdopodobieństw modelu. Pięć niedopasowań może wynikać m.in. z przesunięć terminarza, a nie ze złego oryginalnego PitchAPI ID.

## Przykładowe PROWIZORYCZNE mapowanie (tylko unikalny kickoff; nieweryfikowane IDs drużyn)

| PitchAPI fixture_id | Kickoff UTC | Gospodarz wg starego bloba OpenFootball | Gość wg starego bloba OpenFootball | Commit SHA (pierwsze 12 cyfr) |
| --- | --- | --- | --- | --- |
| `m_3SLMkR` | 2024-09-21 16:30 | Crystal Palace FC | Manchester United FC | `1391504f1de7` |
| `m_3AMymS` | 2024-10-05 16:30 | Everton FC | Newcastle United FC | `5f777dc6e2cd` |
| `m_2pnf3Z` | 2024-10-26 16:30 | Everton FC | Fulham FC | `d01ea3e43ea2` |
| `m_2IJhgL` | 2024-11-09 17:30 | Brighton & Hove Albion FC | Manchester City FC | `d0a780d5a22b` |
| `m_1IZ7nv` | 2025-01-20 20:00 | Chelsea FC | Wolverhampton Wanderers FC | `97a50f4d2ba` |
| `m_2g5x00` | 2025-02-02 16:30 | Arsenal FC | Manchester City FC | `831bb41621b9` |

Wszystkie 60 pełnych wierszy, w tym 17 kandydatów z nazwami, są utrwalone w [raporcie JSON](../data/audits/STEP14_HISTORICAL_BLOB_60_2026-10-27.json), oddzielnie od [raportu próby niezależnego czasu](../data/audits/STEP14_WAYBACK_PUBCLOCK_2026-10-27.json). Historyczne pliki zweryfikowano w repozytorium źródłowym [OpenFootball](https://github.com/openfootball/football.json).

## Dlaczego natywnego ID PitchAPI nie można jeszcze jednoznacznie certyfikować

Pierwotny [target-free Step12 SAFE MODEL VIEW](../data/splits/STEP12_SAFE_MODEL_VIEW_2026-10-26.json) zawiera `fixture_id`, `kickoff_utc`, `partition`, ale **nie zawiera natywnego `home_team_id`, `away_team_id`, nazw obu drużyn ani podpisanej mapy nazw OpenFootball**. Są one w prywatnych, **zaszyfrowanych** oryginalnych receiptach PitchAPI. Istniejący [przejrzany crosswalk 3 spotkań](../config/step11_reviewed_pitch_fixture_crosswalk_20261026.json) dotyczy wyłącznie 25.10.2026 — nie można rozszerzyć go automatycznie na 2023–2026.

Do pełnego łączenia wymagane jest lokalne przywrócenie podpisanego, szyfrowanego archiwum oryginalnego PitchAPI przez właściciela klucza prywatnego **bez eksportowania klucza ani surowych wyników**, następnie porównanie dla każdego ID: obie natywne pary `team_id`, nazwy zespołów, UTC, sezon, hash źródła, wersję publicznego historycznego bloba, brak sprzeczności i zgodę na alias nazwy. Wówczas dopiero możliwa jest osobna zgoda na `PITCHAPI_IDENTITY_MATCH`.

**To nadal nie daje automatycznie `PIT PASS`**: dla dokładnego historycznego dokumentu musiałby istnieć również niezależny zapis czasu publicznego udostępnienia przed cutoff, z porównanym kryptograficznie payloadem (np. WARC/Wayback z danym SHA treści), i dla każdej używanej cechy również źródłowy as-of receipt. Sam Git `commit.committer.date` jest edytowalny, a plik sezonowy może mieć późniejsze rewizje.

## Testy i niezmienne bramki

[GitHub Actions #40492184278](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40492184278) **8/8 testów PASS**, realne pobranie 25 plików i trwały zapis dwóch raportów. Testy obejmują BST/GMT, wiele meczów o jednej godzinie, obecność wyniku przed kickoff, skażony TEST, nieprawidłową chronologię i odmowę awansu na `PIT_CERTIFIED` z samego commita.

Nie modyfikowano oryginalnych danych, Elo + Poisson M0, 20 zamrożonych prognoz, blokad TRAIN ani TEST; **`training_allowed=false`, `gate14_pass=false`, 13/29**.
