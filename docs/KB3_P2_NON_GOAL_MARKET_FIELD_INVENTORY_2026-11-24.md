# KB3 P2 — potwierdzony odczyt istniejących pól statystycznych, 24.11.2026

**Zakres tej czynności:** przegląd już istniejącego kodu i dokumentów źródłowych, **0 nowych wywołań API**. Nie zbudowano nowych prognoz, nie stwierdzono zgodności z linią u bukmachera i nie promowano żadnego modelu.

## Co jest faktycznie zaimplementowane

W [src/kb3_historical_feature_quality.py](../src/kb3_historical_feature_quality.py) istnieją zadeklarowane nazwy czterech statystyk Core: **total_shots, fouls, corners, yellow_cards**. Pełna lista METRICS zawiera również **ShotsOnTarget, ShotsOffTarget, red_cards, shots_inside_box, shots_outside_box**. [scripts/kb3_history_gain_first.py](../scripts/kb3_history_gain_first.py) wykorzystuje cztery metryki Core dla badawczych ośmiu krajowych lig.

| Rozważany rynek | Wewnętrzne źródłowe nazwy w kodzie | Co należy wyjaśnić przed budową rynku |
| --- | --- | --- |
| Faule | fouls | Czy to total, per-team, pełne 90 min i identyczna definicja z rozliczeniem u bukmachera |
| Kartki | yellow_cards, red_cards | Liczba kartek vs punkty kartkowe, druga żółta, kartki ławki, konflikty eventów |
| Rożne | corners | Faktycznie wykonane vs przyznane, okres, strona gospodarze/goście |
| Strzały / celne | total_shots, ShotsOnTarget, ShotsOffTarget | Blokowane, słupki/poprzeczki, strzały celne, suma kategorii i okres 90 min |

To **nazwy wewnętrzne istniejącego historycznego parsera**, a nie świeży bezpośredni proof dokumentacji PitchAPI. Braków nie wolno zamieniać na zero. Nie wolno zakładać, że total_shots zawsze równa się sumie dwóch wybranych podkategorii.

## Nie mylić jakości historycznych last5 z modelem rynkowym

- [Udokumentowana chronologia Core5](KB3_HISTORY_2001_CHRONOLOGICAL_COMPLETENESS_AUDIT_2026-11-05.md): Core5 wymaga pięciu prawdziwych poprzednich meczów **obu** drużyn oraz czterech pól Core. Kompletny Core5 nie jest certyfikacją daty publikacji historycznych wartości przed kickoff.
- [ZMIANY.md](ZMIANY.md) dokumentuje rzeczywistą partię 05.11: historyczny ośmioligowy Core5 976→1225/2156, joint Core5+xG5 280→372. **To wartości historyczne z 05.11, nie nowy dzisiejszy pomiar.**
- [Gotowy niezależny ledger rynków bramkowych](../src/kb3_test_market_ledger_v1.py) już wykorzystuje konkretny market+line+selection+P, SHA, host attestation, immutable settlement. **Nie implementować ponownie** 1X2/O-U goli/BTTS/double chance/team goals.
- [Istniejący techniczny audyt PitchAPI stats/events](../scripts/step11_pitch_native_uefa_stats.py) może pomóc sprawdzić definicje okresów i kluczy, ale nie jest działającym modelem fauli czy kartek.

## Wynik i dalsze czynności

- **P2-01 — WYKONANE CZĘŚCIOWO:** zinwentaryzowano istniejące kodowe nazwy wszystkich czterech obszarów i zidentyfikowano source modules. **ZABLOKOWANE do dalszego odbioru**: aktualna autentyczna zgodność provider period/stats/team/market i kompletność w nowych naprawdę zamrożonych obserwacjach.
- **P2-02 — DO ZROBIENIA:** z istniejących oryginalnych, prawdziwych snapshots sprawdzić definicję wyniku na 90 min, statystyki obu stron i istniejące konflikty kartkowe; brakujące wejścia pozostawić NULL+reason. Żadnych nowych płatnych API bez zgody.
- **P2-03 — DO ZROBIENIA:** osobne badawcze silniki i modele faule/kartki/rożne/strzały, wersjonowane i zamrażane tylko przed autentycznym cutoff; nie używać niedowodowego PIT do produkcyjnego treningu.
- **P2-04 — DO ZROBIENIA:** własne, nienadpisywalne settlement oraz kalibracja i CI dla tych rynków. Żadnych wymyślonych kursów, promocji Championa ani fałszywych próbek z zależnych wyborów tego samego meczu.

**Granice odbioru:** żadna rodzina pozabramkowa nie uzyskała statusu model PASS w tym audycie. Formalne GATE16/17 i oryginalny strict PIT pozostają PENDING.

Prowadzący zadanie: [Issue #190](https://github.com/karolbarankiewicz1984-ui/kb-score-3/issues/190), już istniejące prace nad last5: [#181](https://github.com/karolbarankiewicz1984-ui/kb-score-3/issues/181), pozostałe P0/P1: [#188](https://github.com/karolbarankiewicz1984-ui/kb-score-3/issues/188).
