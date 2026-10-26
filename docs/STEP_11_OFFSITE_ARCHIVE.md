# KB Score 3.0 — GATE11: trwała kopia 760 historycznych meczów — TEST ODTWORZENIA PASS

**Data:** 26.10.2026. **Zakres:** Premier League 2023/24 + 2024/25; **760/760** historycznych wyników. **GATE11 nadal PENDING**, projekt **10/29**. Bez treningu i historycznej certyfikacji PIT.

## Weryfikowalne dowody

- [GitHub Actions: zaszyfrowanie realnej bazy](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40293935946) — SUCCESS: sześć testów syntetycznych, import 760 rzeczywistych meczów, idempotencja, utworzenie zaszyfrowanej kopii bez eksportu surowej SQLite.
- [Prywatne archiwum na Dysku Google](https://drive.google.com/file/d/1lA1Z2qNSWyGxn_6OcyFl3ZmK147BWsn-/view?usp=drivesdk) — **57 824 B ZIP**, w środku wyłącznie `.enc` i manifest. Folder docelowy: `KB Score 3.0 - Kopie zapasowe`. Nie przechowywać tam klucza prywatnego.
- **Niezależne odtworzenie z Google Drive:** kopię pobrano ponownie z folderu Drive do odrębnego katalogu, porównano SHA-256 całego ZIP, sprawdzono zaszyfrowany plik oraz manifest, odszyfrowano *oddzielnym kluczem prywatnym*, zweryfikowano hash SQLite, `PRAGMA integrity_check=ok`, `foreign_key_check=0`, 760 zwykłych zakończonych spotkań, 760 map zatwierdzonych i dwa sezony po 380.
- [Trwały manifest audytu](../data/audits/STEP11_760_OFFSITE_RESTORE_2026-10-26.json) zawiera SHA źródeł audytu i pliku, liczby oraz ID kopii. **Nie zawiera klucza ani surowych rekordów**.

## Bezpieczeństwo archiwum

- `scripts/step11_archive_v2.py`: spójny snapshot transakcyjny SQLite; losowy klucz AES-256-GCM dla każdej kopii; publiczny RSA-3072/OAEP-SHA256 szyfruje ten klucz; SHA-256 i manifest kontrolują integralność.
- `config/step11_archive_recipient_public.pem` jest wyłącznie **kluczem publicznym**. Klucz **prywatny** stworzono poza repo, nie umieszczono go na GitHubie, Google Drive, ani w logach. Dostępny jest właścicielowi jako oddzielny bezpieczny plik do zachowania offline.
- Nowy format `KB3ENC2` nie modyfikuje starej kopii `KB3ENC1` dla 380 spotkań z kroku 09. Nie nadpisuje kopii oraz odrzuca uszkodzony szyfrogram, zmieniony manifest, obcy klucz, niespójne dane i niezgodną liczbę sezonów.
- Workflow kopii jest **jednorazowy**, nie uruchamia samoczynnego codziennego harmonogramu i nie tworzy nowego zakupu. GitHub artifact z szyfrogramem ma ograniczoną retencję, **Google Drive** jest trwałym magazynem.

## Granice dowodu

- Klucz odszyfrowujący należy pobrać i zachować przez właściciela poza folderem szyfrogramu, z dodatkową kopią zapasową. Bez niego plik jest nieodwracalnie nieczytelny. **Nie potwierdzono, że właściciel wykonał własną kopię klucza prywatnego.**
- Rzeczywisty powtórny odczyt i restore potwierdzają **trwałość i integralność archiwum 760**, a nie automatycznie zgodność z wszystkimi warunkami retencji/licencji dostawcy. Przed regularnym gromadzeniem większych wolumenów wymagane jest potwierdzenie uprawnień i polityki retencji danych.
- Dane odtworzone dzisiaj są w klasie **RETROSPECTIVE**. Nie dowodzą, że wyniki lub xG były dostępne historycznie przed konkretną dawną prognozą. `VERIFIED_PREMATCH=0`, `training_allowed=false`, brak nowego modelu i nowych typów.
- Do ukończenia **GATE11** pozostaje mechanizm faktycznych punktowych zapisów czasu udostępnienia informacji (wraz z wersją treści rekordu), kontrola xG, decyzje co do niezatwierdzonych ID PitchAPI i końcowa niezależna akceptacja. Nie wolno awansować do kroku 12 na podstawie samej kopii.

## Dokumentacja techniczna

- [Kod archiwizacji i odzyskania](../scripts/step11_archive_v2.py)
- [Testy](../tests/test_step11_archive_v2.py)
- [Workflow](../.github/workflows/kb3-step11-encrypted-archive.yml)
- [Dziennik kroku 11](STEP_11_PROGRESS.md)
