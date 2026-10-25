# KB Score 3.0 — KROK 08: schemat, trwałe archiwum i test odtworzenia

**Data:** 25.10.2026. **Zakres:** infrastruktura bazodanowa i odbiór odzyskiwania — **bez importu historii meczów i bez treningu ML**. **Wynik testów:** PASS. **Klasyfikacja danych testowych:** wyłącznie SYNTHETIC_TEST_ONLY.

## 1. Architektura zatwierdzona w kroku 08

- **SQLite** jako podstawowy transakcyjny rejestr identyfikatorów, wydarzeń, prognoz, źródeł i historii; obsługuje spójność kluczy obcych i unikalność.
- **Parquet** jako planowany przyszły format dużych tabel treningowych w krokach 09–12. Nie ma jeszcze prawdziwych Parquetów ani hurtowego importu.
- **GitHub**: wyłącznie kod, schemat/migracje, testy i niewielkie niepoufne manifesty SHA; **nie** jedyne miejsce przechowywania bazy.
- **Google Drive**: trwały magazyn kopii poza GitHub Actions w folderze [KB Score 3.0 — Kopie zapasowe](https://drive.google.com/drive/folders/17NvQFKNkFd4eHZSqa-bNU0nFFSmHKTKo). W kroku 08 zapisano i ponownie pobrano **jedynie syntetyczny** backup; pełna produkcyjna replikacja nie jest jeszcze wdrożona.
- **GitHub Actions**: test migracji i odtwarzania na sztucznym przykładzie, bez kluczy API, bez kosztów dodatkowych. Artefakty testowe GitHub są tymczasowe, dlatego wykonałem niezależną kopię poza Actions.

## 2. Pliki techniczne

| Plik | Znaczenie |
|---|---|
| [migrations/001_initial_schema.sql](../migrations/001_initial_schema.sql) | Schemat SQLite v1, relacje i ograniczenia |
| [src/kb3_storage.py](../src/kb3_storage.py) | Inicjalizacja, kontrola integralności, backup online i odtworzenie |
| [tests/test_step08_storage.py](../tests/test_step08_storage.py) | Dziewięć testów migracji, duplikatów, mapowań i immutability |
| [.github/workflows/kb3-step08-storage-gate.yml](../.github/workflows/kb3-step08-storage-gate.yml) | Test GitHub Actions i syntetyczny backup |
| [data/audits/STEP08_BACKUP_MANIFEST_2026-10-25.json](../data/audits/STEP08_BACKUP_MANIFEST_2026-10-25.json) | ID kopii, SHA-256, URL trwałego backupu i wynik odtworzenia |

### Zaprojektowane tabele

1. Źródła: \`providers\`, \`source_snapshots\`.
2. Zespoły/liga: \`competitions\`, \`seasons\`, \`teams\`, \`team_aliases\`, \`team_provider_map\`.
3. Mecze: \`fixtures\`, \`fixture_revisions\`, \`fixture_provider_map\`.
4. Statystyki: \`match_stat_observations\`, \`match_events\`.
5. Kursy: \`odds_snapshots\` — bukmacher+rynek+linia+czas odczytu.
6. ML: \`model_versions\`, \`training_runs\`, \`feature_snapshots\`.
7. Prognozy i wyniki: \`predictions\`, \`prediction_publications\`, \`settlements\`.
8. Jakość i ewolucja schematu: \`quality_audits\`, \`schema_migrations\`.

### Gwarancje i ograniczenia

- **Unikat meczowy**: \`UNIQUE(season_id,home_team_id,away_team_id,kickoff_utc)\`; duplikat tego klucza jest odrzucany. Przełożenia i zmiany kickoff wymagają historii \`fixture_revisions\` i zasad importu kroku 09. Unikalność rzeczywistego meczu przy zmianie daty wymaga mapowania dostawcy, nie tylko tego klucza.
- **IDENTITY** z kroku 07: \`fixture_provider_map\` wymusza \`STRICT + APPROVED + fixture_id\` dla automatycznie zatwierdzonej pary. \`REVIEW\` i \`UNMATCHED\` nie mogą mieć wypełnionego kanonicznego fixture_id. **22 nierozstrzygnięte pary nadal są NIEZATWIERDZONE.**
- **Braki danych**: \`match_stat_observations.numeric_value IS NULL\` wymaga jawnego \`missing_reason\`; wartość 0 jest osobnym, poprawnym pomiarem.
- **Freeze**: \`predictions\`, \`prediction_publications\` i \`settlements\` mają triggery odrzucające UPDATE i DELETE. Korektę settlement należy dopisać nowym rekordem \`supersedes_settlement_id\`; starego wpisu nie ruszamy.
- **LIVE**: trigger wymaga daty utworzenia i rzeczywistego czasu przed kickoff oraz feature snapshotu \`VERIFIED_PREMATCH\`. Symulacje na dawnych meczach oznaczamy \`HISTORICAL_REPLAY\`, a nie LIVE.
- **Trenowanie**: żadnych tabel nie wypełniono prawdziwą historią; zastosowanie cech point-in-time będzie osobno testowane w krokach 09–12.

## 3. Testy i wiarygodne dowody

- [GitHub Actions — pierwszy test end-to-end](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40241295913): **SUCCESS**, 9/9 testów, backup oraz restore \`PRAGMA integrity_check=ok\`, \`foreign_key_check\` bez błędów.
- [GitHub Actions — test po zabezpieczeniu niezaszyfrowanych backupów](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40241611841): **SUCCESS**, 9/9 testów. Domyślne wywołanie backupu bez \`synthetic_test=True\` odrzuca operację: \`PRODUCTION_BACKUP_REQUIRES_ENCRYPTION\`.
- Backup zapisany w [Google Drive](https://drive.google.com/file/d/1DkaIfH24qf7z_KDuwbMzRuUd_iORbFxb/view) (17 459 bajtów w ZIP); **został ponownie pobrany bez użycia oryginalnego GitHub artifact**.
- Po niezależnym odczytaniu ZIP z Google Drive: CRC ZIP OK, backup SQLite 212 992 bajty, suma SHA-256 zgodna, \`PRAGMA integrity_check=ok\`, \`PRAGMA foreign_key_check\` bez błędów, schema_version=1, 1 syntetyczny mecz odczytany, obecne triggery immutability.
- Backup ID: \`20261025T224033196429Z-95353b524e\`
- SHA-256 pliku SQLite: \`ae76048deebd45bc0d97f21b189859fec0ae42f5e69ca51eb197c7b0ad6fe80f\`.
- Manifest dowodu w [data/audits](../data/audits/STEP08_BACKUP_MANIFEST_2026-10-25.json) oraz status w [głównym planie Google](https://docs.google.com/document/d/10wjHL3r3OAuxtezwcIeWztxS8lwjhYon5GM3BLhI0xE/edit).

## 4. Instrukcja odzyskiwania po awarii

**Teraz, dla danych syntetycznych:**
1. Otwórz folder Drive i pobierz \`KB30_GATE08_SYNTHETIC_BACKUP_2026-10-25.zip\`.
2. Rozpakuj do katalogu roboczego. Manifest leży w katalogu \`backup/\`; odpowiada mu plik \`.sqlite3\`.
3. Sprawdź SHA-256 z manifestem; **nie zastępuj automatycznie istniejącej bazy**.
4. Uruchom \`python -m src.kb3_storage restore --manifest <manifest> --folder <katalog backup> --target <nowa nazwa sqlite3>\`.
5. Sprawdź \`PRAGMA integrity_check\`, \`foreign_key_check\`, wersję migracji i liczebności; dopiero wtedy można użyć nowego pliku jako odzyskanego źródła testowego.

**W przyszłości, dla prawdziwych danych:**
- Wyłącznie szyfrowany i uwierzytelniony backup (np. AES-GCM z kluczem w wydzielonym bezpiecznym magazynie) oraz dokumentowane odzyskanie klucza; zwykła kopia SQLite w ZIP nie nadaje się jako produkcyjny backup na Dysk Google.
- Test odtworzenia także z magazynu docelowego, rotacja wersji, monitorowanie miejsca, retencja backupów, alarmy w razie braku kopii.
- Kopie rzeczywistych danych muszą respektować warunki przechowywania/redistribucji API-Football i PitchAPI.
- Zapis do Dysku Google podczas kroku 08 był **jednorazowym uploadem przez połączone narzędzia**, a nie już istniejącym harmonogramem GitHub→Drive. Automatyczna synchronizacja, klucze szyfrujące i retencja mają powstać przed uruchomieniem produkcji — wymagają osobnego odbioru.

## 5. Weryfikacja GATE 08

| Wymaganie z planu | Wynik |
|---|---|
| Migracja bazy danych i odczyt | PASS |
| Wymuszanie unikatów | PASS — test negatywny UNIQUE |
| 22 par REVIEW nadal niezatwierdzonych | PASS — ograniczenie CHECK i test |
| Niezmienność prognoz / publikacji / settlement | PASS — triggery i testy negatywne |
| Backup → restore z kontrolą SHA i integralności | PASS |
| Trwały, niezależny backup poza Actions | PASS — wyłącznie SYNTHETIC, Drive + niezależny download i restore |
| Identyfikator kopii i instrukcja awaryjna | PASS |
| Brak nowych wydatków | PASS — bez zakupów |
| Pełna historia i Parquet wypełnione produkcyjnie | NIE WCHODZIŁY W ZAKRES — kroki 09–12 |
| Szyfrowany, samoczynny backup produkcyjny | NIEWDROŻONY — osobny warunek przed produkcją |

**Wniosek:** techniczna bramka KROKU 08 może być **PASS** dla schematu i prawdziwego testu odtworzenia syntetycznej bazy. To **nie** jest zgoda na magazynowanie nieszyfrowanych rzeczywistych danych. **KROK 09**: bezpieczne próbne pobranie i import jednej ligi/jednego sezonu z idempotencją i wznowieniem, dopiero po sprawdzeniu ograniczeń licencyjnych źródeł.
