# KB Score 3.0 — krok 11: prawdziwe wielosezonowe ELO z jednego PitchAPI

**Data: 26.10.2026.** Wynik częściowy: **historyczne ELO 3+1 sezonu PASS dla przyszłego cutoff, cały GATE11 PENDING (10/29).** Żadnego treningu, żadnych typów u bukmachera i żadnej migracji produkcyjnej.

## Zmiana

Wcześniejszy natywny kalkulator PitchAPI brał wyłącznie rozegrane mecze Premier League 2026/27. Z tego powodu każda drużyna wchodziła do ELO z domyślnego poziomu 1500 mimo istniejących wyników z poprzednich sezonów.

Od teraz `build_native_observed(..., historical_receipts=<cztery zweryfikowane wpisy PitchAPI>)` może wykorzystywać **trzy zakończone sezony (2023/24, 2024/25, 2025/26)**, a następnie dołączyć aktualny sezon 2026/27, zachowując:

- **tylko jednego dostawcę** i natywne `PitchAPI.match_id` oraz `PitchAPI.team_id`, bez API-Football i aliasów nazw;
- tylko faktycznie zakończone spotkania; walidator wymaga 380/380 zakończonych meczów w KAŻDYM roku i braku duplikatów native ID;
- **ciągłość identyfikatorów klubów**; przy podejrzanie małym przecięciu drużyn kolejnych sezonów odrzuca import zamiast po cichu resetować ELO;
- chronologię spotkań, jednoczesne aktualizacje ELO na tym samym kickoffie bez informacji z równoległych meczów i korektę między sezonami;
- osobne znacznikowanie `captured_at_utc` każdej historycznej listy, bez przypisywania im wcześniejszej niż faktyczna daty pobrania;
- **xG historyczne pozostaje `null`**, jeśli nie zostało pobrane i niezależnie zatwierdzone. Średnie xG używają wyłącznie faktycznie dostępnych obserwacji z natywnych źródeł.
- ten sam wspólny kalkulator formy 5/10/15, home/away, punktów, goli, ELO przeciwnika i flag braków wraz z mapą czasu dostępności każdej cechy.

**Parametry ELO nie były dobierane do wyników.** Wciąż są wyjściowo prowizoryczne: initial 1500; K 20; home advantage 65; scale 400; season retention 0.85, także za każdy opuszczony sezon. To nie są zinterpretowane prawdopodobieństwa typów.

## Rzeczywisty audyt PitchAPI — a nie symulacja

[Jednorazowe realne uruchomienie #40329303189](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40329303189), **SUCCESS** (4 wywołania PitchAPI: katalog i 3 sezony; zero API-Football, zero nowych zakupów).

| Sezon | Zakończone spotkania | Drużyny PitchAPI | Wspólne ID z poprzednim sezonem |
|---|---:|---:|---:|
| 2023/24 | 380 | 20 | — |
| 2024/25 | 380 | 20 | 17 |
| 2025/26 | 380 | 20 | 17 |
| 2026/27 | 80 w istniejącym autentycznym rejestrze | 20 | Ciągłość zweryfikowana na źródłowych danych |

Wyniki 1140 historycznych spotkań pobrano **26 października 2026 r. ok. 13:17:47 UTC**. To źródło jest **RETROSPECTIVE_OBSERVED_NOW**, a NIE oryginalny snapshot przedmeczowy z lat 2023–2026. Nie wolno stosować go do fikcyjnego backtestu przy cutoff w dawnych datach.

### Trwały szyfrowany backup i odtworzenie

[Kopia na Google Drive — trzy historyczne sezony PitchAPI](https://drive.google.com/file/d/1_wLVJtOSwjwQwHhjBa54-3f0-aCzhyqJ/view).

Archiwum ZIP (31 907 B) zawiera tylko zaszyfrowane źródła, manifest i agregat. Zostało **ponownie pobrane z Google Drive**, niezależnie odszyfrowane lokalnym kluczem właściciela (RSA-OAEP + AES-256-GCM), a hash każdego z **czterech** źródłowych zapisów i całego łańcucha zweryfikowano. Integralność **PASS**; klucz prywatny oraz jawne statystyki nie trafiły do GitHuba.

- ZIP SHA-256: `301bae69251d19a0192e12c2c033636b3f2822a15dcea2c4beaca28f4b45de2e`
- Szyfrogram SHA-256: `e5e14a2320e65f945a2709c4cd8dfb49ed38d45ccca3502b3e5ba7c21f84d343`
- Ostatni SHA łańcucha źródłowego: `33c750f2db89a0df5faeba9348652a451f33548959839ff7bb0ca49210c2b367`

Nie wystarcza zgodny ZIP: audyt samodzielnie sprawdził również po odszyfrowaniu **1140 kompletnych wyników**, 20 natywnych drużyn na sezon i 17 stabilnych drużyn między każdą parą poprzednich lat.

## Niezależne uruchomienie dokładnego kodu na rzeczywistych dwóch archiwach

Pobrano **wyłącznie kod źródłowy z PR**, nie surowe rekordy ani klucz prywatny. Następnie na odtworzonych kopiach Google Drive uruchomiono dokładny moduł `src/kb3_pitch_native_observed_features.py` dwukrotnie dla tego samego nadchodzącego spotkania Premier League. Trzeci sezon historyczny został połączony z bieżącą bazą obserwacji pobraną wcześniej tego dnia.

| Kontrola | Sam sezon 2026/27 | 2023/24–2026/27 |
|---|---:|---:|
| Wyniki dostępne przed cutoff | 80 | **1220** |
| Poprzednie sezony gospodarzy (liczba meczów) | 0 | **114** |
| Poprzednie sezony gości | 0 | **114** |
| ELO gospodarzy, ustawienia prowizoryczne | 1508.52765 | 1535.01106 |
| ELO gości, ustawienia prowizoryczne | 1480.35796 | 1553.50263 |

- Odczyt czasu `2026-10-26T13:19:00Z`, mecz docelowy dopiero `2026-10-31T12:30:00Z`.
- **121 pól liczbowych/nullable i 159 wpisów `feature_availability`** sprawdzono względem cutoff; nie znaleziono żadnego wpisu z godziny przyszłej.
- Wyliczone cechy przeszły samokontrolę SHA: `38107759ad916fdc7cb581080067327ae6890a2e7cca423e628767392ab7070d`.
- Wynik nie jest rekomendacją bukmacherską ani dopasowanym modelem predykcyjnym. Nie powstały prawdopodobieństwa czy kursy.
- Szyfrowane źródło aktualnego sezonu: [niezależnie odtworzona druga obserwacja](https://drive.google.com/file/d/13idXMzj3dIn_luUdVi7LbcxKROjeLeZ5/view).
- [Sanity manifest wyników bez ID drużyn i surowych strzałów](../data/audits/STEP11_PITCH_MULTISEASON_ELO_REAL_2026-10-26.json).

## Kod, testy i ograniczenia

- `src/kb3_pitch_multiseason_history.py` — wymaga trzech kompletnych sezonów, autentycznych zegarów odczytu i historii hash-chain; blokuje duplikaty meczów i brak spójności identyfikatorów.
- `src/kb3_pitch_native_observed_features.py` — opcjonalna, zgodna wstecz integracja wielosezonowa; bez przekazania `historical_receipts` zachowanie 2026/27 pozostaje identyczne.
- `scripts/step11_pitch_multiseason_capture_once.py` — jeden ograniczony odczyt, 4 wywołania PitchAPI, szyfrowany backup i tylko agregatowy log.
- `scripts/step11_pitch_multiseason_real_audit.py` — lokalna weryfikacja **dwóch zaszyfrowanych źródeł** przed połączeniem, z wymaganym SHA szyfrogramu i prywatnym kluczem tylko u właściciela; jawne SQLite wyłącznie w folderze tymczasowym; wynik bez nazw klubów i surowych danych. Domyślnie brak sieci/API i brak trenowania.
- `src/kb3_pitch_uefa_evidence.restore(include_receipts=True)` umożliwia otrzymanie rekordów w pamięci **tylko po pełnej weryfikacji AES-GCM, odcisku RSA, SHA i łańcucha**, na wyraźne żądanie lokalnego wywołującego; domyślne zachowanie pozostaje bez ujawniania źródeł.
- Testy `tests/test_step11_pitch_multiseason_elo.py`: pełna historia 1140, stabilne ID, wygaszanie ELO, brak xG jako `null`, zachowanie wariantu 1-sezonowego, deterministyczne sumy, blokada przyszłego cutoff i źle podpisanych, niepełnych lub przepisanych danych.
- [Pełna regresja #40330403055](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40330403055): **231/231 PASS** (192 Step11 +39 pozostałe), a starszy sieciowy import API-Football **SKIPPED**. Tylko osobne, pojedyncze uruchomienie PitchAPI wykonało 4 wywołania.

**GATE11 PENDING, formalnie 10/29 zaliczonych.** Wyniki historyczne pobrane dzisiaj mogą wzmacniać przyszłe obliczenia po cutoff ich odczytu, ale nie potwierdzają możliwości przeprowadzenia autentycznego backtestu z lat 2023–2025. Pozostaje prawdziwa obserwacja w kolejnym dniu, szersza kontrola kompletności xG i ostateczny odbiór chronologii w wielu dniach. **Trening nadal zablokowany.** Stare KB Score 2.1, API Market oraz MultiModel niezmienione.
