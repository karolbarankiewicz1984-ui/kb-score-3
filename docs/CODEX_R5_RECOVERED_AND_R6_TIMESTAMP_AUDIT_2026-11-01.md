# Codex R5 — realne odzyskanie obu paczek, audyt i nowy błąd cutoff (01.11.2026)

**Status: SOURCE_RECOVERED / 40_PARTIAL_OFFLINE_PASS_AFTER_LOCAL_R6 / MERGE_NO_GO.** Ten dokument dotyczy izolowanego [DRAFT PR #124](https://github.com/karolbarankiewicz1984-ui/kb-score-3/pull/124); **źródła R1–R5 nie są jeszcze zastosowane do zdalnego kodu**. Poniższe testy wykonano poza `main`, na rozpakowanej częściowej paczce.

## Odzyskane oryginalne źródła

Biblioteka plików właściciela zawiera **oba rzeczywiste archiwa, nie tylko ich opisy**:

- `KB_SCORE_3_CODEX_REVIEW.zip`: SHA256 `22964c177db029b912b5f47b8a8b66d0998d722c772335434eb81e537d1c88c2`, 71 entry ZIP, CRC OK, **70/70** `SHA256SUMS` OK; częściowy zestaw 57 zmodyfikowanych plików Codex względem bazy `6813af619dbe620d321f233e73d2d107d34f8004`.
- `KB_SCORE_3_CODEX_R5_011_012_REVIEW_2026-10-30.zip`: SHA256 `d06446dd9f31ab056f2d45fc17bfaa701e1e38904ecb1aee55517002b7063a07`, 69 entry ZIP, CRC OK, **68/68** `SHA256SUMS_R5` OK.
- `CODEX_R5_011_012.patch`: SHA256 `68a0544c0384bdb4087c2b63613276ff8c65010b7e6a8f2fd2e689c0c03094f9`; na osobnej kopii **oryginalnych plików pierwszego ZIP** sprawdzono `git apply --check` i faktycznie zastosowano patch; porównanie kontrolne sześciu kluczowych plików po patchu z R5 `6/6 MATCH` (ledger, parser, changelog, fixture testy, test R5).
- Archiwa zachowano w prywatnym magazynie właściciela; nie przenoszono ZIP ani sekretów do GitHub publicznego. To nie jest pełna aktualna kopia repozytorium ani binarnych żywych baz.

## Nowe FIND-03 / R6 — błąd type-contract timestamp, odtworzony 01.11.2026

- `src/kb3_pitch_native_ledger.py`, funkcja `shots_asof` tworzy `cutoff=as_utc(cutoff_utc)` (obiekt `datetime`). Przekazuje potem `cutoff=cutoff` do `_validated_stats_pair`, która wywołuje `as_utc(cutoff)`. Rzeczywista funkcja `src/kb3_pit_ledger.py:as_utc` w obecnym GitHub `main` akceptuje wyłącznie napis UTC; w przeciwnym razie rzuca `ValueError('TIMESTAMP_MISSING')`.
- **Niezależny wynik przed poprawką:** `test_codex_r5_xg_integrity.py` **8/9 PASS**, 1 ERROR (`test_012_e2e_immutable_pair_and_asof`), autentyczne wywołanie trafiało w `as_utc(datetime)`.
- **Minimalna poprawka na izolowanej kopii:** w `shots_asof` zamiast `cutoff=cutoff` przekazać **oryginalny znacznik** `cutoff=cutoff_utc`; bez zmiany semantyki cutoff i bez rozszerzania typu `as_utc`.
- `git apply --check` względem **już zrekonstruowanego R5**: PASS. Przygotowano [patch R6 w PR #124](../patches/CODEX_R5_FOLLOWUP_CUTOFF_UTC_2026-11-01.patch), SHA256 `7127f254e8dc30a73dede51a4b711a4cdbfa75ee8bf553951aa4ed2bd47a295c`.
- **Po lokalnej korekcie:** `test_codex_r5_xg_integrity.py` **9/9 PASS** w Pythonie 3.13. Następnie pięć wybranych suite **40/40 PASS**: R5 integrity 9, native Step11 13, legacy step06 8, strict stage2 8, SQLite writer workflows 2.
- **Rzetelne ograniczenie testów:** ze względu na **brak niezmienionych zależności w ZIP** użyto izolowanego testowego adaptera `src/kb3_pit_ledger.py` z dokładną semantyką czterech funkcji (`canonical/hexdigest/as_utc/GENESIS`) z aktualnego `main`; w strict stage2 użyto tylko odtworzonych oryginalnych fikstur `shots/stats` z `test_step14_pitchapi_xg_semantics.py`. Te adaptery/fixture nie są wysyłane do produkcji ani nie oznaczają pełnego checkoutu. Na początku niezależny test ujawnił błąd, którego wcześniejsza bardziej liberalna zaślepka nie wykryła. **Nie wykonano pełnych 197/108 regresji na kompletnym repo.**
- Nie badano realnego provider API. Nie wykonano migracji **kopii rzeczywistej** 3-ligowej bazy SQLite ani porównania wszystkich 73 prognoz po przeniesieniu 57 plików. **Nie można jeszcze scalić**.

## Kontrola rozjazdu od bazy Codex do obecnego main

Pobranie faktycznego GitHub `compare_commits` **`6813af619dbe620d321f233e73d2d107d34f8004` → `727dd78b555cad407ae2ed6a477710501de2e1b3`**: `ahead_by=25` commitów, **19** zmienionych ścieżek (w tym nowe archiwa oraz zmiany w dwóch binarnych SQLite). Zestaw 19 ścieżek porównano z autentycznym wykazem **57** ścieżek `evidence/changed-paths.txt` pierwszej paczki — **0 konfliktów na poziomie identycznej ścieżki**. To dobra przesłanka do trójstronnego importu, ale nie dowodzi zgodności interfejsów ani braku zmian semantyki danych; aktualne binarne SQLite nie mogą być nadpisane starszymi danymi. Wcześniejszy znaleziony FIND-03 potwierdza, że sama zgodność ścieżek nie wystarcza. Cały audit zostaje NO-GO.

## Odbiór wdrożeniowy po odzyskaniu paczek

1. Odtworzyć pełny aktualny checkout repo na odizolowanym runnerze i bezpiecznie zaimportować **spójne 57 plików R1–R4** oraz R5 + powyższy R6, po kontroli diffów i konfliktów z bieżącym `main`; brak naruszania `data/`, `models/`, sekretów lub chronionego TEST. Samo odzyskanie archiwum w Library nie publikuje jego zawartości do GitHub.
2. Pełny Python 3.11/3.12 offline CI 197/108 (z częściowym nakładaniem) + R5, wspólny `test_step14_pitchapi_xg_semantics.py`, pełna kontrola współdzielonych workflow.
3. Migracja wyłącznie na kopii **realnej** źródłowej SQLite, integralność, 29 historycznych tabel i triggerów, awaria/rollback, no-lookahead; oryginalne M0 V1 param SHA `55310f0e1dd3842e6d876069ef21b1380901b3a6cc6884cf6ec6ea351a5812d1` i archiwalne 73 prognozy bajtowo identyczne.
4. Dopiero następnie jeden budżetowany CI bez API i osobna decyzja właściciela o merge. NIE używać poprzednich 40/40 jako pełnego produkcyjnego `PASS`.

**Bramka po tym audycie:** R5 patch provenance **PASS**; R6 znaleziony i poprawiony **w izolowanej kopii**; 40/40 częściowych testów **PASS**; pełny checkout/regresje/realna migracja **PENDING**; `PR #124 MERGE_NO_GO`, `GATE16=PENDING`, `GATE17=PENDING`, ukończone 15/29.
