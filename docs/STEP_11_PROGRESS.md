# KB Score 3.0 — KROK 11 / START / GATE11 PENDING

**Data:** 26.10.2026. **Status:** W REALIZACJI, NIE ZALICZONO. **Postęp zatwierdzony:** 10/29.

## Pierwsza implementacja

- src/kb3_features.py: ELO (roboczo start 1500, K=20, przewaga gospodarzy 65), forma ostatnich 5/10/15 gier, osobno dom/wyjazd; punkty, gole, ELO dawnych przeciwników, liczba dni od poprzedniego meczu, realne xG/xGA.
- tests/test_step11_features.py: negatywne testy cutoff, przyszłych wyników, danych docelowego meczu, spóźnionej publikacji, niezatwierdzonego mapowania, konfliktu xG, błędnego jednoczesnego meczu.
- scripts/step11_features_audit.py: porównanie trybów dla 380 meczów pilotażu z eksportem wyłącznie zliczeń.
- .github/workflows/kb3-step11-features.yml: testy offline i kontrolny import 380 meczów z aktywnego GitHub Secret API-Football. Bez wycieku bazy do artefaktów.

## Katalog cech i czasu dostępności

| Cecha | Źródło i bramka | Brak danych |
|---|---|---|
| home/away_elo | wcześniejsze zaakceptowane wyniki 90 minut, status STRICT+APPROVED | prior 1500 i games_available=0 |
| all/venue_5/10/15_points_avg | wcześniejsze wyniki w tym sezonie | NULL, n i missing_flags |
| all/venue_5/10/15_gf_avg / ga_avg | wcześniejsze bramki zdobyte / stracone | NULL, n i flaga |
| all/venue_5/10/15_opponent_elo_avg | ELO rywala przed dawnym meczem | NULL, flaga |
| all/venue_5/10/15_xg/xga_avg | wyłącznie rzeczywiste obserwacje xG z pochodzeniem i czasem | NULL, nie 0; xg_n i xga_n |
| days_since_last_kickoff | data ostatniego dopuszczonego meczu | NULL |
| elo_home_minus_away | poprzedni rating dwóch drużyn | roboczy prior, licznik historii |

Tryb **verified** dopuszcza wcześniejsze wyniki tylko z dowodem publikacji i
odczytu przed cutoff oraz zatwierdzonym ID. Bez certyfikacji samego snapshotu
meczu docelowego cały wynik ma klasę NOT_VERIFIED; training_allowed=false.

Tryb **replay** jest wyłącznie retrospektywną symulacją dla poprzednich
meczów starszych o minimum 48 godzin. RETROSPECTIVE nie oznacza realnej
historycznej dostępności danych. training_allowed=false. Oba tryby mają
SHA-256, lineage i flagi NULL; nie uwzględniają kursów ani wyniku docelowego.

## Co nadal blokuje odbiór

W SQLite obecnie tylko **380 rzeczywiście importowanych meczów** PL 2024/25;
**10 679** to dotychczas liczba w źródłowym katalogu API, nie liczba
rekordów w treningowej bazie. Brak archiwum point-in-time, pełnych statystyk
i xG. ELO K i przewaga gospodarzy są robocze i nie zostały wytrenowane.

Wymagany niezależny audyt GitHub Actions (11 testów syntetycznych + regresja
i realny pilot), zapis dowodów w PLAN/ZMIANY oraz źródłowym Google Docs.
**Na razie START, NIE PASS.** Bez dodatkowych zakupów, bez zmian w KB2.1,
API Market i MultiModel, bez modeli ML i automatycznych typów.


## 26.10.2026 — rozbudowa ELO o historię między sezonami (GATE11 NADAL PENDING)

- Silnik `src/kb3_features.py` v0.2: poprzednie sezony tej samej **ligi/competition_id** są dopuszczane do historii ELO i cech rolling tylko przy spełnieniu dotychczasowej bramki czasu i mapowania. Sezony z przyszłości i inne ligi nie mogą wejść do cech.
- `EloParameters` to niemutowalna konfiguracja z walidacją zakresów: rating startowy 1500, K=20, przewaga domowa 65, skala 400, zachowanie ratingu między sezonami 0.85. **Wszystkie wartości są PROWIZORYCZNE, nie dopasowane na TRAIN**. Żadne przeszukiwanie K/H, fit ani trening nie odbywają się w kroku 11.
- Korekta sezonowa: `R_new_season = 1500 + (R_old_season-1500) * retention**number_of_seasons`. Dotyczy wyłącznie chronologicznie wcześniejszych sezonów, również gdy klub opuści ligę na kilka lat. Brak historii w lidze nie uprawnia do imputowania meczów rozegranych w innych rozgrywkach.
- Nowe liczności `*_elo_games_available` i `*_prior_seasons_games_available`, jawny `elo_parameters`, `elo_parameter_status`, sezon w `lineage`; hash cech obejmuje wybraną wersję parametrów.
- Sześć dodatkowych testów syntetycznych: kontynuacja ratingu, izolacja konkurencyjnej ligi, przyszły sezon, przerwa wieloletnia, walidacja parametrów, wpływ parametrów na hash.
- Ważne ograniczenie: przy faktycznej bazie pilota nadal **tylko PL 2024/25 / 380 meczów**. Test integracyjny obejmujący **dwa rzeczywiście importowane sezony** oraz ustalenie archiwalnej dostępności informacji pozostają otwarte. Dokładne liczby rzeczywiście sprawdzonych testów CI należy odczytywać z biegu GitHub Actions, nie z tej deklaracji.
- Nie zmieniamy statutu `training_allowed=false`, `verified`/ `replay`, bramek jakości ani wznowienia kroku 12. Bez automatycznego awansu GATE11.

## Potwierdzony pilotaż dwóch sezonów — 26.10.2026

- [GitHub Actions #40289840095](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40289840095) **SUCCESS**: trzy zadania `offline-tests`, `pilot-380`, `pilot-760` zakończone powodzeniem.
- **58/58** testów offline PASS (19 Step11: 11 początkowych + 6 dla ELO + 2 integracyjne; 39 regresyjnych Step08–10). Oddzielnie: **380/380** w dotychczasowym pilocie i **760/760** w nowym teście importu dwóch zakończonych sezonów Premier League (2023/24 i 2024/25).
- Dwa sezony: **23 różne drużyny**, bez dubli przy dwukrotnym imporcie; 3 kontrolne mecze z sezonu 2024/25 miały po 76 wcześniejszych udziałów obu drużyn z poprzedniego sezonu.
- Drugi pilot działał **wyłącznie w tymczasowej przestrzeni GitHub Actions**. **Nie utworzono ani nie zapisano trwałego zaszyfrowanego backupu bazy 760 meczów**. Baza trwale zabezpieczona wcześniej nadal obejmuje jednosezonowy pilot 380. Artefakty GitHub Actions zawierają wyłącznie zliczenia i hashe źródła, nie bazę czy wiersze spotkań.
- `verified`: historyczne mecze bez wiarygodnych timestampów nadal nie są certyfikowane; `replay` to retrospekcja, nie poprawne historyczne zamrożenie przedmeczowe. Brak autentycznych xG historycznych w bazie. **GATE11 nadal PENDING; 10/29, training_allowed=false.**
- Do wykonania przed odbiorem: trwałe bezpieczne archiwum rozszerzonej bazy zgodne z uprawnieniami dostawcy, szersze źródła, realne snapshoty z udokumentowaną dostępnością i sprawdzenie xG/pokrycia, niezależna kontrola GATE11.


## 26.10.2026 — pochodzenie wyników i xG, realny audyt PitchAPI

- Kod cech v0.3: do historii wyników wybierane jest **mapowanie dostawcy wyniku** wskazanego w `fixtures.result_source`, a nie wszystkie mapowania tego spotkania. Osobne obserwacje xG są przyjmowane tylko przy **STRICT + APPROVED** mapowania *tego samego dostawcy* i zgodnym `source_snapshots.provider_id`. Dzięki temu dołączenie PitchAPI do meczu API-Football nie tworzy fałszywego duplikatu historycznej pozycji.
- W trybie `verified` odrzucany jest bieżący rekord wyniku, jeżeli `fixtures.updated_utc` następuje po `source_snapshots.captured_at_utc` skojarzonego dowodu. Historyczny timestamp nie może usprawiedliwiać późniejszej mutacji rekordu. Ta kontrola jest **konieczna, ale niewystarczająca**: nie mamy zapisanego dowodu kryptograficznego wiążącego konkretny **wiersz wynikowy** z jego oryginalnym payloadem źródła; `row_payload_at_snapshot_proven=false` i `training_allowed=false`.
- Negatywne testy: rewizja po snapshotie blokuje wynik, zatwierdzone dwie mapy dostawców nie dublują meczu, REVIEW/PENDING nie przepuszcza xG, provider mismatch blokuje xG. Dodatkowo testy deterministycznego pobierania małej próbki xG.
- **Rzeczywisty audyt xG**: [GitHub Actions #40291895443](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40291895443) — SUCCESS, **12/12** wybranych meczów Premier League 2023/24 i 2024/25 ma kompletne strzałowe xG obu drużyn. **8/12** dopasowano dokładnie po nazwach, dacie i wyniku do API-Football, **4/12** pozostają niezatwierdzone; brak autopromocji aliasów. Wykorzystano **15** zapytań PitchAPI i **2** API-Football; nie kupowano usług.
- **Bardzo ważne**: 12/12 oznacza wyłącznie jakość małej próbki odczytanej teraz. Nie dowodzi kompletności xG dla 760/8907 spotkań ani istnienia historycznych snapshotów przedmeczowych. **0/12** ma udowodniony pierwotny czas dostępności danych przed prognozą późniejszego meczu; xG nie zostały jeszcze zaimportowane do trwałej bazy i nie ma zgody na trening.
- Zadania CI publikują wyłącznie **zliczenia, metadane i hashe**, nigdy surowe xG, dane spotkań ani klucze. Nowy audyt PitchAPI uruchomiono jednorazowo przez push, bez kalendarza, automatycznej cotygodniowej aktywacji czy nowego abonamentu.
- **GATE11 nadal PENDING (10/29).** Otwarte: dowód treści rekordów historycznych w konkretnym czasie, wiarygodny pierwotny `published_at` dla xG, pełne pokrycie i trwały szyfrowany backup rozszerzonej bazy. Starsze modele bez zmian.

## 26.10.2026 — faktyczny trwały backup 760 meczów i test odzyskania z Google Drive

- **WYKONANE:** [Actions #40293935946](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40293935946) SUCCESS: utworzono realny, dwusezonowy zbiór 760 spotkań, zaszyfrowano nowym `KB3ENC2` RSA-OAEP+AES-256-GCM, przetestowano 6 przypadków pozytywnych/negatywnych odtwarzania, do artefaktu CI trafił tylko szyfrogram i zbiorczy manifest.
- **WYKONANE:** kopię ZIP 57 824 B zapisano trwale w prywatnym [folderze Google Drive](https://drive.google.com/file/d/1lA1Z2qNSWyGxn_6OcyFl3ZmK147BWsn-/view?usp=drivesdk); pobrano ponownie z Drive i niezależnie odszyfrowano kluczem prywatnym spoza GitHub/Drive. SHA-256 zgodny, SQLite integrity=ok, foreign_key_check=0, 760 meczów i 760 zatwierdzonych mapowań, 2023/24=380, 2024/25=380.
- **DOWÓD:** [protokół offsite](STEP_11_OFFSITE_ARCHIVE.md) oraz [zapisane SHA i liczby](../data/audits/STEP11_760_OFFSITE_RESTORE_2026-10-26.json). Oryginalna kopia 380 meczów z GATE09 pozostaje bez zmian. Nowy klucz prywatny właściciel musi zachować w bezpiecznym miejscu; fakt jego pobrania przez właściciela wymaga potwierdzenia.
- **Nie usunięto blokad chronologicznych:** wszystkie 760 meczów oznaczono RETROSPECTIVE; brak potwierdzenia historycznych payloadów i momentu ich udostępnienia, xG historycznie niecertyfikowane. Wciąż **GATE11 PENDING / 10/29, training_allowed=false**.

## 26.10.2026 — pierwszy trwały rejestr faktycznie zaobserwowanych danych (GATE11 PENDING)

- [Rzeczywisty PIT capture #40296430026](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40296430026): Premier League 2026/27, **380** rekordów, w tym **80** zakończonych i **300** jeszcze przed kickoff; czas odczytu **09:01:48.745533–09:01:49.018457 UTC**. Oddzielny hash SHA-256 każdego rekordu, pełna kanoniczna odpowiedź źródła i hash-chain obejmujący całą sesję; dopuszczalne tylko nowe `NETWORK_OBSERVED`, bez cofania czasu.
- [Zaszyfrowany i ponownie odczytany ZIP z Drive](https://drive.google.com/file/d/1wvFMLiSQHUP06-r95iNwp9nyBfYbsBoP/view?usp=drivesdk) zawiera dane obserwacji `KB3PIT1`; porównano SHA-256 ZIP i szyfrogramu, odszyfrowano wcześniej przekazanym właścicielowi kluczem RSA; sprawdzono SQLite integrity=ok, 380/380 hashy, zero błędów FK. Klucz prywatny nigdzie nie został dołączony.
- **82/82 testów offline PASS** (43 Step11 + 39 wcześniejszych) — [CI #40296978637](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40296978637). Są testy anty-backdate, niezmienności, cofnięcia/corrected FT, braku historii syntetycznej, SHA oraz przywrócenia. Nowy workflow zbiera przyszłe snapshoty wyłącznie po `workflow_dispatch`: PR/push uruchamiają **same testy**, bez dodatkowych odpłatnych zapytań do API.
- [Protokół obserwacji](STEP_11_PIT_OBSERVATION.md) i [manifest prawdziwych dowodów](../data/audits/STEP11_PIT_LIVE_CAPTURE_2026-10-26.json). Dane z 2023/24–2024/25 nadal RETROSPECTIVE, nie uzyskano historycznych timestampów ich oryginalnej publikacji. 380 bieżących rekordów to dowód tego, co zaobserwowano od dzisiaj, **nie historyczny PIT dla poprzednich sezonów**. Brak dopuszczenia do ML, `training_allowed=false`, GATE11 w realizacji, 10/29.

## 26.10.2026 — druga realna obserwacja PL i pierwszy zaszyfrowany zapis xG

- Pierwszy PIT [Actions #40296430026](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40296430026), drugi [Actions #40298805124](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40298805124), odpowiednio **09:01:49** i **09:20:47 UTC**. Pobrano obie odrębne kopie z Google Drive, odszyfrowano i porównano 380/380 meczów na poziomie rekordów i SHA. **0 zmian statusu, wyniku lub kickoff** w tej krótkiej próbie. To nie dowodzi poprawnego działania na rzeczywistej zmianie podczas kolejki, wymaga kolejnego snapshotu w innym dniu.
- Próba PitchAPI: **5 zapytań API**, 3 zakończone mecze, **3/3 kompletne strzałowe xG**, ale **0/3** przeszło ścisłe połączenie źródeł; **2 AMBIGUOUS_OR_UNMATCHED, 1 ALIAS_CANDIDATE_UNVERIFIED**. xG pozostają zaszyfrowane w dzienniku, jawnie w kwarantannie, **nie przypisano** ich do kanonicznych fixture. Brak fałszywych zer, źródłowe daty publikacji nieudokumentowane.
- [Drugi zaszyfrowany ZIP na Drive](https://drive.google.com/file/d/1yOQUgJeccTYWwPRMBSIqZijY1DtGS-4D/view?usp=drivesdk) został pobrany ponownie, zbadano hashe, integralność SQLite i odtworzenie kluczem właściciela. [Manifest audytu](../data/audits/STEP11_TWO_PIT_XG_2026-10-26.json). Testy offline [#40298663945](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40298663945): **91/91 PASS (52 Step11 + 39 wcześniejszych)**.
- [Protokół](STEP_11_TWO_PIT_XG.md). Historyczne 2023–2025 nadal RETROSPECTIVE, `training_allowed=false`, **GATE11 PENDING, 10/29**. Brak cyklicznych zapytań API i nowych opłat.

## 26.10.2026 — odtworzenie źródła i dokładnie 3 powiązania xG z przeglądem identyfikatorów

- [Rzeczywiste zarchiwizowane źródło #40301238526](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40301238526): 380 rekordów API-Football, 3/3 kompletne feedy PitchAPI, ale początkowo nadal kwarantanna (2 × NAME_DISAGREEMENT_OR_AMBIGUITY, 1 × ALIAS_REVIEW_REQUIRED). Kluczowym brakiem wcześniejszej wersji była utrata metadanych identyfikacyjnych PitchAPI — od nowego pobrania są zachowywane w szyfrowanym `raw_json` wraz z oryginalnymi fixture-kandydatami API-Football.
- Po sprawdzeniu pełnego źródła (czas UTC, FT, 90' gole, oryginalne team ID u obu dostawców, metadane nazw i SHA obserwacji) utworzono **wyłącznie trzy mapowania przypięte do konkretnych meczów**: Sunderland–Leeds, Liverpool–Brighton, Crystal Palace–Newcastle. Ogólne aliasy wyłączone. `src/kb3_reviewed_xg.py` przelicza dopasowanie bez zmiany pierwotnego statusu kwarantanny.
- Kod z GitHub [#40302357607](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40302357607) uruchomiono na rzeczywistym odszyfrowanym pliku po pobraniu z Google Drive: **3/3 bezpieczne odrębne powiązania PASS**, własny mecz i cutoff przed obserwacją odrzucone. 0 wierszy oryginalnego źródła zmieniono. [Protokół](STEP_11_XG_IDENTITY_REVIEW.md), [manifest bez surowych xG](../data/audits/STEP11_XG_MATCHBOUND_REVIEW_2026-10-26.json).
- [CI #40302235918](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40302235918) **111/111 testów PASS** (72 Step11, 39 regresja). Nie ma jeszcze automatycznego pokrycia całej ligi ani integracji z głównym builderem cech; historyczny pierwotny czas publikacji nadal NULL. **GATE11 PENDING, 10/29, training_allowed=false**.

## 26.10.2026 — wspólny silnik ELO/formy z rzeczywistymi observed-at wynikami i reviewed xG

- `src/kb3_features.py` v0.4 i `src/kb3_observed_features.py`: historyczne obserwacje API-Football z archiwum są weryfikowane w chwili `cutoff`, a następnie trafiają do TEGO SAMEGO kalkulatora ELO, formy 5/10/15, dom/wyjazd oraz xG/xGA. `replay` i dotychczasowy `verified` zachowano; nowy status `OBSERVED_AT_NOT_CERTIFIED` nie jest certyfikacją daty pierwotnej publikacji dostawcy.
- Dla 3 reviewed-xG obowiązuje nie tylko obserwacja strzałów po meczu, lecz także niezależna granica czasowa **2026-10-26T09:53:09Z** — udokumentowany merge [GitHub commit 1f6032d](https://github.com/karolbarankiewicz1984-ui/kb-score-3/commit/1f6032d4562d457e9bcb92381bf28a6cfa56a120). Przed tą chwilą reviewed xG nie jest cechą. Fałszywy commit, wcześniejsza data lub niezgodny hash źródła blokują dopuszczenie statystyki.
- [CI #40306542175](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40306542175) **125/125 PASS**: 86 testów Step11 i 39 regresyjnych. Weryfikacja nie wywołuje dostawców ani płatnego API.
- **Nie tylko test syntetyczny:** finalny kod pobrany z [GitHub Actions #40306671705](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40306671705) przetestowano lokalnie na autentycznym, niezależnie pobranym z Google Drive i odszyfrowanym archiwum PIT 2026/27 (380 hashy, integralność SQLite ok, źródło nietknięte). Dla przyszłego Bournemouth–Leeds (fixture 1557448) i cutoff `2026-10-26T10:01Z`: **80** zaakceptowanych przeszłych wyników, **1** obserwacja xG Leeds w oknie 5 (Bournemouth **0**). Przy cutoff `09:45Z` xG **0**, również **0** bez zatwierdzonego crosswalk; uszkodzony hash archiwum powoduje odmowę. [Protokół](STEP_11_OBSERVED_FEATURES.md), [sanity audit SHA](../data/audits/STEP11_OBSERVED_BUILDER_REAL_DRIVE_2026-10-26.json).
- **GATE11 PENDING (10/29)**: potwierdzenie pojedynczego testu obsługi historii i zaledwie 3 xG nie uprawnia do historycznego backtestu z sezonów 2023–2025, trenowania, produkcyjnych typów ani przejścia do kroku 12. Klucze i surowe xG nie opuszczają prywatnego magazynu.

## 26.10.2026 — 10 nowych obserwacji PitchAPI: 5 strict / 5 kwarantanna; dwa niezależne archiwa PIT do formy i ELO

- [Rzeczywisty sezonowy audyt #40308346204](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40308346204): **10/10** kompletnych feedów xG z **10 różnych dat** PL 2026/27, bez ponawiania poprzednich 3. 12 zapytań PitchAPI i 1 API-Football, 0 błędów. **5** dokładnych ID+UTC+FT+wynik+obie nazwy; **4** aliasy REVIEW i **1** mismatch wymagający przeglądu. 5 niezweryfikowanych pozostało w kwarantannie. To próba audytowa, nie dowód kompletności całego sezonu.
- [Nowe zaszyfrowane archiwum ZIP na Google Drive](https://drive.google.com/file/d/1l0Ng06QDIqM1h8IUH9m3Z8aER4f_COdC/view?usp=drivesdk), 85 496 B, ponownie pobrane i odszyfrowane oddzielnym kluczem poza Githubem. SHA ZIP i szyfrogramu zgodne, SQLite integrity=ok, FK=0, 380 rekordów API-Football, **10/10** prawidłowych xG oraz zachowane daty rzeczywistego odczytu 26.10.2026.
- `src/kb3_external_xg_asof.py`: źródło **strict** z odrębnego backupu można teraz warunkowo doprowadzić do `kb3_observed_features.py`, wyłącznie przy zgodności hasha źródła obu archiwów i cutoff nie wcześniejszym niż pobranie xG. Nie wolno łączyć niezależnych hash-chain jako jednego fałszywego łańcucha. [Lokalny test na prawdziwych obu archiwach](STEP_11_XG10_STRATIFIED.md): przyszły fixture 1557452, **80** wcześniejszych wyników, **1** nowe xG w oknie formy, **0** przed czasem drugiego capture i bez drugiej bazy.
- [CI #40309316442](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40309316442): **140/140 PASS** (101 Step11 + 39 regresja). [Szczegółowy raport](STEP_11_XG10_STRATIFIED.md), [manifest SHA](../data/audits/STEP11_XG10_STRATIFIED_REAL_2026-10-26.json). Wszystkie źródła nadal OBSERVED_AT_NOT_CERTIFIED, publikacja dostawcy nieznana, historyczny PIT dla 2023–2025 nadal 0. **GATE11 PENDING, 10/29**, bez treningu i nowych zakupów.

## 26.10.2026 — decyzja: jeden dostawca sportowy zamiast niejednoznacznych mapowań API-Football↔PitchAPI

- Przyjęto **PitchAPI jako preferowanego kandydata na jedyne źródło terminarzy, wyników, zespołów, xG i dostępnych fauli/kartek dla NOWEGO przepływu KB Score 3.0**. Stary API-Football pozostaje w archiwach historycznych tylko do odczytu. 5 niepewnych starych crosswalk **nie jest automatycznie dopuszczonych**, lecz nowa architektura w ogóle ich nie potrzebuje. Tryb wdrożenia `SHADOW_ONLY_NOT_PRODUCTION`, decyzja o migracji później.
- [RZECZYWISTY PITCHAPI-ONLY #40312167476](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40312167476) **SUCCESS**: PL 2023/24 **380**, 2024/25 **380**, 2026/27 **380** (80 FT, 300 przyszłych), 5/5 zakończonych meczów z kompletnymi xG, wspólne natywne `m_ID`, 9 zapytań PitchAPI i **0** API-Football.
- [RZECZYWISTY UEFA/Faule #40312704445](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40312704445) **SUCCESS**: LE 2026/27 **144** widoczne mecze (54 zakończone / 90 przyszłych), LK **108** (36/72), w próbce PL potwierdzono `fouls`, `yellow_cards`, `red_cards`. 5 zapytań PitchAPI / 0 API-Football. Nie jest to jeszcze dowód kompletności xG i fauli na wszystkich spotkaniach UEFA.
- `src/kb3_pitch_native.py` i `src/kb3_pitch_native_features.py`: nowe izolowane `PitchAPI.match_id` jako klucz wyniku i statystyk, jeden kalkulator ELO/formy/xG, `shadow_native` oznaczone **NOT VERIFIED PIT**, bez trwałego zapisania raw payloadów i bez treningu. Nie modyfikowano dotychczasowych historycznych baz.
- [CI #40313071652](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40313071652) **160/160 PASS** (121 Step11 + 39 regresja).
- Pełna polityka i ograniczenia: [docs/STEP_11_SINGLE_PROVIDER_DECISION.md](STEP_11_SINGLE_PROVIDER_DECISION.md), [config/STEP11_PROVIDER_POLICY.json](../config/STEP11_PROVIDER_POLICY.json). `GATE11 PENDING`, **10/29**, `training_allowed=false`; następny krok: zaimplementować *trwały zaszyfrowany rejestr obserwacji PitchAPI* i historyczne cutoff oraz rozszerzyć sprawdzanie UEFA xG. Kursy bukmacherskie nie są potwierdzoną funkcją PitchAPI i, jeśli będą potrzebne, pozostają niezależną warstwą cenową.

## 26.10.2026 — nowy trwały natywny PitchAPI PIT

- [Realny odczyt #40315374235](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40315374235): **380** meczów PL 2026/27 (80 zakończonych, 300 przyszłych), **5/5** kompletnych xG; **7 PitchAPI, 0 API-Football**. Sześć sesji `NETWORK_OBSERVED` z prawdziwymi timestampami 11:29:09–11:29:10 UTC, **385** SHA rekordów, pełen niezmienny łańcuch SHA.
- [Zaszyfrowane archiwum na Google Drive](https://drive.google.com/file/d/18AeQOY7it5F58S4EqHKk8GDpqOD_TtUg/view) pobrano ponownie, odszyfrowano offline dotychczasowym kluczem właściciela, zweryfikowano **385/385 rekordów, 6/6 sesji, integrity=ok, FK=0**. SHA ZIP `1260442238b8b1b94bcc6d5d99ce7be5ea01ed51736df8289fefc85b4da7b5de`, bez przechowywania klucza prywatnego w GitHub.
- Nowy `kb3_pitch_native_ledger.py`, `kb3_pitch_native_archive.py`, `kb3_pitch_native_observed_features.py`: PitchAPI-only matches/shots, zabezpieczony czas odczytu, read-only ELO/form/xG as-of. [CI #40316210520](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40316210520) **175/175 PASS** (136 Step11 + 39 starszych).
- [Protokół](STEP_11_PITCH_NATIVE_PIT_ARCHIVE.md), [manifest](../data/audits/STEP11_PITCH_NATIVE_FIRST_OFFSITE_2026-10-26.json). **GATE11 PENDING, 10/29**, brak udowodnionej oryginalnej daty publikacji danych dostawcy, brak autoryzacji treningu oraz brak produkcyjnego przełączenia.

## 26.10.2026 — natywne xG UEFA: 12/12 kompletnych źródłowych próbek (LE/LK)

- [Rzeczywisty audyt #40318301119](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40318301119) **SUCCESS**: Liga Europy 2026/27: **6/6** kompletnych xG (z listy 144 meczów, 54 zakończonych; próba 4 daty). Liga Konferencji: **6/6** (z listy 108 meczów, 36 zakończonych; próba 2 daty). Natywne `PitchAPI.match_id` spina shot feed i mecze, zero API-Football, maksymalnie i faktycznie 15 wywołań PitchAPI. **12/12 próbek nie jest pełną weryfikacją sezonu**.
- **15 rzeczywistych źródłowych odpowiedzi** z hash-chain i timestampami hosta zaszyfrowano RSA-OAEP/AES-GCM. [Prywatna kopia Google Drive](https://drive.google.com/file/d/1LdmMRLmtaObUK7gs9r55D6950jTMCwxF/view). Ponownie pobrane ZIP i szyfrogram mają zgodne sumy SHA: ZIP `4401fa6be34bad08ddf3729f563506b231851ef45554d0389b524ea34ce30ac4`, ciphertext `fc49dc39502a2c73a8883d0732797a284075845bac9161f183bf9a496d4c6b16`, hash-chain `aef1c98c5dfc6cecb60ab810a13b5ed5ca82fd956b79fb4ad5c33b0b2b9ccc06`. **Odtworzenie prywatnym kluczem kopii Drive jeszcze nie wykonane** — oddzielny blocker, nie deklarować pełnego offsite-restore.
- `src/kb3_pitch_uefa_evidence.py`, `scripts/step11_uefa_native_xg_capture_once.py`, testy — brak autoaliasów, brak xG jako 0 przy niekompletnych feedach, szyfrowany pełny materiał dowodowy. [Regresja #40318219204](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40318219204) **187/187 PASS** (148 Step11 + 39 poprzednie).
- [Raport szczegółowy](STEP_11_UEFA_NATIVE_XG_COVERAGE.md), [manifest](../data/audits/STEP11_PITCH_UEFA_XG12_2026-10-26.json). Historyczne opublikowanie wyników przez dostawcę nieznane, pełne pokrycie UEFA niepotwierdzone, dalsze prawdziwe rewizje wymagają czasu. **GATE11 PENDING, 10/29, training_allowed=false**.

## 26.10.2026 — niezależny restore UEFA 15/15 PASS, gotowe porównywanie przyszłych rewizji PitchAPI

- PONOWNIE pobrana wcześniej zaszyfrowana [kopia UEFA z Google Drive](https://drive.google.com/file/d/1LdmMRLmtaObUK7gs9r55D6950jTMCwxF/view) została **rzeczywiście odszyfrowana poza GitHubem** dotychczasowym kluczem właściciela. Odcisk klucza RSA, odczyt klucza sesji OAEP, autentyczność AES-256-GCM, SHA nieskompresowanych 364970 B, **15/15** oryginalnych odpowiedzi i cały łańcuch SHA — **PASS**. Klucz ani jawne źródło nie zostały opublikowane.
- `src/kb3_pitch_native_drift.py`: odrębne potwierdzone archiwa pełnego terminarza 380 meczów mogą być porównane po natywnych `PitchAPI.match_id` (zmiana terminu, wyniku, statusu, nazwy). Zmiana kanonicznych `team_id`, skład 380 meczów i błędny source hash wymagają odmowy. Wynik agregatowy nie ujawnia nazw/ID klubów.
- [CI #40320084066](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40320084066) **199/199 PASS** (160 Step11 + 39 regresja); dodatkowe **12 testów dryfu**, w tym reschedule, wynik zmieniony po meczu, FT, alias wyłącznie tekstowy, manipulacja ID i brak wyniku nie równy zero.
- **Drugi autentyczny, natywny snapshot PitchAPI nie został jeszcze wykonany** w tym torze; brak podstaw do stwierdzenia „0 zmian” ani do porównania między różnymi datami. Uruchomienie ponownego ograniczonego pobrania w tym kroku nie powiodło się na etapie tworzenia workflow; NIE zastępowano go datami syntetycznymi. [Raport i manifest](STEP_11_UEFA_NATIVE_XG_COVERAGE.md), [SHA evidence](../data/audits/STEP11_PITCH_UEFA_XG12_2026-10-26.json).
- **GATE11 nadal PENDING, 10/29**. Rygor PIT historycznych lat 2023–2025 nadal niepotwierdzony. `training_allowed=false`.

## 26.10.2026 — drugi autentyczny natywny PitchAPI PIT, osobne zaszyfrowane backupy, pełny realny diff

- [Run #40321588543](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40321588543) **SUCCESS**: drugie realne pobranie PL 2026/27 o `12:19:16.338115Z`, 380 meczów, 5/5 kompletnych xG; 7 PitchAPI i 0 API-Football. Pierwsza obserwacja `11:29:09.681040Z` — rzeczywisty odstęp **50,11 min**, bez pozorowania innej daty.
- [Nowy zaszyfrowany backup w Google Drive](https://drive.google.com/file/d/1X27ol04hWczbRCKin_pcKeiyVcLeF_x7/view) pobrano ponownie i rzeczywiście odszyfrowano poza GitHubem istniejącym kluczem prywatnym. SHA ZIP `7849b3dcebaa7b906f6a36df9584e8043d028cd20d7c2a1b8d77d136d4b09163`, SHA szyfrogramu `3355a181d82f2d5f5ad1c474962fedaca6d8f314c1dccd315b3e62ecd4e3ce80`. Obydwa archiwa: SQL integrity=ok, FK=0, po **385/385** rekordów i pełne odrębne **6/6 hash-chain**.
- Bezpieczny realny diff po natywnym match ID: **0/380** zmian pełnych źródłowych rekordów meczowych, 0 godzin, 0 wyników, 0 statusów, 0 nazw i 0 podmian team ID; **5/5** powtórzonych shot-feeds również bez zmian. Dwa source payload SHA są identyczne `3f68e047863fe6e4c2ffef3b84013fbe121a19b2054503ffa766520c072fc2da`.
- [Raport techniczny](STEP_11_NATIVE_SECOND_REAL_CAPTURE.md), [bezpieczny manifest](../data/audits/STEP11_PITCH_NATIVE_TWO_REAL_CAPTURES_20261026.json). Usunięto poprzedni blocker „brak drugiego rzeczywistego native snapshotu”, ale **wielodniowy test nadal PENDING**. Nie znamy pierwotnej daty opublikowania źródłowych danych przez dostawcę; `GATE11 PENDING, 10/29`, `training_allowed=false`.

## 26.10.2026 — mapa dostępności każdej cechy i kontrola no-lookahead

- Wspólny `kb3_features.py` otrzymał wersję wyjścia **v0.5**, a `src/kb3_step11_field_audit.py` w trybie `observed` wykonuje walidację **każdego** rezultatu i jego xG jeszcze przed ELO oraz wystawia `feature_availability` dla **wszystkich wartości i missing_flags**. Wpis zawiera najpóźniejszy wymagany timestamp źródła, typ, liczbę historycznych meczów, hash zestawu źródłowych fixture oraz znacznik `published_at=NULL`. Dla xG bierze pod uwagę faktyczny moment pobrania strzałów i ewentualny późniejszy moment zatwierdzenia review. Odrzuca rezultat dopisany po cutoff, xG po cutoff, błędne liczby, fałszywe dane własnego meczu i niejednoznaczne zegary źródła.
- [Pełna regresja #40325431132](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40325431132) **217/217 PASS** (178 Step11 +39 dawnych), w tym 11 nowych testów i starsze testy obu architektur observed. Żadne nowe zapytania PitchAPI / API-Football ani training.
- [Szczegółowy katalog i tabela warunków GATE11](STEP_11_FIELD_PROVENANCE_GATE.md). Zidentyfikowano dodatkowe jawne ograniczenie: native PitchAPI builder na dziś obsługuje sezon **2026/27**, ale **nie importuje do ELO wcześniejszych sezonów 2023–2025**. Kolumna `prior_seasons_games_available` jest w tej ścieżce zerowa i nie może udawać wielosezonowej wiedzy. Przejście do kroku 12 nadal zablokowane przez GATE11: prawdziwy kolejny dzień obserwacji, ocena pokrycia i walidacja pełnego PIT; **10/29 zaliczone**.

## 26.10.2026 — brak automatycznego wydawania zapytań na przestarzałe piloty API-Football

- Ustalony jeden preferowany dostawca sportowy to PitchAPI, natomiast starszy CI `kb3-step11-features.yml` uruchamiał dwa historyczne importy API-Football na każdym push do `main`. W ramach kontroli kosztu i zgodności architektury pozostawiono te joby tylko dla **ręcznego `workflow_dispatch`**, nie dla push/PR. Nie zmieniono zachowania istniejących archiwów.
- [CI #40326752798](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40326752798) **220/220 PASS (181 Step11 + 39 starszych)**, oba network piloci `SKIPPED`, 3 nowe testy kontraktu workflow. Wciąż `GATE11 PENDING` (10/29).

## 26.10.2026 — KONIEC OGRANICZENIA ELO JEDNEGO SEZONU: 3+1 prawdziwych sezonów PitchAPI

- [Rzeczywisty import PitchAPI #40329303189](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40329303189): PL 2023/24, 2024/25 i 2025/26, **380/380 FT każdy**, 1140 unikatowych native match IDs, po 20 drużyn i **17 wspólnych natywnych team IDs** w przejściach 2023→2024 oraz 2024→2025. Dokładnie 4 wywołania PitchAPI, **zero API-Football**, bez nowego abonamentu.
- [Zaszyfrowana kopia w Google Drive](https://drive.google.com/file/d/1_wLVJtOSwjwQwHhjBa54-3f0-aCzhyqJ/view) została ponownie pobrana i niezależnie odszyfrowana kluczem właściciela poza GitHub, RSA/AES, **4/4** SHA-chain, **1140/1140** źródłowych wyników PASS, brak jawnego surowego payloadu lub klucza w repo. SHA ZIP `301bae69251d19a0192e12c2c033636b3f2822a15dcea2c4beaca28f4b45de2e`, ciphertext `e5e14a2320e65f945a2709c4cd8dfb49ed38d45ccca3502b3e5ba7c21f84d343`.
- `src/kb3_pitch_multiseason_history.py` i rozszerzenie `src/kb3_pitch_native_observed_features.py`: 3 historyczne sezony zostają dołączone tylko przy autentycznej obserwacji źródła **przed cutoff** oraz ciągłych ID, bez zmyślonego xG. Dane z sezonów wcześniejszych pobrane DZISIAJ **nie są historycznym PIT** z lat 2023–2025. Historyczne `xg=null`, `training_allowed=false`, Elo K=20/Home=65/retention=.85 prowizoryczne.
- Dokładny kod źródłowy uruchomiono lokalnie na niezależnie odszyfrowanych DWÓCH archiwach PitchAPI przy cutoff 26.10.2026 13:19Z i przyszłym kickoff 31.10: **1140 historii+80 wyniki obecnego sezonu = 1220, 114 poprzednich spotkań każdej z drużyn, 121 cech, 159 znaczników czasu, wszystkie as-of <= cutoff, SHA pełnego wyniku `38107759ad916fdc7cb581080067327ae6890a2e7cca423e628767392ab7070d`**. [Raport](STEP_11_PITCH_MULTISEASON_ELO.md), [manifest](../data/audits/STEP11_PITCH_MULTISEASON_ELO_REAL_2026-10-26.json).
- [231/231 offline CI PASS #40330403055](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40330403055): 192 Step11 +39 regresji, starszy automatyczny network pilot API-Football SKIPPED; brak treningu, prognoz czy innych zakupów. **GATE11 PENDING, 10/29.**

## 26.10.2026 — większa próbka xG jednego dostawcy: 30/30 + offsite odtworzony

- [Rzeczywisty audyt PitchAPI #40334387182](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40334387182): pełne listy 380 Premier League, 144 Liga Europy, 108 Liga Konferencji; uprawnione zakończone odpowiednio 80/54/36; **po 10 strzałowych xG COMPLETE z każdej ligi = 30/30**. Rozkład dat próby odpowiednio **10/4/2** (Liga Konferencji realnie ma tylko dwie daty w tym etapie). Dokładnie 34 wywołania PitchAPI w archiwizowanym runie, 0 API-Football.
- **34 realne źródłowe sesje, RSA-OAEP/AES-GCM** zapisane w [prywatnym Drive](https://drive.google.com/file/d/1ddByW04Sw3bDLxq-h2P-HyvwRtuBI423/view). Archiwum pobrane ponownie, odszyfrowane poza GitHub, SHA ZIP/cipher/plaintext, 34/34 łańcuchowych hashy, 30/30 natywnych source match/team IDs PASS. SHA ZIP `95db06fdca31c23c67a3625208d2675a3a882bb86b4dd29ca11f97fccb2d5906`.
- Porównując autentyczne natywne `match_id` ze starszym odtworzonym archiwum UEFA, znaleziono po **2 powtórzone mecze** w LE i LK. Razem **14 unikalnych meczów LE +14 LK +10 nowych PL =38 unikalnych meczów o kompletnych xG**. Dobór czasu nie jest losowy i **nie** dowodzi kompletności 100% meczów czy certyfikacji historycznego PIT.
- W **pierwszym** realnym przebiegu #40334130610 pobrano 34 źródła, ale końcowy warunek błędnie żądał trzech dat w Lidze Konferencji; runner nie zachował archiwum mimo 30/30 xG. Drugi odczyt (kolejne 34 wywołania) naprawił sprawdzanie na minimum dwie daty, a upload zaszyfrowanych źródeł następuje teraz **`if: always()`**. **Łączny faktyczny koszt 68 wywołań PitchAPI w obu przebiegach**; bez nowego abonamentu.
- [Pełny audyt, ograniczenia i dowody](STEP_11_THREE_LEAGUES_XG30_COVERAGE.md) / [manifest](../data/audits/STEP11_THREE_LEAGUES_XG30_OFFSITE_2026-10-26.json). Testy po dodaniu dwóch zabezpieczeń workflow: **241/241** w pełnej regresji (202 Step11 +39 poprzednich). **GATE11 nadal PENDING (10/29)**; cross-day obserwacja nie istnieje jeszcze, brak treningu i przełączania produkcji.
