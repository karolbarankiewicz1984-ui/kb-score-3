# KB Score 3.0 — niezależna kontrola oryginalnej historycznej bramki PIT, 2026-11-01

**Zakres:** wyłącznie oryginalna rygorystyczna rekonstrukcja 2023/24–2025/26 (121 cech + 38 flag, 760 TRAIN i 380 VALIDATION), bez TEST 2026/27, bez oryginalnego M1 fit i bez nowych kluczy/API. **Wynik: `GATE14_ORIGINAL_STRICT_NATIVE_PIT=PENDING`; certyfikowanych wierszy 0/760 TRAIN i 0/380 VALIDATION.** Nie jest to odwrócenie formalnej akceptacji *odrębnego* wariantu B z 29.10.2026.

## Nowa kontrola rzeczywistych źródeł zewnętrznych przez API GitHub (01.11)

Dla publicznego `vaastav/Fantasy-Premier-League` niezależnie ponownie pobrano metadane GitHub, zamiast wyłącznie przepisywać lokalny raport:

1. **2023/24:** `compare/4e6447daccfb053a496e4aebd37d264dfa949676...436f1ff2d306783d3e3892dc3d3ce21712cbc08e` zwrócił `status=ahead`, `ahead_by=2`, `behind_by=0`, `merge_base=4e6447daccfb053a496e4aebd37d264dfa949676`; w różnicy występują rzeczywiste `data/2023-24/fixtures.csv` i `data/2023-24/gws/merged_gw.csv`. Odrębny `fetch_commit` potwierdził SHA potomka i wiadomość `Add GW32 data`. `fetch_file` starego `data/2023-24/fixtures.csv` pod SHA `436f1ff2...` zwrócił historyczny blob `342f02b154054bc196d0279e88b5dfccc2cfe0c7` i oryginalne kolumny `id,kickoff_time,team_a,team_h,finished`.
2. **2024/25:** `compare/f42ed38d279afc705448ebc2b89e48838a0fdfba...29e6c2f4590b1a03f218552ca676b9495539cfdc` zwrócił `status=ahead`, `ahead_by=31`, `behind_by=0`, `merge_base=f42ed38d279afc705448ebc2b89e48838a0fdfba`; w różnicy istnieje `data/2024-25/fixtures.csv`. `fetch_commit` potwierdził wiadomość `Add GW5 data`; `fetch_file` starego `data/2024-25/fixtures.csv` pod SHA `f42ed38...` zwrócił historyczny blob `40af503c82fdc343e740092641f009a4cf435848` z rzeczywistymi `finished`, `kickoff_time` i parą ID drużyn.

**Granica nowego dowodu:** porównanie Git DAG i istnienie starych blobów potwierdza *tożsamość źródłowych rewizji i ich przodków*, **nie** dowodzi samodzielnie daty pierwszego publicznego PushEvent, oryginalnej tożsamości każdego natywnego PitchAPI fixture/team ani opublikowania 159 pól przed kickoff. Niezależne zegary GHArchive pozostają wyłącznie według wcześniejszych osobno zapisanych raportów (np. `STEP14_ALL_74_FPL_REVISIONS_ANCHORED_GHARCHIVE_2026-10-29.json`); nie udajemy nowego odczytu tych eventów.

## Rzeczywiste GitHub Actions — ponownie odczytane joby i logi

- [#40738870670](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40738870670), job `122994718765`: 6/6 testów PASS, `rows=1140`, `numeric=73`, `flags=14`, `field_slots=99180`, `original_PIT_qualified_rows=0`; artifact `12837194077`.
- [#40745602928](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40745602928), job `123018430263`: 9/9 testów PASS, `native_fixture_joins=1140`, `all_previous_source_ft=106`, `provider_original_full_pit=false`, `gate14_pass=false`; artifact `12840967212`.
- [#40746307963](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40746307963), job `123020914619`: 2/2 testy PASS; alternatywne player-xG z FPL nie jest automatycznie PitchAPI team-xG.
- [#40916193143](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40916193143), job `123596940030`: niezależny audyt *zrewidowanego* `GATE14-B` PASS (720/374, model M1-R); sam log jawnie podaje `original_GATE14=PENDING_NOT_CERTIFIED`. Nie wolno użyć tego wyniku jako PASS oryginalnego PIT.

## Odczyt istniejących nowszych dowodów

- `data/audits/STEP14_FINAL_1140x159_PIT_GATE_2026-10-29.json`: 1140 wierszy, **181260** wymaganych slotów, **0** slotów z oryginalnym dowodem native per-field PIT, `allow_M1_fit=false`, `gate14=PENDING`, TEST nieczytany.
- `data/audits/STEP14_FPL74_2024_MIXED_XG_CORRECTED_V2_RESEARCH_SUMMARY_2026-10-29.json`: 74 badawcze rewizje FPL, 40/760 TRAIN i 107/380 VALIDATION z kompletnym **alternatywnym** player-xG5, lecz **0/760 i 0/380** z oryginalnym natywnym 159-PIT; 3 wersje z przyszłym wynikiem w pliku odrzucono. `data/audits/STEP14_ALL_74_FPL_REVISIONS_ANCHORED_GHARCHIVE_2026-10-29.json` odróżnia SHA źródła i serwerowy zegar potomka od niewiarygodnego committer.date.
- `docs/STEP14_ELO_2023_2026_1140_AND_57_WITNESSED_2026-10-29.md`: 1140/1140 retrospektywnych obliczeń Elo, 57 zweryfikowanych badawczych targetów 2025/26 z częściowymi polami, ale Elo liczone po fakcie nie jest oryginalnym źródłem PIT.
- `docs/PLAN.md`: formalny krok 14 zaakceptowany w **wariancie B**, ale `GATE14_ORIGINAL_STRICT_NATIVE_PIT=PENDING`; ten dokument kontroluje **tylko oryginalny standard** i niczego nie przestawia.

## Niezamknięte niezależne warunki

1. Nie ma per-mecz/per-pole historycznych oryginalnych obserwacji natywnego PitchAPI z udokumentowanym czasem pierwszej publikacji i czasem capture sprzed właściwego kickoff, dla 73 non-xG + 14 flag oraz 48 xG/xGA + 24 flag.
2. Dla `match_id + team_id + period=All + expected_goals` nadal brak pierwszej wersji xG, daty pierwszej publikacji, historii korekt i niezależnego potwierdzenia semantycznej równoważności PitchAPI vs FPL/Opta.
3. Nie istnieje kompletna, audytowalna historyczna macierz 159 wartości i flag PIT dla dokładnie zamrożonych 760 TRAIN i 380 VALIDATION; alternatywne badania, nawet z poprawnym historycznym zegarem źródła publicznego, nie stanowią automatycznie oryginalnych wartości PitchAPI.
4. PASS testów kontroli *blokady* nie jest PASS bramki dopuszczenia danych. Bez nowych autentycznych dowodów brak podstaw do fit oryginalnego M1 i oceny oryginalnego TEST.

**Decyzja:** pozostawić `GATE14_ORIGINAL_STRICT_NATIVE_PIT=PENDING`, `TRAIN=0/760`, `VALIDATION=0/380`; oryginalny M1 bez treningu, TEST nietknięty. Nowe potwierdzenie Git DAG i blobów jest wąskim, audytowalnym dowodem zewnętrznym, nie dowodem spełnienia całości.

## 2026-11-08 — ponowna niezależna kontrola stanu oryginalnego PIT

Odczytano ponownie źródłowy `STEP14_COMPREHENSIVE_HISTORIC_PREMATCH_RECONSTRUCTION_2026-10-28.md`, niniejszy audyt oraz dokument oryginalnej pierwszej publikacji PitchAPI xG. Brak nowego autentycznego `first_available_at_utc` dla oryginalnego PitchAPI `match_id + team_id + period=All + expected_goals`; historyczny FPL player-xG i dzisiejszy PitchAPI team-xG nie stanowią równoważnego dowodu.

W rzeczywistym Actions [#42501013612](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/42501013612) etap `offline-history-safety` przeszedł, a `live-observed-backfill` pobrał **240 nowych historycznych statystyk**, **205 zweryfikowanych xG** i zgłosił **4161 łącznie obserwacji**, lecz krok `Commit immutable private research data only` zakończył się `TypeError: 'int' object is not callable` w `target.stat().st_size()`. Dane z nieudanego przebiegu **nie są uznane za trwale zapisane**. Poprawka `324aa6d` zamienia `st_size()` na właściwość `st_size`; jej pełny wynik CI musi zostać potwierdzony oddzielnie. Ani pozytywny backfill, ani bieżące xG nie dowodzą oryginalnego PIT 2023–2025.

**Formalna decyzja bez zmian:** `GATE14_ORIGINAL_STRICT_NATIVE_PIT=PENDING`, certyfikowane oryginalne wiersze `TRAIN=0/760`, `VALIDATION=0/380`; 121 oryginalnych cech + 38 flag nie są niezależnie poświadczone przed kickoff. Oryginalny M1 nie trenowany, TEST nietknięty. Nie utożsamiać z wariantem badawczym B, ani z sukcesem testów zabezpieczeń.
