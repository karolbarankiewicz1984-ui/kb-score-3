# KB Score 3.0 — wykonanie kroku 01: aktualna baza M0, kopia, odtwarzanie i szyfrowany backup poza GitHub

**Data:** 2026-11-04; **status:** `PARTIAL_PASS / OWNER_PRIVATE_KEY_OFFSITE_RESTORE_PENDING`. **Bez:** merge PR, API, fit, zmiany M0, przepisania forecast, ENG TEST.

## Dowody rzeczywiście wykonanych operacji
1. [PR #147](https://github.com/karolbarankiewicz1984-ui/kb-score-3/pull/147): read-only skrypt `scripts/audit_kb3_step01_restore.py`, realny SQLite `data/forward_m0_720_eight/kb3_forward_eight.sqlite`; bajtowa kopia do osobnego katalogu tymczasowego, następnie `sqlite3.Connection.backup()` do drugiej osobnej bazy. Porównanie SHA samej kopii, wszystkich tabel i SHA ich wierszy, integralności SQLite, `foreign_key_check` i triggerów niezmienności. Próbny UPDATE wykonany tylko na odtworzonej, disposable SQLite i odrzucony. Oryginalna baza nadal bez zmian.
2. [GitHub Actions #41853754238](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/41853754238) SUCCESS; odtworzenie PASS. **Baza zamrożona w tym obrazie:** 126 prawdziwych prognoz M0 i 74 settlement; ten przyrost względem wcześniejszych 91 nie pochodzi z #146 (PR nadal draft). 8 tabel; `model_params_sha256=55310f0e1dd3842e6d876069ef21b1380901b3a6cc6884cf6ec6ea351a5812d1`; `model_manifest_sha256=add298d85ec2957f657bf6a6765cc093b284119bb2f45e001278bfd0c90da8bb`.
3. [GitHub Actions #41854296003](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/41854296003) SUCCESS: wygenerowano **wyłącznie zaszyfrowaną** kopię `AES-256-GCM + RSA-OAEP-SHA256` używając istniejącego klucza publicznego właściciela (RSA 3072-bit). Żadnych kluczy prywatnych ani plaintext SQLite w archiwum. Artefakt `kb3-step01-M0-current-encrypted-sqlite` ID `13335354221`, ZIP digest `sha256:4cc321e7302faaf690967ec35a536e9aeebcbe0f037da24acc5ec76e7ccb81f5`. GitHub artefakt wygasa po 14 dniach, więc nie stanowi trwałej kopii samodzielnie.
4. **Zapis poza repozytorium:** [Google Drive — KB3_M0_CURRENT_ENCRYPTED_BACKUP_2026-11-04.zip](https://drive.google.com/file/d/14VB_1YAGV3bj5FsjwLzEIanWa24LurAa/view?usp=drivesdk) w istniejącym folderze [Kopie zapasowe](https://drive.google.com/drive/folders/17NvQFKNkFd4eHZSqa-bNU0nFFSmHKTKo). Odczyt po uploadzie z Drive: 108776 bajtów. Ponownie pobrany ZIP ma dokładnie ten sam SHA-256, co oryginalny artefakt GitHub. ZIP CRC PASS; dokładnie dwa pliki (.enc i .manifest.json), brak plaintext. `encrypted_sha256=645eac0160154c7f8350b15fe322c3c90fa7323c441301407711af9865940e21`; manifest zgadza się z szyfrogramem.
5. **Snapshot source:** commit `17e2a75a6d4469534c8b7b5f5eeaaf08e34f18f8` (head PR #147 przy generacji, obejmuje bazę z main), bajty 741376; plaintext SHA-256 `d3314ff994f3d007cbcb7ea2c9bfe09e94cc6766c33137904207fcceb1c0529a`. Oryginalny plik nie został zmieniony przez kontrolę.

## Pozostały warunek kroku 01
- GitHub Actions i ChatGPT nie mają prywatnego klucza RSA właściciela, dlatego **nie wykonano rzeczywistego odszyfrowania kopii z Google Drive i osobnego restore po transferze**. Nie wolno oznaczać pełnego `OFFSITE_RESTORE_PASS` przed tym testem. Szyfrogram jest zweryfikowany bajtowo, ale dostęp do klucza musi pozostać poza repozytorium.
- W okresie prób M0 na main nadal mogą pojawić się nowsze prognozy/settlements; backup ma punktowy SHA i nie zastępuje regularnej polityki kopii. Nowsza wersja źródłowa wymaga kolejnej kopii.
- Nie scalono PR #147; skrypt i workflow pozostają w draft PR. Testy uruchomiono z tej gałęzi. Nie mylić ich z testem po merge.

## Decyzja operacyjna
Krok 01: **Bajtowa i logiczna kopia + szyfrowany upload poza repo = PASS; pełny odczyt plaintext z offsite = PENDING.** Kolejny bezpieczny ruch: rozpocząć odbiór #146 i równolegle naprawy #143, ale bez live merge/przełączenia przed zamknięciem uzgodnionych bramek. Osiągnięcie kroku 01 nie zmienia 15/29, GATE16/GATE17 PENDING, M0 ani Championa.

## Aneks decyzyjny 04.11.2026 — brak wymogu obsługi klucza prywatnego

Na życzenie właściciela **nie wymagamy posługiwania się prywatnym kluczem RSA jako blokującego warunku dalszych badań i przygotowania PR #146/#143**. Obowiązują dwa osobne statusy:

- `STEP01_OPERATIONAL_GO`: fizyczne kopiowanie obecnej realnej SQLite, druga kopia przez API SQLite, kontrola tabel/wierszy/SHA, poprawność kluczy obcych oraz odrzucenie próby modyfikacji immutable — PASS wg [CI 41853754238](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/41853754238). Można przejść do audytu, przygotowania kodu, testów na kopii i warunkowego pilotażowego wdrożenia w osobnych bramkach.
- `OFFSITE_DECRYPT_RESTORE_NOT_VERIFIED`: zaszyfrowany ZIP na Drive ma poprawny SHA/CRC i jest w prywatnym folderze, ale nie ma dowodu, że obecnie można go odszyfrować i odtworzyć po utracie repo; nie traktować jako jedynej kopii odtworzeniowej.

Oryginalne historyczne ustalenia powyżej pozostają nietknięte. **Bez przechowywania prywatnego klucza w GitHub/ChatGPT, bez odszyfrowywania, bez publikacji jawnej SQLite i bez obchodzenia szyfrowania.** Pełną disaster recovery można później rozwiązać alternatywnym zarządzanym magazynem po osobnym uzgodnieniu; nie blokuje to dalszego badania modelu.
