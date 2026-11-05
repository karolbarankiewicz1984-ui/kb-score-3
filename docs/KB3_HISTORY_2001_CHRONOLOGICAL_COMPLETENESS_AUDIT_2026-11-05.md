# KB Score 3.0 — audyt 2001 historycznych obserwacji, chronologia i kompletność par cech (05.11.2026)

**Rodzaj:** niezależny read-only audyt *rzeczywistej* bazowej SQLite z oryginalnego artefaktu GitHub Actions. **Nie wykonano treningu ani zmian M0/CatBoost/kalibracji.**

## Źródło i kontrola pochodzenia

- Automatyczne [GitHub Actions #42002590625](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/42002590625), ukończone SUCCESS; historyczne +240 meczów, +204 zweryfikowane xG.
- Oryginalny archiwalny ZIP `KB3_HISTORY_PITCHAPI_SEALED_RESEARCH`, **artifact ID 13402849432**, utworzony przez serwer GitHub `2026-11-05T09:32:33Z`. Pobrano niezależnie oryginalne 21 585 462 bajty ZIP: faktyczny SHA-256 `a5428b35da8bee862bca7f3d129a60251363d534b55d552551784fb445153b41` zgadza się dokładnie z `digest` odpowiedzi GitHub.
- Z archiwum odczytano oryginalną `research/historical_multistat/observations.sqlite` (53 837 824 bajty, SHA-256 `0eae525fac24c359b6441160950cd32f907ebbb64a815dafa957f5ef2ff4e765`), oraz `issue_rechecks.sqlite`; `PRAGMA integrity_check=ok`, `foreign_key_check=[]`.
- SQLite ma 8 640 zindeksowanych zakończonych spotkań, ale tylko **2 001 rekordów observation** i **2 001 odpowiadających im rolling_feature_cache**; indeks to NIE 8 640 kompletnych rekordów treningowych. Zespół i mecz identyfikujemy według `(scope, match_id, kickoff_utc)`.

## Definicja kryterium porównywalności

Do badawczego zbioru trening/validation kwalifikują się tylko osiem krajowych lig ESP, ITA, GER, FRA, NED, BEL, TUR, POL i **sezony 2023/24–2025/26** (bez UCL i 2026/27), zgodnie z `scripts/kb3_p1_historical_eligibility_split.py`. Hipotetyczny cutoff dla cech jest `kickoff−2 h`, a poprzedni rezultat może zostać uwzględniony dopiero przy `previous_kickoff+3 h <= cutoff`. Rekord docelowy nie może wejść do swoich cech, ostatnich 5 meczów nie zastępuje się starszymi z dogodniejszymi danymi; braki nie są zerami.

- **History5:** 5 prawdziwych poprzednich meczów dla *każdej z obu drużyn* oraz komplet wyników/bramek i punktów.
- **Core5:** History5 + pełne wartości dla obu drużyn z ostatnich 5 meczów dla czterech pól: `total_shots`, `fouls`, `corners`, `yellow_cards` (`CORE` z `src/kb3_historical_feature_quality.py`).
- **xG5:** History5 + zweryfikowane `xg_for/xg_against` dla prawdziwych pięciu poprzedników obu drużyn.
- **Core5+xG5:** przecięcie powyższych cech; nie utożsamiać z pełnym 85-feature M1-R/kontraktem P1-asof-v2 i nie certyfikować PIT.
- Porównano listę prawdziwych pięciu poprzedników przy cutoff `kickoff−2h` z odczytem już istniejącego cache (gdzie użyto `previous_kickoff+3h <= kickoff`): **0 rozbieżności wyboru pięciu poprzedników w 1 925 historycznych krajowych obserwacjach**; stąd cache daje tę samą kwalifikację przy surowszym cutoff w tym snapshot.

## Zweryfikowane liczniki z autentycznej bazy

| Zbiór | Liczba |
|---|---:|
| Wszystkie historyczne observations, także bieżący sezon i UCL | **2 001** |
| Osiem dozwolonych lig, trzy wybrane zakończone sezony | **1 925** |
| History5 (5 poprzednich wyników obu zespołów) | **1 915** |
| Core5 (pełne cztery podstawowe statystyki obu zespołów) | **976** |
| xG5 (pełne zweryfikowane xG obu zespołów) | **377** |
| Core5 oraz xG5 na **tych samych spotkaniach** | **280** |
| Core5 bez pełnego xG5 | 696 |
| xG5 bez pełnego Core5 | 97 |
| History5 bez Core5 i bez xG5 | 842 |
| Formalne, oryginalne per-target źródłowe PIT i dopuszczenie v2 FIT/VALIDATION | **0** |

Pełny podział **Core5 / Core5+xG5**, według ligi w badawczej grupie 1 925: BEL 317/114, ESP 174/49, FRA 126/34, GER 163/28, ITA 123/37, NED 21/1, POL 20/2, TUR 32/15. Suma 976/280.

## Symulowany, chronologiczny TRAIN / VALIDATION, 7-dniowe embargo

Rozcięcie tylko *wewnątrz danego subzbioru*, bez przecieku po tym samym kickoff, 70% intencja TRAIN i osobna walidacja. To policzone selektory i kontrola gotowości, **NIE** dowód wykonania treningu ani wynik modelu:

| Spójny subzbiór | Całość | TRAIN | VALIDATION | Odrzucone w 7-dniowym embargo |
|---|---:|---:|---:|---:|
| History5 — wyniki bez obowiązkowych statystyk | 1 915 | 1 337 | 564 | 14 |
| Core5 — 4 kompletne statystyki | 976 | **683** | **256** | 37 |
| xG5 — kompletne xG (niekoniecznie Core5) | 377 | 263 | 94 | 20 |
| Core5+xG5 na tym samym meczu | 280 | **196** | **74** | 10 |

**Kluczowa blokada PIT:** `provider_first_published_at_utc` i `original_provider_first_published_utc` w źródle mają same `NULL`; **0 z 2 001** pierwotnych obserwacji zapisano przed hipotetycznym odcięciem własnego meczu (`kickoff−2h`, ponieważ archiwum pobrano dopiero w 2026 r.). Żaden późniejszy `observed_at` nie dowodzi dawnych zegarów publikacji. Powyższe ilości są `HISTORICAL_RECONSTRUCTED_NOT_ORIGINAL_PIT`, nie `official_v2_training_eligible`, a już zwłaszcza nie ukończonym PIT 85 cech. Brak 85-cechowego oryginalnego zestawu przedmeczowego: formalnie **0**; zakaz przenoszenia badawczych liczb do FIT100.

## Co naprawdę ogranicza wielkość próbek?

Na 1 925 celach historycznych jest **1 362** z kompletem 5 wcześniejszych statystycznych meczów obu drużyn (każdy poprzednik ma obserwację), lecz tylko **976** z kompletnymi Core5 (różnica 386). Najważniejszą przyczyną są braki/rozbieżności `yellow_cards` i odzyskiwanie ich przez oddzielny, niezmienny recheck. Dla NED w Core5 jest 21/216, POL 20/174, TUR 32/190; w Core5+xG5 odpowiednio 1/216, 2/174, 15/190. Obecne historyczne zweryfikowane xG to zgodność źródeł shots/stats, **nie** potwierdzenie czasu pierwotnej publikacji.

## Techniczna decyzja i dalsza kolejność

1. Zachować dotychczasowy M0, Shadow Six, frozen 23 par, kalibrację, GATE16/GATE17, chronologiczny TEST i zasadę 100 FIT +50 nowych HOLDOUT bez zmian.
2. **Osobny badawczy eksperyment** CatBoost na Core5 (683/256) i wspólnym Core5+xG5 (196/74); porównać predykcje na tych samych meczach, nie zestawiać skuteczności modelu bez xG na większym, łatwiejszym zbiorze z xG na innym zbiorze.
3. Zbadać źródłowe braki `yellow_cards` w NED, POL, TUR i kontynuować rzeczywisty historyczny backfill bez dopisywania liczb po fakcie; rozważyć osobną *badawczą* ablację cechy yellow_cards, która pozwoliłaby badać szerszy zestaw z pełnymi trzema podstawowymi statystykami (bez zmiany modelu docelowego).
4. Oddzielnie utrzymywać formalne PIT=0 dla retrospektywnych źródeł; odróżniać retrospektywny trening i rzetelną przyszłą walidację na zamrożonych prognozach GitHub.

**Zamknięcie audytu:** odczyt bez zmian w GitHub data/SQLite, bez wywołania API, bez reforecast i bez uruchomienia treningu. Wyniki odnoszą się do konkretnego artefaktu #13402849432, a nie do późniejszych rewizji bazy.
