# KB Score 3.0 — krok 14: autentyczne PitchAPI home_team_id / away_team_id (kontrola właściciela)

**Status 27.10.2026:** jawne źródła GitHub/GDrive przejrzane: brak obu natywnych `team_id` historycznych czterech spotkań. Audyty Step06 (60 próbek) i Step07 (60 wpisów) nie zawierają tych czterech `fixture_id`; Step12 SAFE zawiera tylko `fixture_id/kickoff/partition`. W Drive katalog 19 kopii zawiera poprawny, uprzednio niezależnie odtworzony **zaszyfrowany** oryginał [KB3_PITCH_PL_2023_2026_NATIVE_20261026.zip](https://drive.google.com/file/d/1_wLVJtOSwjwQwHhjBa54-3f0-aCzhyqJ/view), SHA256 `301bae69251d19a0192e12c2c033636b3f2822a15dcea2c4beaca28f4b45de2e`, chain SHA `33c750f2db89a0df5faeba9348652a451f33548959839ff7bb0ca49210c2b367`. Zapisane historyczne 1140 oryginalnych meczów z czasem rzeczywistego pobrania w **2026**, a nie przed meczami 2023–2026.

**Brak w tej sesji oryginalnego prywatnego klucza RSA** (celowo nie jest przechowywany w GitHub/Drive/logach) powoduje, że rzeczywistych natywnych wartości `team_id` nie da się uczciwie jeszcze odczytać. Nie wolno ich rekonstruować z nazw, wyników, samego kickoff ani sztucznych ID w testach.

## Cztery celowe dopasowania do kontroli

| PitchAPI fixture_id | Oczekiwana para z archiwalnego publicznego bloba | Kickoff UTC | Rola |
| --- | --- | --- | --- |
| `m_3AMymS` | Everton – Newcastle United | 2024-10-05 16:30 | TRAIN |
| `m_4AseJ9` | Leeds United – Everton | 2025-08-18 19:00 | VALIDATION |
| `m_0lzfjT` | Liverpool – Arsenal | 2025-08-31 15:30 | VALIDATION |
| `m_0JJdwI` | Sunderland – Aston Villa | 2025-09-21 13:00 | VALIDATION |

Do każdego `fixture_id` odczytywane są **dwie autentyczne natywne wartości** `t_XXXXXX` z podpisanej oryginalnej listy `matches`, obie źródłowe nazwy i dokładny UTC. Weryfikacja niezależnego czasu publicznego SHA i opublikowanego wtedy zestawu nazw opiera się na osobno zamrożonym [audytowym blobie 60](../data/audits/STEP14_HISTORICAL_BLOB_60_2026-10-27.json) oraz [GH Archive eventach](../data/audits/STEP14_GHARCHIVE_SERVER_PUSHCLOCK_2026-10-27.json). Stały słownik sezonów konwertuje provider `2024/2025` na publiczny `2024-25`, odpowiednio `2025/2026` na `2025-26`. Nazwy muszą być dokładne po bardzo konserwatywnym usunięciu końcowego `FC/AFC`. Każda niezgodność blokuje `identity_crosswalk_confirmed`. Nie stosuje się fuzzy join ani rezultatów meczu do parowania.

## Dokładny bezpieczny sposób uruchomienia na zaufanym komputerze właściciela

Potrzebne są **dwa pliki obecne tylko lokalnie**: oryginalny ZIP pobrany z [Dysku Google](https://drive.google.com/file/d/1_wLVJtOSwjwQwHhjBa54-3f0-aCzhyqJ/view) i prywatny klucz PEM, który właściciel posiada offline. **Nie należy przesyłać PEM, zrzutów jego zawartości ani odszyfrowanej pełnej bazy do ChatGPT, GitHub lub Google Drive.** Jeżeli PEM zaginął, nie da się odszyfrować oryginału bez prawidłowego klucza.

W katalogu lokalnej kopii repozytorium `kb-score-3` należy upewnić się, że kod jest aktualny (`git pull --ff-only`) i zainstalować bibliotekę `cryptography` lokalnie (`python -m pip install cryptography`), o ile jeszcze jej nie ma.

**Linux, przykład (zmień ścieżki na rzeczywiste):**

```bash
python3 -m scripts.step14_native_pitch_teamids_local \
  --archive-zip "$HOME/Downloads/KB3_PITCH_PL_2023_2026_NATIVE_20261026.zip" \
  --private-key "$HOME/.local/share/kb3/private-rsa.pem" \
  --output "$HOME/KB3_STEP14_NATIVE_TEAM_IDS_PRIVATE.json"
```

**Windows PowerShell, przykład (zmień ścieżki na rzeczywiste):**

```powershell
py -3 -m scripts.step14_native_pitch_teamids_local `
  --archive-zip "$HOME\Downloads\KB3_PITCH_PL_2023_2026_NATIVE_20261026.zip" `
  --private-key "$HOME\Documents\KB3-private-rsa.pem" `
  --output "$HOME\Desktop\KB3_STEP14_NATIVE_TEAM_IDS_PRIVATE.json"
```

Ścieżka wyniku musi być **nowa i poza katalogiem repo**, plik tworzony jest bez nadpisywania (na Unix z uprawnieniami `0600`). Do raportu przechodzą wyłącznie 4 dwuelementowe pary `pitch_home_team_id/pitch_away_team_id`, nazwy i statusy kontroli, źródłowe SHA, bez wyników, kursów, sekretów i TEST. Po prawidłowym zakończeniu konsola wypisuje wyłącznie `MATCHED` (0–4), `TRAIN` (0–1), `VALIDATION` (0–3), SHA raportu i `GATE14 PENDING`; identyfikatory są **tylko we własnym pliku lokalnym**.

**Bez dostępu do PEM nie należy uruchamiać jakichkolwiek zapytań sportowego API ani zastępować `t_XXXXXX` sztucznymi wartościami.**

## Walidacja kodu i ograniczenia

[Weryfikator par](../src/kb3_step14_native_team_crosswalk.py), [bezpieczny runner prywatnego źródła](../scripts/step14_native_pitch_teamids_local.py), [10 negatywnych i pozytywnych testów jednostkowych](../tests/test_step14_native_team_crosswalk.py). [GitHub Actions 10/10 PASS](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40497546091): testy używały **wyłącznie wytworzonych w kodzie przykładowych par**; **nie potwierdzają rzeczywistych natywnych wartości**.

Odszyfrowanie historycznych **retrospektywnych** źródeł z 26.10.2026 potwierdzi tożsamość `PitchAPI.fixture_id → PitchAPI home_team_id/away_team_id`, ale **nie** stwierdzi, że cechy Elo/xG były dostępne przed każdym historycznym meczem. Formalny `GATE14 PENDING`, tylko 13/29, oficjalne 0/760 TRAIN dopuszczonych. Brak naruszenia zamrożonych 20 prognoz, M0 i wyników TEST.
