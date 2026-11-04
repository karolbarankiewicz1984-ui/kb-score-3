# KB Score 3.0 — CatBoost Shadow 6: kontrolowane wpięcie do M0, domyślnie OFF

**Dyspozycja:** „Działaj dalej”. Etap po PR #154: przygotować rzeczywiste równoległe zamrażanie przyszłych predykcji na tej samej migawce co M0; nie aktywować go samowolnie.

## Wykonane zmiany techniczne

1. **Jednoznaczne wskazanie pliku modelu:** `config/kb3_shadow_six_pinned_research_model.json` odwołuje się do JEDNEGO rzeczywistego artefaktu 13366883765, Actions run 41922809252. CBM SHA256 `58c5a7fc35afe942893a25b96233689d1f7814ec8a93ed689a7b46f553dbbbc5`, manifest SHA256 `9a1b2ce07d11aa369066de712469470f862836a5ba5d3e817402589e65fc8eca`. Nie mieszać plików z różnych sesji trenowania. Artefakt wygasa 18.11.2026; plan trwałego przechowywania jest jeszcze wymagany.
2. **Fail-closed preflight PRZED wywołaniem PitchAPI:** `src/kb3_p1_shadow_live_gate.py` akceptuje wyłącznie jawny przełącznik `KB3_SHADOW_SIX_ENABLED=true/1` i sprawdza autentyczne bajty CBM, SHA, manifest, dokładny kontrakt sześciu cech i flagę `production_approved=false`. Brak SHA/binarnego modelu/manifestu = odmowa bez sportowego API. Domyślnie OFF.
3. **Równoległe wejście bez zmiany M0:** `src/kb3_step16_m0_720_eight_forward.py` ma opcjonalne `shadow_engine`/`shadow_sink`. Nowy CBM odczytuje identyczną rzeczywistą migawkę `_compose_features` i rodzica M0 z tego samego pobrania danych, tej samej ligi/meczu oraz cutoff. Żadnych dodatkowych wywołań do dostawcy, parametrów M0, zmian oryginalnych prawdopodobieństw, etykiet celu ani zmian w już zamrożonych rekordach.
4. **Atomowe staging SQLite:** `freeze_only_new_m0()` dopisuje shadow tylko jeśli rodzic M0 został nowo zapisany w TYM SAMYM przebiegu. Wymaga 1 shadow na nowego M0, SHA rekordu i identyfikatora źródła, FK i append-only triggerów. Stare prognozy są pomijane bez backfill. Naruszenie zamyka całą próbę przed publikacją bazowej SQLite. `official_fit_increment=0`.
5. **Późniejszy niezależny dowód GitHub hosta:** `src/kb3_p1_shadow_host_provenance.py` czyta dokładny oryginalny ZIP z Actions, weryfikuje SHA rodzica M0 i CBM, oryginalny timestamp GitHub `created_at` przed kickoff−90 minut, oraz zapisuje tylko poświadczone, nieedytowalne dowody. Same lokalne daty i logi nie są podstawą. Zestawienie metryk dopiero po dołączeniu rzeczywistego wyniku i host proof obu prognoz na tym samym meczu. M0 pozostaje championem.
6. **Workflow M0 z domyślną blokadą:** `actions/download-artifact@v4` pobiera wybrany artefakt tylko w trybie `forecast`, po ustawieniu w repo jawnej zmiennej `KB3_SHADOW_SIX_ENABLED=true`. Standardowy `settle` nie pobiera modelu. Na tym etapie repo variable NIE została ustawiona; żaden PR nie scalony. Przy braku lub wygasłym artefakcie nie wolno ignorować błędu ani robić niecertyfikowanego przeliczenia z historii.

## Procedura odbioru

- Test PR-only ma rzeczywiście pobrać dokładny wybrany CBM z GitHub Actions (bez ponownego trenowania) i uruchomić istniejący generator M0 wraz z dwoma challengers Step17 i nowym Shadow na 64 SYNTETYCZNYCH przyszłych meczach, a następnie sprawdzić 64 niezmienione prognozy M0, 128 dotychczasowych challengers, 64 nowe wpisy shadow i immutable constraints.
- Osobny test weryfikuje czy archiwum ZIP rzeczywiście zawiera dokładnie te bajty SQLite i rekordy CBM, a bez niezależnego proof nie liczy ich jako sparowane wynikowo prognozy. Dołączyć istniejące testy regresji M0/Step17 i kontrolę braku edycji data/models.
- Formalne etapy: P1-01 PARTIAL, GATE16/GATE17 PENDING, próg M0 100 FIT + 50 nowych HOLDOUT bez zmian. Sześcioczynnikowy CBM trenowano na RECONSTRUCTED research, nie na certyfikowanym historycznym PIT. Nie ma automatycznego wyboru Championa.

## Co musi się wydarzyć przed realnym uruchomieniem?

Przegląd i kontrolowane scalenie zależnych PR #151, #152, #153, #154 i tego PR; trwałe przechowanie dokładnie wybranych bajtów CBM/manifestu (obecny artefakt wygasa 18.11.2026), osobny audyt bezpieczeństwa oraz jawny opt-in do zmiennej repo. Dopiero wtedy przyszły harmonogram M0 może wygenerować prawdziwe nowo zamrożone prognozy Shadow. Bez host-created proof przed kickoff-90 minut nadal 0 zaakceptowanych par prospektywnych. Brak nowych provider API w ramach tej budowy.

## Status

Implementacja robocza do weryfikacji CI. Wyniki testów, identyfikator runu i rzeczywiste blokady należy uzupełnić wyłącznie po potwierdzonym wykonaniu.

## 04.11.2026 — rozwiązanie problemu wygasającego modelu (wykonane)

- **Trwała kopia konkretnego modelu:** nowy [GitHub Actions #41929594196](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/41929594196) `SUCCESS`. Repozytorium otrzymało wyłącznie na gałęzi badawczej PR #155, w `assets/research/kb3_shadow_six_v1/`, **dokładne bajty 65 032 B** istniejącego modelu `.cbm` i jego historyczny manifest `JSON` ze starego artefaktu `13366883765`. Workflow weryfikował wymagane SHA: **CBM** `58c5a7fc35afe942893a25b96233689d1f7814ec8a93ed689a7b46f553dbbbc5`, **manifest** `9a1b2ce07d11aa369066de712469470f862836a5ba5d3e817402589e65fc8eca`; nie trenował ponownie ani nie dotykał M0. Kopia znajduje się w prywatnym repo jako wersjonowane pliki i **nie zniknie wskutek wygaśnięcia starego artefaktu Actions**. Nie utożsamiać kopii z dopuszczeniem historycznego PIT.
- **Integracja workflow zmieniona:** warunkowy, wyłączony domyślnie krok przed wywołaniem PitchAPI odczytuje teraz dokładnie te trwałe pliki z checkout repo i kopiuje do katalogu roboczego, z weryfikacją SHA/manifestu. Nie pobiera już modelu z wygasającego artefaktu. `load_opted_shadow()` dodatkowo wymaga wpisu w pin JSON potwierdzającego konkretny folder w repo i rzeczywisty GitHub mirror run ID. Przy brakach lub zamianie bajtów zakończy błąd przed żądaniem sportowego API.
- **PR-only CI** również odczytuje teraz trwałą kopię, nie stare archiwum; dzięki temu będzie można ponawiać testy **po 18.11.2026**. Kontrole SHA, home/away, zgodności z istniejącym 6-cechowym `make_forecasts()`, niemodyfikowalności SQLite i braku retro-backfill pozostają takie same. Osobny mirror workflow ma ściśle ograniczoną docelową gałąź, żadnych force-push i ponownego fitowania; po pierwszym udanym zapisie nie zostaje ponownie uruchomiony przy każdym update plików modelu.
- **Nie włączono LIVE:** PR #151–#155 pozostają robocze; `main` nie został zmodyfikowany w obszarze działania M0. Nie zmieniono repo variable `KB3_SHADOW_SIX_ENABLED`, kalibratorów, danych i polityki 100 FIT + 50 przyszłych HOLDOUT. Pierwszy realny forward/host-proof dla Shadow 6 nadal 0, aż nastąpi osobny odbiór i kontrolowane uruchomienie.

### Odbiór integracji z trwałej kopii

Po zmianie źródła artefaktu ponownie wykonać pełne, rzeczywiste GitHub CI PR #155 i rejestr wyników, nie opierać się wyłącznie na testach sprzed zmiany.
