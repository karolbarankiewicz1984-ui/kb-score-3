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
