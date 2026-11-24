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
