# CODEX-01 — audyt aktualnego main i ograniczone poprawki źródeł

**Wynik: PARTIAL wykonania / NO-GO dla pełnego wdrożenia R1–R5.**
Gałąź: `fix/codex-r1-r5-audit-20261103`. Baza: `eabab06139b185d34450d314989783bdc980b088`.
Nie scalono do main, nie uruchomiono dostawcy, backfillu ani rzeczywistego fitu.
Formalnie nadal 15/29; GATE16/GATE17 PENDING.

## Pochodzenie i brakujące materiały

Przeczytano PLAN, ZMIANY, rejestr czterech zleceń, issue #120/#121 z historią
A0/R1/R2/R3/R4/R5/R6 oraz stan i dokumenty draft PR #124. #124 ma head
`8631523db62a2a27770108c57dc15cb1f74a688d`; nie zawiera pełnego kodu R1–R5.

W udostępnionym runtime, katalogach Library/shared/scratch, repozytorium i
połączonym Drive nie odnaleziono dwóch oryginalnych ZIP-ów. Dokładny zdalny ref
`fix/p1-features-calibration-sqlite` nie istnieje. Lokalny obiekt
`1b35907b9242ea15a3070c93af352b92a274231d` nie jest dostępny w checkout.
To stwierdzenie o dostępności w tej sesji, nie o usunięciu archiwów właściciela.
Nie odtworzono 57 plików, patcha R5 ani historycznych suite z opisów.

Odzyskano **wyłącznie dwa autentyczne pliki z #124**, bez modyfikacji ich bajtów:

| Plik | Git blob | SHA256 |
|---|---|---|
| `migrations/005_m0_publication_proofs.sql` | `5a76fe16eca67efc0f660c0f9dfe8de9089211f5` | `f2651a60305aa81c251bf78b647a5addc964d7bbe87d07004440ca9916b278b5` |
| `tests/test_codex_migration_offline.py` | `757012393de3a5c5c20ceb182a646ca9ac86189d` | `adc6544c05dbd9e2e02baddf05fb70149f3d72a954b8e8e54e54323fbdb7293b` |

Pozostały kod i testy tego PR są **niezależnymi poprawkami obecnego main**,
a nie rzekomo odzyskaną paczką Codex.

## Macierz ustaleń

| Ustalenie | Weryfikacja obecnego main | Działanie / status |
|---|---|---|
| FIND-01 / total_shots | Potwierdzony: Step17/backfill sprawdzały xG, ale nie niezależną liczbę strzałów | Nowy walidator pary: dokładnie jeden licznik `All.total_shots` obu stron; NULL, zły typ, duplikat i niezgodność blokują |
| FIND-02 / shots + stats | Potwierdzony: native ledger nie przechowywał stats; Step17 ufał metadanym receipt bez powiązania z payloadem | Atomowy sidecar native, zakotwiczenie w chain SHA, weryfikacja asof, osobne zegary, ponowna kontrola przed zapisem Step17; patrz ograniczenia legacy poniżej |
| P1-05 / kompletność | Potwierdzone: sam niepusty feed lub pojedyncza połowa wystarczały w starszej ścieżce | Nowe pobrania wymagają pełnego okresu, unikalnych niepustych ID strzałów, natywnych stron, niezależnych xG i liczników |
| P1-01 / TRAIN vs forward | **Nadal potwierdzony i otwarty** | TRAIN używa kickoff i 48h; forward cutoff i 3h. Nie zmieniono zamrożonego M0 ani wejść starego CatBoost w ciemno |
| P1-02 / starsza kalibracja | **Nadal potwierdzony i otwarty** | 100 niepoświadczonych syntetycznych rekordów dociera do granicy fit. Fit przechwycono przed wykonaniem; zero zapisanych kandydatów. Sama migracja 005 nie integruje walidatora publikacji |
| P1-03 / SQLite writers | Częściowo wcześniej naprawiony: trzy workflow miały wspólną blokadę; daily nadal inną; rebase pozostał | Wspólna blokada jobów zapisujących bazę, bez blokowania niezależnych walidacji PR; usunięto rebase binarnej SQLite. Odrzucony push wymaga ręcznego odzyskania z artefaktu i ponowienia na najnowszej bazie |
| P1-04 / automatyczny trening | Potwierdzony: PR/push wykonywał fit z nazwami historycznych wyników | Osobny offline job; fit tylko workflow_dispatch + jawny input; unikalny RUN_ID/RUN_ATTEMPT w RUNNER_TEMP, artefakt zamiast zapisu do main |
| P2-01 / CLI no-op | **Już naprawiony** w main, historia commitu `20e1c62` | Istniejące testy CLI no-op i idempotencji PASS; nie wprowadzono ponownie starej poprawki |
| P2-02 / luki CI | Potwierdzone w wąskich filtrach starszych workflow | Pełny offline PR/main CI obejmuje src/scripts/tests/migrations/workflows, z blokadą sieci/fit/zapisu dowodów |
| P2-03 / brzeg siatki | Nadal 0.6 jest maksimum FIXED_GRID | Ograniczenie badawcze; bez rozszerzania siatki, nowego fitu i zmiany M0 |
| R6 / cutoff datetime | Dotyczy niedostępnej implementacji R5 | Nowa niezależna ścieżka używa strun UTC i testu asof; nie udaje przetestowania nieobecnego patcha R6 |

Późniejsze poprawki #137–#142 pozostają w bazie. Nie podmieniono selektora
ośmiu lig, overlay kartek, parametrów modeli ani dotychczasowych raportów.

## Zmiany integralności nowych źródeł

- Struktura stats odpowiada SDK PitchAPI 0.1.6: `match_id`, `home_team.id`,
  `away_team.id`, `periods[].period`, `groups[].items[].key/home/away`.
  Liczniki SDK są strunami całkowitymi; 0 jest wartością, NULL brakiem.
  Jest test z rzeczywistymi klasami dataclass SDK, bez wywołania sieci.
- Wymagane są oba natywne xG i oba liczniki. Zgodność samego xG w tolerancji
  0.15 nie wystarcza. Całkowicie pusty feed daje 0 tylko przy jawnych 0/0
  i 0/0 xG w niezależnych stats. Pusta strona z dodatnim xG jest odrzucona.
- Akceptowane są `All` albo dokładnie dwie rozpoznane połowy, bez mieszania
  agregatu i połówek. Nieznany okres, brak połowy, duplikat ID i obcy team
  blokują parę. Bez live nie potwierdzono wszystkich wariantów etykiet serwera.
- Receipts muszą odpowiadać dokładnym payloadom i SHA, mieć poprawny chain,
  pochodzenie, kolejność i osobne zegary. Oba pobrania są po kickoff+3h;
  pojedyncze pobranie <=180 s, para <=360 s, bez nakładania i przyszłego zegara.
- Native `record()` blokuje writer przed odczytem poprzedniego chain. Stats
  i shots zapisują się w tej samej transakcji. Błąd po INSERT shots wycofuje
  capture, record i sidecar. Aktywny cudzy transaction nie jest commitowany.
- `pitch_source_pairs` jest append-only. SHA stats i jego zegary są powiązane
  z oryginalnym chain capture. `verify()` i `shots_asof()` wykrywają podmianę,
  również gdy napastnik przeliczył sam digest sidecaru. As-of wymaga zakończenia
  **obu** pobrań. Starsze native shots bez pary pozostają w kwarantannie.
- Rzeczywisty kod starego native collectora przekazuje teraz oba źródła.
  Zachowano cap 7 requestów: 2 mecze × 2 źródła + katalog + sezon = 6.
  Test wywołuje collector z fałszywym SDK, szyfruje i odtwarza jego bazę.
- Step17 weryfikuje oryginalne payloady ponownie przed zatwierdzeniem batcha;
  FK jest sprawdzane przed commit. Backfill i recheck nie oznaczają nowej
  pary jako VERIFIED na podstawie samej zgodności sum xG.

## Rzeczywiście wykonane testy

| Kontrola | Wynik |
|---|---|
| Pełny bazowy main, Python 3.12.14 | 1180/1180 PASS; 0 errors/failures/skips |
| Pełny zmieniony checkout, Python 3.11.17 | **1218/1218 PASS**, 46.760 s; 0 errors/failures/skips |
| Pełny zmieniony checkout, Python 3.12.14 | **1218/1218 PASS**, 42.432 s; 0 errors/failures/skips |
| Nowe/odzyskane kontrole | 38 testów: 29 source-pair/native, 3 dodatkowe SQLite, 4 workflow, 2 odzyskane z #124 |
| Pięć negatywnych prób na bazowym main | Wszystkie błędnie zaakceptowane: brak stats, brak total_shots, zła liczba, jedna połowa, fałszywy SHA receipt |
| Te same pięć prób po poprawce | Wszystkie odrzucone |
| Bezpośredni moduł Step06 | 8/8 PASS, niezależnie od discover |
| SQLite 005 na kopii rzeczywistej bazy | 29 starych tabel i ich wiersze identyczne, +2 nowe tabele; FK/integrity, idempotentne DDL, rollback, UPDATE/DELETE immutability PASS |
| Dwa native writery i wymuszony błąd po pierwszym INSERT | Lock conflict, rollback i późniejsze prawidłowe ponowienie PASS |
| 73 dawne forecasty vs autentyczny commit 6813af6 | Wszystkie oryginalne kolumny 73/73 identyczne; bieżąca baza ma 91 prognoz |
| Parametry M0 / chronione pliki | SHA parametrów zgodne; git diff data/models/config pusty |
| Chronologia i antyprzeciekowe testy obecnego repo | PASS; audyt różnic kontraktu i starego fit ujawnia opisane otwarte blokery |

Runner `python scripts/test_codex_offline.py` uruchamia dostępne unittest,
odrzuca duplikaty ID i blokuje socket connect, CatBoost.fit oraz zapisy do
data/models/config. Ładowanie istniejącego CBM do testów jest dozwolone.
Nie uruchamia nowych treningów na rzeczywistych danych. Testy Poissona używają
istniejących, syntetycznych wektorów. Python 3.11 i 3.12 wykonują ten sam zbiór;
**1218 to liczba unikalnych testów, nie 2436**.

Zestawów **197/108** i autentycznych 9 testów R5 nie ma w dostępnym kodzie.
Nie uruchomiono ich pod tymi nazwami, nie zsumowano do 305 i nie uznano nowej
suite za dowód pełnego pokrycia nieobecnych testów. Nowe 29 testów źródła to
osobna regresja obecnej implementacji.

Pierwszy przebieg po zaostrzeniu parsera: 19 failures/22 errors (brak stats
w starych fixtures i konieczność rozdzielenia uwierzytelniania archiwum V1).
Po rozdzieleniu pozostała jedna nieuzupełniona fixture UEFA, następnie
1209 testów wykryło jedną starą asercję liczności statystyk. Dodatkowy test
immutability kopii ujawnił pomyłkę testu 9 vs 8 placeholders; poprawiono test.
Nie ukryto tych nieudanych przebiegów; końcowe wyniki powyżej są po korektach.

Oryginał bazy migracji SHA256:
`df39abd9daed3b43793a71bb58dc2c9eb548a69e2f84d4e397f671f0a42b7144`.
Digest wszystkich starych kolumn 73 forecastów:
`cf3e4c81615e424c7c1d10888adffc65112a8c57d78b3297e9c743b102413bf7`.
M0 param SHA256:
`55310f0e1dd3842e6d876069ef21b1380901b3a6cc6884cf6ec6ea351a5812d1`.

## Blokery i czynności przed wdrożeniem

1. Dostarczyć autentyczne ZIP-y R1–R5 z historią 197/108 + R5/R6. Zweryfikować
   SHA, zrobić rzeczywiste porównanie trójstronne, bez przywracania starego kodu
   nad poprawkami #137–#142. Ta praca nie jest pełnym importem R1–R5.
2. Rozwiązać P1-01 za pomocą jawnej, zgodnej definicji cech lub bezpiecznej
   blokady niezgodnego challengera, zachowując M0 V1 i ciągłość jego forecastów.
   Na tym samym syntetycznym źródle stwierdzono różnicę obu days_since oraz
   zaokrąglenia elo_home_minus_away; zgodne 85 nazw nie dowodzi zgodnej semantyki.
3. Zintegrować niezależny walidator publikacji ze starą kalibracją i członkostwem
   FIT100/HOLDOUT50. Migracja bez kodu nie rozwiązuje P1-02. Nie zmieniać
   istniejących kandydatów/parametrów i nie wykonywać teraz fitu.
4. Ukończyć wersjonowanie lub kwarantannę **pozostałych ścieżek legacy**.
   Cross-provider `kb3_xg_pit`/`kb3_reviewed_xg` zachowują oryginalną semantykę
   archiwum v2; nie są objęte nowym certyfikatem pary. Historyczne rekordy
   `VERIFIED` w `observed_native_xg`/`observations` nie zostały ponownie
   zweryfikowane; konsumenci wymagają osobnego sidecaru albo kwarantanny.
   Nie przepisywać ich oryginalnych wierszy. Nie utożsamiać PASS nowego intake
   z recertyfikacją dotychczasowej historii.
5. Ocenić świadomie skutki zaostrzenia: niepełne feedy będą dawały mniej xG;
   starsze collectory bez stats pozostają UNVERIFIED. Sprawdzić etykiety okresów
   i ewentualne powtórzenia total_shots na kontrolowanej próbce dostawcy dopiero
   po odrębnym ustaleniu zakresu. **W tej sesji 0 requestów PitchAPI/API-Football.**
6. Sprawdzić CI dokładnego PR SHA, koszty i triggery live przed merge.
   Nie dispatchować backfillu. Istniejące workflow live na push main wymagają
   świadomej oceny przed wdrożeniem. Błąd push SQLite odzyskiwać z artefaktu
   i ponowić na aktualnym main; bez rebase/force ani podmiany nowszej bazy.
7. Niezależny review i osobna decyzja właściciela. Nie awansować Championa,
   GATE16/17, nie otwierać TEST i nie traktować retrospective research jako
   oryginalnej cechy przedmeczowej. Chroniony TEST nie był użyty do fit/tuningu.

**Decyzja:** można przeglądać ograniczony diff, ale **nie kierować całego
wdrożenia R1–R5 do zatwierdzenia/merge**. Draft PR i raport nie są wdrożeniem.

## Kontrola PR i korekta blokady jobów

Utworzono [draft PR #143](https://github.com/karolbarankiewicz1984-ui/kb-score-3/pull/143),
pierwszy kodowy commit `332b06334a69b068e00ced33494f56312d995568`.
Automatyczne CI tego PR ujawniło, że wspólna blokada na poziomie całych workflow
anuluje oczekujące walidacje: [run 41719647942](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/41719647942)
ma CANCELLED. To rzeczywisty niezaliczony przebieg, nie błąd modelu ani ukryty PASS.
Przeniesiono blokadę na joby zapisujące SQLite; dla daily w trybie PR jest
oddzielna kolejka testowa. Cztery odpowiednie testy workflow po korekcie PASS.
Oczekujące joby writerów podlegają ograniczeniu pojedynczego pending job w
GitHub concurrency; zmiana nie tworzy trwałej kolejki zadań.

Ostateczne wyniki CI dokładnego HEAD i linki do runów są aktualizowane w opisie
PR po ich faktycznym zakończeniu. Nie dispatchowano live ani eksperymentu fit.
