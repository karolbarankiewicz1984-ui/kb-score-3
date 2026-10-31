# KB Score 3.0 — kontrolowane przygotowanie wdrożenia Codex R5 (31.10.2026)

**Status: STAGING_PREPARED / SOURCE_NOT_APPLIED / MERGE_NO_GO.** Ten dokument znajduje się wyłącznie na izolowanej gałęzi odbiorowej `review/codex-r5-staging-20261031`, utworzonej z autentycznego `main` `86a6cfb2ca9a5b5cf5b19b761d0f81ef12a0a3fb`. Nie dowodzi przeniesienia kodu Codex na GitHub ani zaliczenia testów. To instrukcja i lista kontroli do kontynuacji w tej samej gałęzi.

## Źródła i niezmienne referencje

- Rejestr bazowy: [issue #121](https://github.com/karolbarankiewicz1984-ui/kb-score-3/issues/121); dotychczasowy [R5 review](https://github.com/karolbarankiewicz1984-ui/kb-score-3/issues/121#issuecomment-6532740202).
- Oryginalny ZIP `KB_SCORE_3_CODEX_REVIEW.zip`, SHA256 `22964c177db029b912b5f47b8a8b66d0998d722c772335434eb81e537d1c88c2`, to **częściowy zestaw 57 zmienionych plików**, nie pełny checkout.
- Offline R5 ZIP `KB_SCORE_3_CODEX_R5_011_012_REVIEW_2026-10-30.zip`, SHA256 `d06446dd9f31ab056f2d45fc17bfaa701e1e38904ecb1aee55517002b7063a07`; zawiera `CODEX_R5_011_012.patch`, `MAIN_FIXTURE_UPDATE.patch`, dokumentację i 9 nowych testów. **ZIP jest w rozmowie ChatGPT, nie na tej gałęzi ani w GitHub Releases.**
- Oryginalna baza Codex `6813af619dbe620d321f233e73d2d107d34f8004`; według metadanych końcowy lokalny Codex `1b35907b9242ea15a3070c93af352b92a274231d`, ale **nie jest to ref zdalnej gałęzi**.
- Badawczy M0 V1 param SHA256 `55310f0e1dd3842e6d876069ef21b1380901b3a6cc6884cf6ec6ea351a5812d1`; 73 wcześniej zamrożone oryginalne prognozy muszą pozostać identyczne; chroniony TEST Premier League 2026/27 zamknięty.
- Formalnie **15/29**, `GATE16=PENDING`, `GATE17=PENDING`, `CATBOOST_WITH_XG=NOT_TRAINED`; bez zmiany Championa.

## Dlaczego NIE wolno teraz przejść prosto do merge

Porównanie obecnego GitHub `main` z plikami ZIP ujawniło, że `src/kb3_shot_feed_validation.py`, `tests/test_codex_r5_xg_integrity.py`, `docs/CODEX_CHANGELOG.md`, `migrations/005_m0_publication_proofs.sql` i `.github/workflows/kb3-offline-regression.yml` **nie istnieją jeszcze na main**. Natomiast `src/kb3_pitch_native_ledger.py` na main to wcześniejsza wersja źródła (blob SHA `e97bae8aa4cbd359cac99e0a3c901047bb942cba`), nie wariant ze zrzutu Codex. R5 zmienia interfejs wywoływany przez wcześniejszy patch i zależy od innych 55 plików. Nie wystarczy dopisać jednego importu lub wymienić dwóch plików.

## Zakres późniejszego kontrolowanego PR (nie wykonano jeszcze)

1. Pełny, prywatny checkout `main`; odtworzyć oryginalną gałąź Codex na kopii. Weryfikacja źródeł i SHA, porównanie bazy Codex vs bieżący HEAD, pełna analiza różnic; nigdy nie nadpisywać działającego `main`.
2. Przenieść na tę gałąź odbiorową **całą spójną serię zmian Codex R1–R4** z oryginalnego ZIP, wykluczając `data/`, `models/`, sekrety, żywe bazy, istniejące raporty i prognozy. Wykonać i przejrzeć trójstronny merge, ze szczególnym uwzględnieniem zmian od `6813af6`. W razie konfliktu zatrzymać i opisać rozstrzygnięcie.
3. Zastosować `CODEX_R5_011_012.patch` i `MAIN_FIXTURE_UPDATE.patch` do prawidłowej bazy, dopiero po `git apply --check`; każdy hunk sprawdzić na finalnych plikach. Zmiany R5:
   - FIND-01: `COMPLETE_SHOT_XG` tylko przy dokładnie jednej poprawnej, niezależnej parze `total_shots` w okresie `All` i zgodnej liczbie strzałów; brak/duplikat/niezgodność => null + `UNVERIFIED`.
   - FIND-02: nieredagowalny sidecar `pitch_shot_stats_receipts`, oryginalny stats payload i jego SHA, niezależny zegar, transakcyjny zapis z shots, kontrola podczas `verify()` i `shots_asof()`. Starszy pobór bez statystyk musi zostać w kwarantannie, nie uzyskać fikcyjnego `COMPLETE`.
4. Weryfikować prawdziwe wywołania: nie wolno oznaczać statusu `COMPLETE` przy braku obu natywnych odpowiedzi. Zmiana parsera nie jest tożsama z podłączeniem `stats_payload` do rzeczywistego zbieracza. Odrębny Step17 osiem-ligowy collector ma obie odpowiedzi, ale nie dowodzi poprawności ścieżki V2.
5. Wersjonowanie i bezpieczeństwo SQLite: przeprowadzić migrację **na kopii autentycznej bazy**, a nie na jej produkcyjnym pliku; porównać 29 historycznych tabel, wszystkie rekordy i digest przed/po, immutable UPDATE/DELETE i rollback; żaden stary SHA nie może się zmienić. W razie usterki: rollback kopii i NO-GO.
6. Pełne testy na kompletnym repo i Python 3.11 (oraz 3.12 offline, jeśli możliwe), w tym wszystkie historyczne suite z raportów Codex (197/108, z częściowym pokrywaniem się), 9 nowych testów R5, `test_step14_pitchapi_xg_semantics.py`, oryginalny M0 720 V1, 73 archiwalne prawdopodobieństwa, 100 FIT + 50 późniejszych HOLDOUT, celowe testy negatywne i `git diff --check`.
7. Audyt bezpieczeństwa i kosztów: przed jakimkolwiek rzeczywistym GitHub Actions sprawdzić przywrócenie puli od 01.11.2026 i rodzaj triggerów; dopiero po testach offline jeden kontrolowany CI run bez fit i bez API, bez dostępu do chronionego TEST. Pełny test z dostawcą tylko osobno, po wyraźnej zgodzie na jego zakres i po kontroli API.
8. Po spełnieniu bramek: osobna decyzja o scaleniu; dopiero następnie ocena prawdziwych nowych forecastów, serwerowego freeze < kickoff, settlementów oraz kompletności natywnego xG. Żadnego retrospektywnego backfill prognoz.

## Macierz odbioru (na 31.10.2026)

| Kontrola | Dowód | Stan |
|---|---|---|
| Autentyczna paczka R5, SHA/CRC | R5 ZIP SHA i testzip przeprowadzony offline | PASS tylko dla paczki |
| Dwa błędy FIND-01/02 | R5 patch + 40/40 wybranych syntetycznych testów | OFFLINE_PARTIAL_PASS |
| Zależności od 55 wcześniejszych zmian | Oryginalny częściowy zrzut; kod main różny | OPEN |
| Spójny zestaw źródeł na gałęzi odbiorowej | Jeszcze nieprzeniesiony | OPEN |
| Pełny checkout i pełne testy 197/108 + nowe | Brak takiego niezależnego uruchomienia | OPEN |
| Migracja i rollback realnej kopii SQLite | Nie wykonano | OPEN |
| 73 prognozy M0 V1 bajtowo identyczne | Nie zweryfikowano z patchem na pełnym checkout | OPEN |
| GitHub Actions/SDK/live | 31.10 ostatnie zadania wciąż failure | BLOCKED |
| Merge do main / wybór Championa | Zakaz bez niezależnych bramek | NO-GO |

## Zasada pracy i zapisów

Każdy późniejszy commit do tej gałęzi musi mieć: listę ścieżek, pochodzenie poprawki (oryginalny ZIP/sha), odtwarzalny wynik testów i rezultat negatywnych przypadków. Dopisywać kolejne wpisy do `docs/ZMIANY.md` i centralnego issue #121; istotne decyzje synchronizować z Google Docs. Dopuszczalne jest przygotowywanie testów offline i przegląd diffu bez minut Actions. Nie przekształcać tego dokumentacyjnego PR w `ready for review`, dopóki gałąź nie zawiera rzeczywistego zweryfikowanego kodu.

**Decyzja obecna: GO na izolowany staging i dokumentację; NO-GO na kodowy merge, fit i produkcję.**
