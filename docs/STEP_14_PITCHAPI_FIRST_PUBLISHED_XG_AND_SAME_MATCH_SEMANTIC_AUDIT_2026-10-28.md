# Krok 14 — PitchAPI: pierwotna publikacja xG i porównanie identycznych historycznych meczów (28.10.2026)

## Ustalenie z oficjalnego źródła

Sprawdzona bezpośrednio [dokumentacja PitchAPI](https://pitchapi.dev/) (28.10.2026) udostępnia:

- `GET /v1/matches/{id}/shots` → `data.match_id`, `periods[].shots[].team_id` oraz `expected_goals` (0–1): prawdopodobieństwo gola **przed strzałem**. `expected_goals_on_target` (**xGOT**, post-shot) jest **inną** metryką.
- `GET /v1/matches/{id}/stats` → `data.match_id`, `home_team.id`, `away_team.id`, `period=All`, `items[].key=expected_goals` — liczbowy w zapisie `double` meczowy xG obu stron. `npxG` pomija karne i **nie jest tą samą** liczbą.
- Historia meczu i statystyk jest obecnie deklarowana od roku 2021, lecz to jest **historyczna dostępność retrospektywna dziś**, a NIE niezależny dowód, że taka sama wersja team xG była opublikowana przed spotkaniem w latach 2023–2025.
- Dokumentacja nie określa dla pojedynczego dawnego `match_id + team_id + xG` pola `provider_original_published_at`, dawnego `first_seen_at`, wersji/wcześniejszej rewizji wartości czy gotowego endpointu `as_of`. Oznacza to **brak publicznego potwierdzenia**, nie dowód, że wewnątrz firmy nie istnieją metadane publikacji.
- Changelog z 19.09.2026 odnotowuje nowe identyfikatory w części lig po przebudowie feedu. To niezależny sygnał, że obecny identyfikator i aktualna reprezentacja historycznego spotkania nie mogą być automatycznie założone jako identyczne z tym, co było publiczne dawniej.

W `data/audits/STEP14_OWNER_RSA_FULL_380_60_ELO_10_OF_10_SCREEN_2026-10-28.json` udowodniono 380/380 + 60/60 historycznych wyników FT, ale oryginalny ZIP PitchAPI zawiera **katalog i listy zakończonych meczów**, nie autentyczne historycznie pobrane `shots` ani `stats` z udokumentowaną datą ich pierwszej publikacji. Zachowane PitchAPI xG z końca października 2026 r. są prawdziwymi dzisiejszymi obserwacjami, **nie** dowodem daty publikacji xG w 2023 r.

**Stan dowodu oryginalnego PitchAPI xG sprzed targetów: `BLOCKED_MISSING_PROVIDER_ORIGINAL_FIRST_PUBLISHED_AT`.**

## Jak weryfikujemy definicję bez pomieszania meczów, stron i dostawców

Dodano `src/kb3_step14_pitchapi_xg_semantics.py`, `scripts/step14_owner_pitchapi_xg_same_fixture_local.py` oraz **19 testów czysto syntetycznych i mocków** (14+5) oraz 17 testów zamrożonego starego FPL, razem **36/36 PASS CI #40701194878**. Żaden test GitHub Actions nie odpytywał PitchAPI ani nie używał prywatnego ZIP lub klucza.

Program dla Windows, po lokalnym odszyfrowaniu oryginalnego RSA, wybiera deterministycznie **6** spośród zweryfikowanych **380** meczów ligi angielskiej 2023/24 (indeksy chronologiczne 20,84,148,212,276,340). Połączenie FPL fixture → PitchAPI native fixture i obie drużyny potwierdza **pełny historyczny, jednoznaczny 20-drużynowy fingerprint godzin meczów home/away**, nie zbliżona nazwa drużyny. Natywne ID zostają w pamięci procesu.

Dla każdego z 6 meczów porównujemy trzy pary `home, away`:

1. Suma `shots[].expected_goals` dla `team_id` gospodarza i gości w **tym samym native match ID** (bez xGOT).
2. `period=All` + `key=expected_goals` ze `stats` dla tych samych `home_team.id`, `away_team.id` (bez npxG i bez podwojenia połówek).
3. Zsumowane `expected_goals` zawodników FPL/Opta dla **dokładnie tego samego starego FPL fixture ID + team_h/team_a**, ze starego SHA-pinned pliku opublikowanego **27.05.2024, 18:05:12 UTC**. `was_home` i `opponent_team` zostały wcześniej zweryfikowane z oryginalnym terminarzem; nie wolno zastępować `expected_goals_conceded` wierszy zawodników meczowym xGA.

Skrypt dopuszcza **maksymalnie 12** bieżących wywołań PitchAPI SDK (6× shots, 6× stats), nigdy nie pobiera wyników docelowych ani zbioru VALIDATION/TEST. Oblicza tylko zbiorcze **MAE, medianę, max i liczniki różnic** 0,02/0,10/0,25 dla Pitch shots vs Pitch team stats oraz FPL vs Pitch stats. Nie zapisuje wartości xG, nazw, ID, payloadów, klucza ani oryginalnego zaszyfrowanego tekstu. Raport powstaje lokalnie **poza GitHub**. Nawet idealny wynik w 6 przypadkach **nie dowodzi tej samej metodologii/modelu predykcyjnego u dwóch dostawców** — to tylko mierzalny test zgodności na próbce.

### Uruchomienie na Windows

Po pobraniu aktualnego `main` do osobnego katalogu, w PowerShell w folderze projektu:

```powershell
Test-Path ".\scripts\step14_owner_pitchapi_xg_same_fixture_local.py"
Test-Path Env:PITCHAPI_API_KEY
```

Jeśli klucz API jest ustawiony lokalnie, drugie polecenie zwróci `True`. Jeśli go nie ma, nie wysyłać klucza przez ChatGPT; można go wprowadzić bez ujawniania na ekranie:

```powershell
$secure = Read-Host "Klucz PitchAPI (lokalnie)" -AsSecureString
$bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
try { $env:PITCHAPI_API_KEY = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($bstr) }
finally { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr) }
```

W razie braku SDK: `py -3 -m pip install pitchapi` (oficjalne, aktualne SDK). Następnie:

```powershell
py -3 -m scripts.step14_owner_pitchapi_xg_same_fixture_local --archive-zip "$HOME\Downloads\KB3_PITCH_PL_2023_2026_NATIVE_20261026.zip" --private-key "$HOME\Desktop\KB3_760_PAKIET_ODZYSKIWANIA_POUFNE\KB3_760_KLUCZ_ODZYSKIWANIA.pem" --output "$HOME\Desktop\KB3_STEP14_PITCH_XG_SEMANTIC_AUDIT.json"
```

Skrypt **nie był uruchomiony na właścicielskim Windows w momencie tego wpisu** — wynik liczbowy realnych 6 spotkań jest **NIEZNANY**, NIE wolno go domniemywać ani przedstawiać jako PASS.

## Bezpośrednie pytania do PitchAPI potrzebne do odblokowania historycznego xG

Dostawca musi odpowiedzieć **dla konkretnego dawnego `match_id + team_id + metric=expected_goals + period=All`**:

1. Czy **pierwotna wartość** team xG oraz `shots[].expected_goals` była udostępniona użytkownikom jego API przed kolejnym wskazanym kickoffem? Prosimy o `first_available_at_utc`, nie godzinę dzisiejszego pobrania lub finalnej korekty.
2. Prosimy o autentyczną historyczną odpowiedź `stats` i `shots`, `source_version`, SHA256 payloadu, niezmienny identyfikator wersji i najlepiej niezależny archiwalny serwerowy log (timestamp + hash) poświadczający publikację. Jeśli dane zostały dodane retroaktywnie, prosimy o `backfill_at` i opis korekt.
3. Jaki upstream dostarcza `team expected_goals`, jaki jest zakres strzałów (karne, samobójcze, dogrywka, konkurs karnych), czy statystyka `stats` jest sumą identycznego zbioru `shots[].expected_goals`, czy wyliczeniem z odrębnej procedury? Czy wartości w latach 2023/24 i 2024/25 były ponownie przeliczane?
4. Czy `match_id/team_id` oraz historyczne `shots` są stabilne wersjami w latach 2023/24–2025/26, czy zdarzały się migracje i zmiany ID podobne do opisanych w changelogu 2026?
5. Czy udostępniany jest eksport per-fixture/per-team *as-of* przed określonym historycznym terminem? Jeśli nie, prosimy o formalne potwierdzenie braku historii poprzednich wersji.

**Tylko pierwotne i niezależnie sprawdzalne poświadczenie pozwala certyfikować oryginalne xG PitchAPI.** Sama dzisiejsza zgodność liczbowych xG z FPL nie zastępuje publikacji historycznej. Bez źródłowych dowodów `null + missing_flags`; każda ewentualna zmiana definicji wymaga oddzielnej wersji metodologii i ponownego audytu, nie dopuszcza automatycznie oryginalnego CatBoost M1.

**Status bez zmian: 13/29, GATE14 PENDING, TRAIN_PIT 0/760, VALIDATION_PIT 0/380, bez M1 treningu, M0 oraz 20 zamrożonych prognoz i TEST bez zmian.** [Zamrożony rejestr](../data/audits/STEP14_PITCHAPI_ORIGINAL_XG_FIRST_PUBLICATION_AND_SEMANTICS_STATUS_2026-10-28.json).
