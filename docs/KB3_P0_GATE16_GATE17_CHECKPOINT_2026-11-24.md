# KB Score 3.0 — checkpoint P0 / GATE16 / GATE17 z 24.11.2026

**Zakres:** rzeczywisty najnowszy dostępny M0 settle z 23.11 godz. **20:15:44 UTC**; wykonana 24.11 kontrola repozytorium i kodu, bez zewnętrznego dopowiadania wyniku meczu. **Nie** jest to nowy settle, nie przeprowadzono dopasowania modeli ani nie zmieniono chronionego TEST.

## Źródło prawdy i liczby

- [Oryginalny frozen/proof/settle receipt M0 23.11 20:15 UTC](../data/pit_sidecar/m0_720_eight/2026-11-23/settle-201542175506/RECEIPT.json) — ostatni odnaleziony receipt na tym checkpoint.
- [Nowe autentyczne 18 prognoz 23.11 18:29 UTC](../data/pit_sidecar/m0_720_eight/2026-11-23/forecast-182908259177/RECEIPT.json), 15 źródłowych API calls, 7 z 8 lig (bez TUR); 18 nowych meczów i 36 odpowiednio utworzonych challenger forecastów (dwa silniki na mecz, nie 36 meczów).
- **286** łącznie host-verified forward forecasts; **208** settled; **78** unready. Ten settle dodał **0** nowych wyników. Dokładne powody: **66** `RESULT_MATURITY_3H_NOT_REACHED`, **9** `PROVIDER_RESULT_MISSING` (wszystkie **TUR**), **3** `KICKOFF_CHANGED_REVIEW_REQUIRED` (**FRA 2, POL 1**).
- Metryki 208 dotychczas rozliczonych: M0 top1 119/208 = 57,21%, Brier sum3 0,57413328, log loss 0,96656331. To metryki badawcze, nie ROI i nie proof wygranej.
- Kontrola publikacji host: w receipt `publication_proof_audit.verified_forecast_rows_total=286`, `actions_artifact_verified_rows_added=18` i `still_unproven=0` dla tej procedury. Nie dowodzi to oryginalnej historycznej daty publikacji 2023–2025.

## Trzy prawdziwe rozbieżności kickoff, pierwsza pełna diagnostyka

Wszystkie poniższe wartości pochodzą z **rzeczywistej** `settlement_decisions` źródłowego receipt z 23.11 o 20:15 UTC. Każda ma `provider_home_id_matches_original=true`, `provider_away_id_matches_original=true`, `original_capture_before_earliest_90m_cutoff=true`, `manual_review_required=true`, `automatic_settlement_permitted=false`.

| Liga / natywne ID | Oryginalny frozen UTC | Provider podaje UTC | Delta | Oryginalny capture UTC |
| --- | --- | --- | ---: | --- |
| FRA `m_1ronn6` | 07.11 16:15 | 07.11 18:00 | +105 min | 04.11 14:43:51 |
| FRA `m_264TKg` | 07.11 19:45 | 07.11 20:05 | +20 min | 04.11 14:43:51 |
| POL `m_4dpQ5H` | 21.11 19:15 | 21.11 19:45 | +30 min | 15.11 20:09:18 |

**Weryfikacja osiągnięta:** ten sam natywny ID, te same home/away, czas freeze wcześniejszy od obydwu cutoffów, źródłowy nowy kickoff i jego delta są policzone. **Nadal brak osobnego, niezależnego źródła potwierdzającego oficjalną zmianę godzin i wyniku końcowego 90 min dla tych trzech ID.** Obecny receipt nie ma pełnego protokołu ręcznej autoryzacji i **nie uprawnia do automatycznego rozliczenia**. Nie podmieniać pierwotnego kickoff ani nie stosować zewnętrznego wyniku bez pozytywnego mapowania pary klubów i dat.

**Dokładne 9 brakujących wyników TUR:** `m_0DtFS8`, `m_2Nqkzr`, `m_1J9qAA`, `m_4Nltap`, `m_42ahTy`, `m_0d0c1o`, `m_1lrxfA`, `m_053xJU`, `m_3tsGl4`. Brak w aktualnej siedmioligowej odpowiedzi PitchAPI nie jest dowodem wyniku. Pozostałych **66** nie traktować jako błędów, dopóki wymagane `kickoff + 3h` w odpowiedniej migawce nie minie.

## Wykonane kontrole i nowe poprawki 24.11

- [`scripts/kb3_review_postfit_readonly.py`](../scripts/kb3_review_postfit_readonly.py): audyt pending został zaostrzony — każdy nierozliczony forecast wymaga host-attributed `github_server_event_utc` między capture a oryginalnym `kickoff - 90 min`. Brak dowodu, za późna publikacja lub brak tożsamości = wyjątek `PENDING_HOST_PUBLICATION_NOT_BEFORE_CUTOFF`, a nie cichy PASS. Po poprawce na zmieniony kickoff dodatkowo weryfikowane jest `host <= min(original, provider) - 90min`, bez auto-override. W raporcie nowe pola jawnie rozdzielają **pozytywną wewnętrzną zgodność source ID/cutoff** od **niedostępnej niezależnej weryfikacji oficjalnego kickoff i wyniku końcowego**.
- Dodane syntetyczne regression checks dla **opóźnionego/missing host proof** oraz dla zgodnego źródłowo, lecz wciąż **kwarantannowanego** przesunięcia kickoff. Nie znoszą kwarantanny.
- **GATE16 forward follow-up:** nowa read-only sekcja `post_holdout_forward_followup` wybiera z host-verified, settled M0 wyłącznie mecze zamrożone **po `holdout_review.reviewed_at_utc`**, poza FIT100 i HOLDOUT50. Wyniki liczy na surowych `p_1x2` i niezmienionym `T=0.7`, bez re-fit, zmiany modeli, parametrów, FIT/HOLDOUT czy protected ENG TEST. W receipt z 23.11 było **61** potwierdzonych po FIT, z czego 50 użyto w pierwszym HOLDOUT; pozostałe **11** to *kandydaci* spoza tej pierwotnej próbki, **nie** automatycznie 11 kwalifikowanych po całym REVIEW. Raport poda rzeczywistą liczność ściśle nowszej podpróbki po wykonaniu CI.
- **GATE17:** trzy silniki mają 135 identycznych rozliczonych spotkań w 2 niezależnych blokach tygodniowych. Do wiarygodnych przedziałów potrzeba 8 ISO-week blocks i rzeczywistych `ci95` dla trzech par i trzech metryk. Poprzedni rozjazd 4 vs 8 tygodni poprawiony; **GATE17=PENDING**.

## Dowód uruchomienia / granice odbioru

Nowy plik kodu, testowe asercje, raport i rejestr zostały zapisane w GitHub. **Nie ma w tym checkpoint osobno zweryfikowanego `COMPLETED SUCCESS` z nowej wersji CI** ani nowej rzeczywistej oceny GATE16 follow-up z tego właśnie kodu. Nie nadpisywać stanu statystycznego raportów na podstawie samych zmian kodu. Po następnym faktycznym Actions run i receipt dopisać run ID, wyniki testów i niezależne obserwacje. Brak dostępnego nowego receipt po 23.11 20:15 UTC **nie przesądza**, czy zaplanowany późniejszy job uruchomił się, pominął zapis czy zawiódł — wymaga sprawdzenia job logów.

## Następne czynności w kolejności

1. **P0:** sprawdzić wynik rzeczywistego GitHub Actions po wdrożeniu; odczytać najnowszy M0 `settle`, porównać `286 / 208 / 78` i host proof, nie dopuszczać fake settle. Zweryfikować niezależnie 3 oficjalne zmiany kickoff i autentyczne wyniki 90min, nie zmieniając frozen forecast; 9 TUR po powrocie źródła.
2. **GATE16:** odczytać raport `post_holdout_forward_followup`, policzyć metryki ściśle nowszej kohorty per liga/tydzień; dopiero po kolejnych niezależnych tygodniach dokument decyzji, bez FIT na HOLDOUT.
3. **GATE17:** po każdym nowym settlement odświeżyć identyczne pary M0/Elo-only/CatBoost no-xG, metryki Brier/log loss/top1, 8 niezależnych tygodni i realne cluster-bootstrap CI. V3-R, Shadow Six i rynki nie mogą być bez kontroli wersji dodawane do 135.
4. **P2:** oryginalny historyczny PIT 159 pól pozostał 0/760 TRAIN i 0/380 VALIDATION, brak dowodu pierwszej publikacji. Pozostać przy FORWARD FIRST; bez auto-promocji.

**Bramki po tej operacji:** `GATE16=PENDING`, `GATE17=PENDING`, oryginalny `GATE14 STRICT=PENDING`, `Champion` bez zmian. Brak zakupów API i nieautoryzowanego dostępu do chronionego TEST.

## Dalszy niezależny cross-check 24.11 — oficjalne godziny potwierdzone, natywne ID nadal wymagają mapowania

Po pierwotnym repo-only audycie sprawdzono także **niezależne zewnętrzne źródła** (tylko do odczytu; nie zasilono bazy wynikami). Utworzono nieprodukcyjny, wersjonowany [`data/audits/KB3_SHIFTED_KICKOFF_EXTERNAL_CROSSCHECK_2026-11-24.json`](../data/audits/KB3_SHIFTED_KICKOFF_EXTERNAL_CROSSCHECK_2026-11-24.json), commit [e794210d](https://github.com/karolbarankiewicz1984-ui/kb-score-3/commit/e794210d898c933f0a765e9d27f012ce23086eed). W pliku jest jawny `native_id_team_name_mapping_verified=false`, `no_auto_settlement=true` i osobne pola wyników wyłącznie **kandydatów meczu oficjalnego**, nie wyników przypisanych do prognozy.

1. **FRA `m_1ronn6`:** 07.11 16:15→18:00 UTC = 17:15→19:00 CET. Oficjalny [komunikat LFP](https://www.lfp.fr/article/les-coups-d-envoi-de-aj-auxerre-paris-fc-et-psg-estac-troyes-decales) (04.11) potwierdza **AJ Auxerre – Paris FC**, dokładnie **+105 minut**. Niezależna [informacja Paris FC](https://parisfc.fr/en/pro-mens-team/aj-auxerre-vs-paris-fc-kickoff-postponed/) i [raport Ligue 1 z 8.11](https://ligue1.com/en/articles/l1_article_6054-j10-les-enseignements-du-week-end-ligue-1-2026-2027) wskazują oficjalny mecz i jego kandydacki wynik **0:1**. **Brak nadal dowodu, że natywny ID `m_1ronn6` faktycznie odpowiada tej parze klubów w obu stronach.**
2. **FRA `m_264TKg`:** 07.11 19:45→20:05 UTC = 20:45→21:05 CET. Ten sam [oficjalny LFP](https://www.lfp.fr/article/les-coups-d-envoi-de-aj-auxerre-paris-fc-et-psg-estac-troyes-decales) i [terminarz PSG](https://www.psg.fr/en/content/ligue-1-matchday-10-fixtures-2026-2027-paris-saint-germain-estac-troyes) potwierdzają **Paris Saint-Germain – ESTAC Troyes**, dokładnie **+20 minut**. [Strona PSG po meczu](https://www.psg.fr/en/matches/mens-football/20262027/paris-vs-troyes-2026-11-07) podaje kandydacki wynik **1:0**, lecz nie jest jeszcze połączony z natywnym `m_264TKg` przez zweryfikowaną tabelę team-ID → nazwa.
3. **POL `m_4dpQ5H`:** 21.11 19:15→19:45 UTC = 20:15→20:45 CET. [Oficjalnie pierwotny terminarz Ekstraklasy](https://ekstraklasa.org/aktualnosci/terminarz-15-kolejki-202627/) podawał **Radomiak Radom – Wisła Kraków o 20:15**, a relacja [TVP Sport](https://sport.tvp.pl/96609695/pko-bp-ekstraklasa-wisla-krakow-nie-wyszla-na-mecz-z-radomiakiem-radom/amp) potwierdza faktyczny początek **20:45, +30 min**. [Oficjalna karta meczowa Ekstraklasy](https://ekstraklasa.org/mecz/3141ed0a-7da2-482a-8126-065afd29c91d/radomiak-radom-wisla-krakow/przeglad/) podaje kandydacki wynik **0:0**. Nie dowodzi natywnego przypisania `m_4dpQ5H` do Radomiaka i Wisły bez jawnych, sprawdzonych danych provider team-ID.

**Status po nowym dowodzie:** przesunięcia w harmonogramie odpowiadają dokładnie rzeczywiście opisanym meczom, więc **sam fakt zmiany godziny ma silne zewnętrzne potwierdzenie**. Pozostaje jednak kontrola połączenia `native_match_id → provider home_team_id/away_team_id → dokładne nazwy klubów` z oryginalnego zaszyfrowanego źródła i wyników 90min. **Żadnego automatycznego rozliczenia, zmiany starych prognoz, nowych M0 settlement ani zmiany liczności 208/78.** Nie traktować JSON `external_candidate_final_score_90min` jako autoryzowanego wejścia do algorytmu rozliczania.
