# Rejestr decyzji KB Score 3.0 — V3-R chronologiczna wersja badawcza (16.11.2026)

**Decyzja właściciela:** rozwijać drugą, równoległą wersję KB Score 3.0 bazującą na historycznych wynikach i statystykach odtworzonych chronologicznie. Zachować oryginalną V3 i rygorystyczne PIT. To **nie jest zgoda na obniżenie oryginalnych wymagań formalnych ani na promocję modelu produkcyjnego**.

## Zakres wdrożenia

1. Oddzielna nazwa eksperymentu: **V3-R_CHRONOLOGICAL_RECONSTRUCTION**, własny skrypt `scripts/kb3_v3r_walkforward.py`, własne raporty CI. Nie nazywać tej wersji oryginalną V3 121+38 ani 87-vector builderem.
2. Wejście: istniejące, rzeczywiste archiwum SQLite `observations.sqlite.gz` z przypiętym SHA256 i kontrolą odtworzenia. Źródło to historyczne obserwacje pobrane retrospektywnie w 2026 roku; **nie stanowi niezależnego dowodu ich publikacji przed ówczesnym meczem**. Zakaz nadpisania bazy danych.
3. Istniejący builder `scripts/kb3_p1_retro_catboost_1007_376.py` (nie kopiować kodu) odtwarza cechy wyłącznie z **zakończonych poprzednich meczów** przed hipotetycznym cutoff (kickoff minus 2 godziny), z wymaganym opóźnieniem dostępności wyniku poprzednika. Wynik meczu docelowego służy wyłącznie jako etykieta po wytworzeniu cech.
4. Osobne warianty CatBoost 1/X/2: **bez xG (14 cech)** oraz **z retrospektywnymi xG (18 cech)**; każdą brakującą statystykę zachować jako NaN, nigdy jako fikcyjne 0. Kontrola against Laplace train-only baseline. Nie interpretować historycznego xG jako certyfikowanego pre-match xG.
5. Dwa testy *expanding walk-forward* wyłącznie **wewnątrz istniejącego research TRAIN**: granice po 55% i 75% chronologii, siedmiodniowe embargo, grupowanie jednakowych godzin kickoff, zestawy walidacji rozłączne. Parametry CatBoost ustalone przed testem, bez strojenia na walidacji.
6. Po testach wewnętrznych wykonać **jedną oddzielną historyczną walidację** z istniejącego splitu research TRAIN/VALIDATION. Nie używać tej walidacji do fit w żadnym z wcześniejszych foldów. To nadal nie jest prospektywny HOLDOUT.
7. Raport z CI zawiera liczniki, wyniki log loss/Brier/top1, SHA danych wejściowych i modeli badawczych w lokalnych artefaktach. Do artifact przesyłać **tylko raporty agregatów**, a nie pliki źródłowe, surowe dane dostawcy i modele .cbm. Zależności przypięte; zero wywołań PitchAPI lub innych płatnych API.
8. Obowiązujące zakazy: bez dotykania oryginalnego Step14/PIT, 760/380, chronionego ENG 2026/27 TEST, aktywnego M0, oryginalnego modelu M1-R 720/374, kalibracji produkcyjnej, rejestrów prognoz i automatycznego wyboru Championa.

## Kryteria odbioru technicznego

- Testy odrzucają duplikaty, dołączanie oryginalnego VALIDATION lub ENG, niespełnienie 7-dniowego embargo, wspólne kickoffi po obu stronach granicy i zmianę wyników baseline przez etykiety walidacji.
- Raport ma dokładnie dwa niezależne okresy testowe, komplet mierników i dwie odrębne rodziny cech.
- Artefakt powstaje po zakończonym przetworzeniu **rzeczywistych istniejących danych** w GitHub Actions z niezmienną bazą źródeł, a nie tylko po kompilacji kodu.
- Utrzymać `GATE14_ORIGINAL_STRICT_NATIVE_PIT=PENDING`, `GATE16/17=PENDING`, `production_approved=false`, `official_fit_increment=0`. Wariant B kroku 14 nadal jest zaliczony według kryteriów badawczych — nie należy tego cofać ani mylić z oryginalnym PIT.

## Granice interpretacji wyników

Walka z przeciekiem etykiety i chronologiczny podział **nie rozwiązują** ryzyka późniejszej korekty historycznych statystyk (revision bias), braku daty pierwszej publikacji źródła ani driftu dostawcy. Współczynnik trafności z tego eksperymentu nie jest udokumentowaną skutecznością przyszłych zakładów, a porównanie z produkcyjnym M0 będzie wymagało **tych samych przyszłych spotkań i niezależnie zamrożonych prognoz obu modeli**.

## Dalsza kolejność

1. Zweryfikować zielony przebieg CI V3-R i zapisać rzeczywiste metryki, nie przewidywane.
2. Zdecydować o odrębnym, kontrolowanym generatorze nowych, niezależnie archiwizowanych przedmeczowych prognoz V3-R (tylko po sprawdzeniu zgodności cech train/forward). Nie dopuszczać historycznie wygenerowanych prognoz jako `forward`.
3. Na dopiero przyszłych, wspólnych meczach porównywać M0/V3-R i odchylenia kalibracji; bez automatycznej zmiany Championa. Do tego czasu decyzja **RESEARCH_ONLY**.
4. Oddzielnie prowadzić poszukiwanie historycznych źródeł PIT dla pierwotnej V3.

**Uruchamianie:** GitHub Actions `KB3 V3-R chronological reconstructed research (offline only)` — tylko pull_request lub świadome ręczne workflow_dispatch, bez dodatkowego cyklicznego obciążenia i bez nowego kosztu API.


## Wynik faktycznego uruchomienia i odbiór — 16.11.2026

- [PR #179](https://github.com/karolbarankiewicz1984-ui/kb-score-3/pull/179) **MERGED** (squash commit `dd28610e7447a2f75a1f697450354be2c2a8da38`). Zmiany w gałęzi `main`.
- [GitHub Actions #43822657527](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/43822657527): **SUCCESS**. Weryfikacja SHA256 źródłowego, prawdziwe testy, sześć faktycznych fitów badawczych, niezmienność oryginalnych modeli i brak promocji — wszystkie etapy PASS.
- Aktualny zbiór badawczy po rozszerzeniu historycznej bazy: **4550 research TRAIN / 1864 research VALIDATION**. Te liczby nie są oryginalnym 760/380 i nie są nowymi, prospektywnymi próbkami.
- Pierwsza walidacja na dokładnie tych samych 1864 historycznych spotkaniach: wariant 14 cech bez xG: **log loss 1.0397046063, Brier sum3 0.6251960324, top1 46.9957%**; wariant 18 cech z retrospektywnym xG: **log loss 1.0404296571, Brier sum3 0.6256549577, top1 46.7275%**.
- Dodatkowy przedział ufności (bootstrap po tygodniach, 29 tygodni, 600 powtórzeń) dla różnicy xG minus no-xG log loss: **[-0.00328235, +0.00529918]** — nie daje wiarygodnego dowodu przewagi xG w tym historycznym eksperymencie.
- Nazwa artefaktu: `KB3_V3R_RECONSTRUCTED_CHRONO_RESEARCH_METRICS_ONLY` (GitHub Actions artifact ID `14205308088`, raport SHA256 `c9d11570a993fc144292af58db0bbdfe0631160c10e4251aadde581a0589374e`).
- **Decyzja:** techniczne wdrożenie toru V3-R zaliczone. `ORIGINAL_STRICT_PIT=PENDING`, `official_fit_increment=0`, `production_approved=false`. Nie przenosić tych metryk do raportu efektywności M0 ani nie mieszać z prospektywnym HOLDOUT. Kolejna faza: świadomie uruchamiany, zamrażany przed meczem V3-R shadow dopiero po niezależnej kontroli zgodności cech TRAIN/FORWARD.


## Faza 2 — obiektywna kontrola gotowości źródeł V3-R do przyszłych spotkań (16.11.2026)

- `scripts/kb3_v3r_forward_readiness.py` czyta wyłącznie niezmienne, istniejące prognozy M0 i zamrożone SQLite z historycznymi obserwacjami; **zero zapytań API** i żadnych nowych prognoz.
- Każda statystyka 5 ostatnich meczów musi mieć oryginalny `source_observed_at_utc` niepóźniejszy od faktycznego `captured_at_utc` prognozy M0; sprawdzane są czas zakończenia wcześniejszego meczu +3h, natywne ID obu drużyn, data, brak TEST ENG, wynik sprzed meczu.
- Stosowany jest ten sam `build_features_without_target_label`, którego użyto w treningu badawczym. Dostępność klasyfikujemy odrębnie: historia pięciu meczów, komplet 14 cech, komplet 18 cech z xG.
- Wynik statusu `CANDIDATE_14_ONLY` lub `CANDIDATE_ALL_18` jest **kandydatem do dalszego audytu**, a nie pozwoleniem na zamrożenie prognozy: zbiór dawnego indeksu nie zastępuje rzeczywistego kompletnego terminarza z godziną pobrania w ostatniej sesji. Bez porównania z pełną natywną listą ostatnich spotkań i źródłowego odtwarzania TRAIN/FORWARD pozostaje `not_eligible_for_auto_forward_scoring_without_fresh_listing_crosscheck=true`.
- Nowy workflow `KB3 V3-R forward readiness from real M0 (no provider API)`: PR, push na `main`, harmonogram codziennie 13:50 UTC (14:50 CET zimą), ręczny `workflow_dispatch`. Każdy przebieg wgrywa tylko agregowany raport do GitHub Actions, bez eksportu surowych danych. Nie zmienia M0/Shadow Six ani nie promuje V3-R.
- Dalszy etap dopiero po źródłowej gotowości i niezależnym potwierdzeniu train/forward: archiwizacja rzeczywistej prognozy przed kickoff, porównanie tylko z parą M0 tego samego meczu, później właściwy holdout. Nie należy obchodzić braku statystyk przez wstawienie zera.

**Stan decyzyjny:** read-only readiness, `V3R_FULL14_18_SHADOW=NOT_YET_ACTIVATED`, `GATE14_ORIGINAL_STRICT_NATIVE_PIT=PENDING`.


## Wynik faktycznego uruchomienia Fazy 2 — 16.11.2026, 07:47 UTC

- [PR #180](https://github.com/karolbarankiewicz1984-ui/kb-score-3/pull/180) **MERGED**. Oddzielny workflow i testy są na `main`; składnia workflow poprawiona commit `b7e414cd5de3fc3225df2e64cd9a7bedc5e98720`.
- [GitHub Actions #43826225574](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/43826225574) **SUCCESS**, w tym 7 testów niepozwalających na późne obserwacje oraz 5 testów pierwotnego walk-forward.
- Na **70 realnie zamrożonych M0** z rozkładem przyszłych meczów: `STATISTICS_LAST5_INCOMPLETE=70`, `CANDIDATE_14_ONLY=0`, `CANDIDATE_ALL_18=0`. Oznacza to brak wystarczających kompletnych statystyk last5 w aktualnie odtworzonym i datowanym przed cutoff źródle; nie dowodzi braku danych u dostawcy w ogóle.
- Nie utworzono nowych forward V3-R 14/18: `no_new_forward_predictions_generated=true`. M0 i starszy Shadow Six pozostają bez zmian. Potwierdzony sam odczyt 70, nie automatyczny awans.
- Zachowany wyłącznie agregowany plik GitHub Actions artifact ID `14205904600`; raport SHA256 `f6b02f149f8fa93d1834ec68f32fb5b845b56b62918069def8aa1d82d22da711`.
- Następny techniczny bloker i kryteria zakończenia zapisano w [Issue #181](https://github.com/karolbarankiewicz1984-ui/kb-score-3/issues/181): przedmeczowy komplet last5 prawdziwych źródeł z katalogu live + matching feature names/order/units/NaN, potem host-attested forward-shadow i rzeczywisty paired comparison.
- Codzienny odczyt **13:50 UTC**, bez nowych requestów PitchAPI, testów dotykających TRAIN oryginalnego M1, ani pobierania angielskiego TEST. Nie włączać produkcyjnego V3-R na podstawie 70 braków.

**Decyzja:** automatyczny audyt gotowości — **AKTYWNY**, V3-R 14/18 prawdziwy SHADOW — **ZABLOKOWANY DANYMI last5**, oryginalny PIT — **PENDING**. Dalsze przygotowanie zbierania statystyk wymaga kontrolowanego limitu istniejącego API, bez fikcyjnych prognoz.


## Faza 3 — decyzja właściciela: dane opcjonalne nie zatrzymują modelu (16.11.2026)

**Dyspozycja:** pobieramy rzeczywiste statystyki ostatnich pięciu meczów; jeżeli pojedynczego parametru nie ma, ignorujemy tylko jego wartość wejściową, ale nadal szukamy go w następnych zbiorach. Nie traktujemy braku jako zera. Nie zatrzymujemy całego przetwarzania z powodu pojedynczej niedostępnej statystyki.

### Nowa polityka danych V3-R FLEX

| Kategoria | Gdy dane istnieją | Gdy brakuje |
| --- | --- | --- |
| Natywne ID meczu/drużyn, czas i wynik 90 min | Weryfikacja źródła | **Kwarantanna błędnego rekordu**, nie dopuszczać danych z innego meczu ani z przyszłości; inne mecze działają dalej |
| Historyczny ostatni wynik / forma 5 | Obliczamy na dokładnie pięciu poprzednich meczach | Wektor może zawierać `null/NaN`, ale przy braku wiarygodnego łańcucha pięciu spotkań **pozostawiamy M0 jako działającą prognozę zastępczą** |
| Strzały, faule, rożne i żółte kartki | Korzystamy z rzeczywistej wartości dla tych samych pięciu meczów | `null/NaN` w odpowiedniej cesze; pozostałe cechy pozostają aktywne |
| xG / xGA | Tylko prawidłowa definicja i sprawdzony natywny provider | `null/NaN`; wybieramy wariant bez xG lub model z natywną obsługą braków, nigdy `xG=0` |
| Status pobierania | Osobny licznik rzeczywiście pozyskanych parametrów | Osobna kolejka `missing_fields_retry_queue`, bez fałszywego statusu PASS źródłowego |

**Ważne:** każda wartość średnia ze zdefiniowanego okna pięciu musi mieć pełne 5/5 rzeczywistych obserwacji; brakujące 2 z 5 nie mogą zostać zastąpione obliczeniem 3/5 i opisane jako 5/5. W ten sposób zachowujemy identyczną definicję cechy po stronie treningu i przyszłych prognoz. CatBoost przyjmuje `NaN`; parametry i wcześniejsze historyczne wyniki pozostają niezmienione. W przypadku braków modelu V3-R istniejący M0 nie przestaje pracować.

### Pobieranie realnego źródła

- Priorytet `scripts/kb3_v3r_last5_priority.py` bierze wyłącznie **rzeczywiste, już zamrożone przyszłe mecze M0**, dopasowuje natywne ID, oba zespoły i UTC do **nowej, oryginalnej listy PitchAPI** i wybiera brakujące autentyczne spotkania z ostatniej piątki. Zły match ID trafia do kwarantanny, a nie do treningu.
- Samo pobranie wykorzystuje istniejące `scripts/kb3_historical_pitchapi_backfill.py`, szyfrowanie oryginalnych odpowiedzi źródłowych i zapis append-only z rzeczywistą datą obserwacji. Żadnej wartości nie przesuwamy w czasie wstecz do daty zamrożenia poprzedniego M0.
- **Limit:** 1 paczka do 24 meczów na przebieg; do 150 wywołań historycznego dostawcy na paczkę plus maksymalnie **12** osobnych zapytań recheck (3 xG × 2 i 6 kart × 1). Uruchomienia planowane **02:15 i 14:15 UTC** (3 wcześniejsze zastąpiono 2). Wyłączone próby automatycznego ponawiania SDK. Priorytet dotyczy obecnych przyszłych meczów, a pozostała część paczki zachowuje historyczny gain-first backfill.
- Jeśli statystyk meczu nie da się pobrać, pozostaje on nierozwiązany i kwalifikuje się ponownie; `new_match_stats` liczy wyłącznie naprawdę uzyskane, zweryfikowane źródła, nie liczy prób ani szacunków.
- Nie przerabiać wcześniejszego zamrożenia M0 z 15 listopada na nową prognozę V3-R; przed nową prognozą konieczne są rzeczywiście aktualne wejścia i nowy serwerowo potwierdzony dowód czasu. Przy złej tożsamości/niezgodnej definicji danych nie wolno publikować wyliczenia, ale nie zatrzymuje to pozostałych lig.

### Bramka uruchomienia pełnego V3-R Shadow

`V3R_FLEX_OPTIONAL_MISSING_ALLOWED=true` nie oznacza jeszcze `V3R_LIVE_MODEL_ACTIVATED=true`. Wymagana jest oddzielna zgodność trening/forward, przypięty dokładny model CatBoost, host-attested nowa prognoza i kompletna lista terminarza. Do tej chwili działają M0 i dotychczasowy Shadow Six, a V3-R przygotowuje prawdziwe statystyki i kontroluje braki. `GATE14_ORIGINAL_STRICT_NATIVE_PIT=PENDING`, `TEST` oraz model Champion nienaruszone.

## Wykonanie rzeczywistego pobierania — 16.11.2026, 08:25 UTC

- [PR #182](https://github.com/karolbarankiewicz1984-ui/kb-score-3/pull/182) **MERGED**, nowa polityka opcjonalnych braków i priorytet rzeczywistych ostatnich pięciu spotkań są na `main`.
- [GitHub Actions #43830691797](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/43830691797) **SUCCESS**, wszystkie etapy w tym źródła i zapis repozytorium. Pierwszy przebieg #43830430410 miał błąd typu znacznika UTC (tekst zamiast `datetime`); poprawka `fe5f0cc9dd714e13a90613746e54086fed1082fe` i ponowienie zostały faktycznie potwierdzone.
- [Oryginalny raport źródłowy](../data/pit_sidecar/historical_multistat/2026-11-16/run-43830691797-1-b1/HISTORICAL_BACKFILL_REPORT.json): **24 nowo zweryfikowane rzeczywiste statystyki spotkań**, **23 zweryfikowane natywne xG**, **0 błędów pobrania statystyk**; stan całkowity `observed_stats_matches=7304`, `verified_native_xg=6488`.
- **70/70** istniejących rzeczywistych przyszłych prognoz M0 dało się dopasować do bieżącej natywnej listy PitchAPI bez niezgodności ID/zespołu/UTC. Znalazło się **334 unikatowych brakujących wyników pobrania statystyk autentycznych poprzedników last5**, z których **18** weszło do paczki. Pozostało **316** w kolejce (stan liczony przed faktyczną realizacją paczki; przy 18 udanych pobraniach odpowiada niewypełnionej reszcie). Pozostałe 6/24 spotkań wybrano historyczną metodą gain-first.
- [Raport całej sesji](../data/pit_sidecar/historical_multistat/2026-11-16/run-43830691797-1-summary/ACCELERATED_CAPTURE_REPORT.json): **83 rzeczywiste wywołania historii + 8 recheck**, w tym cztery potwierdzone brakujące wartości żółtych kartek przez eventy, 1 niezgodność xG nadal oznaczona brakującą, bez fałszywego PASS. Zapisy źródeł zaszyfrowane, odrębne, z datą pobrania; żadne `first_published` historyczne nie zostało wymyślone.
- Prawdziwe zamrożenia M0 wykonane wcześniej (np. 15.11) nie zmieniają czasu swoich źródeł. Nowe obserwacje z 16.11 mogą służyć **tylko przyszłemu, późniejszemu odczytowi V3-R**, po sprawdzeniu zestawu cech i niezależnym freeze. Nie można przedstawiać ich jako część starej prognozy.
- Kontrola jakości V3-R [#43830429817](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/43830429817) **SUCCESS** i rozpoznała 70 przypadków `PARTIAL_NAN_OK_RESEARCH`. To decyzja przepływu, **nie 70 nowych prognoz V3-R**. Na razie M0 pracuje jako istniejący forward baseline.
- Dalszy automat: 02:15 i 14:15 **UTC** (03:15/15:15 CET), jedna paczka 24 mecze + maks. 12 rechecks na przebieg. Nadal 316 poprzedników może wymagać pobrania, a pojedyncze niedostępne parametry nie zatrzymują dalszej analizy badawczej.

**Stan:** rzeczywiste dane pobrane i zapisane; polityka braków wdrożona; pełny nowy `V3R_14_18_FORWARD_SHADOW` jeszcze nie zatwierdzony ani niezamrożony. Oryginalny strict PIT pozostaje `PENDING`; M0, poprzedni Shadow Six i chroniony TEST bez zmian.

## Faza 4 — uruchomienie niezależnego V3-R SHADOW (dyspozycja właściciela, 16.11.2026)

- Od dziś wariant badawczy **CatBoost 14 cech bez xG** przechodzi z walidacji retrospektywnej do **oddzielnej, faktycznej prognozy przyszłej**. Oryginalna V3, M0, Shadow Six i chroniony angielski TEST bez zmian.
- `scripts/kb3_v3r_forward_shadow.py`: przy pierwszym uruchomieniu trenuje **tylko na istniejącym, historycznie rekonstruowanym research TRAIN**; walidacja nie jest dołączona do fit. Zamraża na stałe plik `assets/research/kb3_v3r_forward/v3r_no_xg_14.cbm` oraz manifest z SHA256 binarki, cechami w kolejności, SHA źródła, liczbą TRAIN, parametrami i `production_approved=false`. Następne runy **nie trenują ponownie i nie zmieniają oryginalnego modelu**.
- Jedynie już istniejące i rzeczywiście zamrożone prognozy M0 mogą być źródłem pary. Pobierane są **nowe** natywne listy PitchAPI (`CURRENT` + `PREVIOUS`), osobno weryfikowane dla każdego z ośmiu krajów. Nie zostanie wywołane API dla ENG/chronionego TEST. Dopasowujemy komplet natywnych ID, drużyn, UTC i brak wyniku przyszłego meczu.
- Cechy `home/away goals_for,goals_against,points,total_shots,fouls,corners,yellow_cards` powstają przez **ten sam builder co TRAIN** z prawdziwych pięciu ostatnich zakończonych spotkań; tylko dane źródłowe z oryginalnym `observed_at` niepóźniejszym od nowego uruchomienia. Brak opcjonalnych statystyk to `NaN`, nigdy `0`. Przy braku rzeczywistego łańcucha pięciu wyników pozostaje M0 i osobna kolejka nieuzupełnionych danych.
- Każda **nowa** prognoza V3-R jest oddzielnym niezmiennym JSON w `data/v3r_shadow/forecasts/LEAGUE/NATIVE_MATCH_ID.json`, nie zamienia, nie aktualizuje i nie wstecznie dołącza starej prognozy M0. Raport + SHA powstają w `data/v3r_shadow/reports/`, a oryginalne bieżące odpowiedzi PitchAPI są zaszyfrowane w `data/v3r_shadow/sources/`.
- Prawdopodobieństwa dotyczą **wyłącznie rynku 1/X/2**. Co najmniej 90 minut przed kickoff (preflight wymagający 3 godzin zapasu na start), bez dostępu do etykiety docelowego meczu. Udowodnienie daty publikacji przez niezależny GitHub-host artifact pozostaje odrębnym audytem: `independent_host_publication_proof_pending=true` nie może być nazwane dowodem, dopóki nie potwierdzi się rzeczywistej daty GitHub.
- GitHub Actions `KB3 V3-R real future CatBoost Shadow (isolated from M0)` uruchamia testy na PR **bez klucza API**, a na `main`: od razu po merge, ręcznie i automatycznie codziennie 07:09/13:09/19:09 UTC. Nie pobiera żadnego API, kiedy nie ma nowych uprawnionych par M0; maksymalnie 17 network calls przy pełnym zakresie ośmiu lig.
- **Nie wolno** liczyć wyniku z wcześniejszego przedmeczowego cutoff M0, uzupełnionego po jego zamrożeniu, jako „wtedy prognozowany V3-R”. V3-R otrzymuje **swój nowy** rzeczywisty cutoff i jest porównywany z tym samym meczem M0 dopiero po faktycznym rozegraniu.
- `ORIGINAL_STRICT_PIT=PENDING`, `official_fit_increment=0`, `V3R_SHADOW_RESEARCH_ONLY`, `production_approved=false`, bez automatycznej promocji Championa. Prawdziwa przewaga M0 vs V3-R będzie wymagała przyszłych wspólnych rozstrzygniętych spotkań.

## Faktyczny start V3-R Shadow — 16.11.2026, 13:21 UTC

- [PR #183](https://github.com/karolbarankiewicz1984-ui/kb-score-3/pull/183) **MERGED**, squash `5fb66a0e78d392398f95cc669bcfd3cabb8cca71`.
- [GitHub Actions #43874724829](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/43874724829) **SUCCESS**, także live job i końcowy zapis do `main`; nowy artefakt GitHub Actions ID `14229541037`, serwerowa data utworzenia 2026-11-16 13:21:49 UTC.
- Faktycznie utrwalono **70 nowych, przedmeczowych prognoz V3-R** 1/X/2 na **70 tych samych przyszłych meczach, co istniejące M0**. Rozkład: BEL 9, ESP 9, FRA 9, GER 9, ITA 9, NED 9, POL 8, TUR 8. **149 wcześniejszych/niekwalifikujących się M0** nie zostało retroaktywnie przetworzonych.
- [Niezmienny raport nowego przebiegu](../data/v3r_shadow/reports/2026-11-16/run-43874724829.json): `new_future_frozen_forecasts=70`, `new_m0_parent_candidates=70`, `unavailable_reasons={}`, `provider_network_request_count=17`, `production_approved=false`. Raport SHA256 `11c29b714137be919d4ad4c3c3b1afd7ea919aa46715b7b027dd8cde00f482d6`.
- [Manifest przypiętego modelu](../assets/research/kb3_v3r_forward/manifest.json): rzeczywiście wytrenowany **CatBoost 14 cech**, wyłącznie `4555` historycznych `TRAIN`, bez `1864` `VALIDATION`, `model_binary_sha256=0faa6159d9d94f8e4931506103ede2d77ada0542f618eb2309ff4da95f78c946`, `manifest_sha256=06fcfa3f3befd3a2264248fc3b269c0ec76c912051586a144297929529fd6435`. Zapisany model ma być używany na następnych runach **bez ponownego fit**.
- Wszystkie rzeczywiste wejścia zamrożone z nowymi źródłami natywnego PitchAPI (17 calls, 8 krajów, poprzedni i bieżący sezon), nie z retrospektywnie przeniesioną datą starego M0. Oryginalne odpowiedzi zaszyfrowano. Braki opcjonalnych statystyk oznaczono jako `NaN`, a istniejące M0 pozostawiono bez zmian.
- Kontrola GitHub Actions sprawdziła 70 rekordów po ich wygenerowaniu: `generated_at_utc < kickoff_utc - 90 min`, spójność SHA i prawdopodobieństw 1/X/2 oraz zakaz promocji. Serwerowy artefakt zapisano, jednak niezależna walidacja historycznego dowodu bajt-po-bajcie/host-publication jest jeszcze **PENDING**, zgodnie z `independent_host_publication_proof_pending=true` w każdym rekordzie.
- Dalszy krok: gdy mecze się zakończą, rozliczać i porównywać V3-R vs M0 na wspólnych spotkaniach (accuracy, log loss, Brier, kalibracja), a jednocześnie zbierać źródła dla kolejnych prognoz. **Nie wymagać 316 brakujących retrospektywnych statystyk jako blokady następnego Shadow run.**

**Wynik operacyjny: `V3R_14_FWD_SHADOW=ACTIVE`, `production_approved=false`, `champion_unchanged=M0`, `original_V3_gate14=PENDING`.**
