# KB Score 3.0 — GATE 09: kontrolny import historii — PASS (techniczny)

**Data odbioru:** 26.10.2026. **Zakres:** Premier League, sezon 2024/2025, league ID 39, źródło API-Football. **Status:** PASS dla pilota 1 liga / 1 sezon; nie jest to odbiór pełnej historii ani uruchomienie modelu ML.

## Co wykonano

1. Jedno rzeczywiste pobranie `fixtures?league=39&season=2024` w [GitHub Actions #40277192712](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40277192712): **380/380** spotkań, **380 unikalnych** identyfikatorów, 380 statusów FT. Liczba zgadza się z kontrolnym audytem kroku 05.
2. Import do fizycznego schematu SQLite v1 z GATE08: **380** rekordów meczów i **380** ścisłych map identyfikatorów własnego dostawcy API-Football. Dane oznaczono jako `RETROSPECTIVE`, bez fałszywej etykiety prematch. Niewyjaśnionych 22 par PitchAPI z GATE07 nie zatwierdzano.
3. **Idempotencja:** import #1 dodał 380 meczów, import #2 dodał **0**, ponownie rozpoznając 380. **Crash/restart:** kontrolowane przerwanie po zapisie 17 rekordów, a po wznowieniu 17 rozpoznanych i 363 dodane — 380 końcowo.
4. **19/19 automatycznych testów PASS** — 10 nowych testów importu (w tym konflikty ID, wyników, dat, 90-minutowy wynik przy dogrywce, błędy dostawcy, duplikaty i niedozwolona promocja REVIEW) oraz 9 regresyjnych testów bazy z GATE08.
5. **Trwałe archiwum poza GitHub Actions**: skompresowaną bazę zaszyfrowano **AES-256-GCM** i zapisano w prywatnym folderze Google Drive. Następnie **pobrano ją ponownie z Drive**, porównano SHA-256 bajtów szyfrogramu, odszyfrowano i sprawdzono integralność SQLite, klucze obce i 380 rekordów. Nie jest to tylko test pliku lokalnego.

## Niezależne dowody

- [Uruchomienie GitHub Actions — SUCCESS](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40277192712)
- [Kod importera](../scripts/step09_import_history.py) · [10 testów](../tests/test_step09_import_history.py)
- [Manifest w repozytorium](../data/audits/STEP09_IMPORT_2026-10-26.json)
- [Szyfrowane archiwum na Google Drive](https://drive.google.com/file/d/1S1blIbulStO8TZBvwu8JgVERPU-WsdDU/view)
- [Końcowy manifest archiwum na Drive](https://drive.google.com/file/d/1xwHgHWAVmOlkd0ZSxlgMs_PrTy8O1rvF/view)
- [Narzędzie przywracania](../scripts/step09_restore_archive.py) — wymaga pakietu Python `cryptography` i *oddzielnego* pliku z kluczem.

| Kryterium | Wynik |
|---|---|
| Lista API-Football, Premier League 2024/25 | 380/380 |
| Unikatowe identyfikatory źródła | 380 |
| Powtórny import | 0 nowych / 380 ponownie rozpoznanych |
| Wznowienie po zapisaniu 17 | 363 dodane / 17 rozpoznanych |
| Testy kroku 09 | 10/10 PASS |
| Testy regresyjne kroku 08 | 9/9 PASS |
| SQLite integrity_check | ok |
| SQLite foreign_key_check | 0 błędów |
| Archiwum Drive → ponowny odczyt → odszyfrowanie → odtworzenie | PASS |
| Nowe zakupy | 0 zł |

**SHA-256 źródłowej bazy SQLite:** `fc3f0ae2fe9fb4c89bbaf561571906fb35b23d3b1f03b7131a462f9dfe179fc4`.

**SHA-256 zaszyfrowanego pliku:** `231c6bab3154e973cebf9814bee0c4da7846ae584fdca6271f3ddf977007aa13`.

## Ograniczenia i bezpieczeństwo

- Klucz odzyskiwania jest udostępniony właścicielowi **jako odrębny plik**, nie jest przechowywany na GitHubie ani na Dysku Google. **Właściciel musi zachować go w bezpiecznym miejscu** (np. menedżer haseł); bez klucza archiwum będzie nieodwracalnie nieczytelne. Bezpieczne przechowanie klucza przez właściciela nie zostało jeszcze potwierdzone.
- Automatyzacja cyklicznych szyfrowanych backupów, retencja i operacyjne zarządzanie kluczami **nie są jeszcze wdrożone**; dzisiejszy test potwierdza jednorazowy odczyt i odtworzenie. GitHub Actions artefakt pomocniczy wygasa 02.11.2026, ale osobny zaszyfrowany plik Drive jest trwałym źródłem danych z tego pilota.
- Nie przechowywano surowego ciała JSON odpowiedzi API — tylko kanoniczne, zweryfikowane pola w SQLite, checksumy i identyfikatory. Danych historycznych nie przedstawia się jako faktycznie zaobserwowanych przed startem konkretnego meczu.
- Nie pobierano jeszcze statystyk spotkań, xG, kursów ani wszystkich lig. Nie uruchomiono treningu, prognostyki ani raportów produkcyjnych.

## Decyzja

**GATE09 = PASS (techniczny, dla jednego pełnego sezonu).** Wymagania odbioru: zgodność liczby z terminarzem, brak duplikatów po powtórnym imporcie, wznowienie po przerwaniu i trwały manifest/archiwum — wszystkie spełnione i udokumentowane.

**Kolejny krok: 10 — kontrola jakości i chronologii danych.** Rozszerzenie importu na następne ligi/sezony i rutynowe szyfrowane backupy dopiero po odpowiednich testach i ustaleniu bezpiecznego przechowywania klucza.
