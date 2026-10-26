# KB Score 3.0 — Krok 12: pierwszy REALNY indeks 1520 fixture PitchAPI

**Data:** 26.10.2026  
**Status:** STEP12 W REALIZACJI — GATE12 **PENDING** (11/29 formalnie odebranych).  
**Bez nowej subskrypcji, bez treningu, bez zmian KB2.1/API Market/MultiModel.**

## Rzeczywiste wyniki jednorazowej procedury

[GitHub Actions #40345911294](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40345911294): offline testy bezpieczeństwa PASS, a następnie **pięć** odczytów z istniejącego PitchAPI: katalog oraz 4 kompletne sezony Premier League z natywnymi IDs. Obserwacja ostatniego sezonu zakończyła się `2026-10-26T15:05:59.918386Z`.

| Split (według kickoff) | Sezon(y) | Realne mecze | Dopuszczone do ML |
|---|---|---:|---:|
| TRAIN | 2023/24 + 2024/25 | 760 | 0 |
| VALIDATION | 2025/26 | 380 | 0 |
| TEST — nietykalny holdout | 2026/27 | 380 | 0 |
| **SUMA** | 4 sezony | **1520** | **0** |

W bieżącym sezonie `2026/27` było 80 zakończonych i 300 nierozpoczętych spotkań. Historyczne wyniki pobrane dziś nie uzyskały fałszywego `prematch observed_at`: otrzymały `RETROSPECTIVE` i kwarantannę. Nadchodzący terminarz ma autentyczny czas obserwacji, ale **nie** ma zgody na traktowanie informacji o samym terminie jako kompletnego certyfikatu cech ELO/xG; również pozostaje w kwarantannie.

**Rzeczywisty zamrożony indeks:** [data/splits/STEP12_NATIVE_REAL_SPLIT_2026-10-26.json](../data/splits/STEP12_NATIVE_REAL_SPLIT_2026-10-26.json), niezmienny dla tej wersji danych.  
**Rzeczywisty audyt i SHA:** [STEP12_NATIVE_REAL_AUDIT_2026-10-26.json](../data/audits/STEP12_NATIVE_REAL_AUDIT_2026-10-26.json).  
**SHA256 manifestu:** `da387303645a9bb9476351044944e5465d178ddff689c96b579093c4fb4fce3a`.  
**SHA256 zaszyfrowanego źródła:** `70acaf4906bb1bc698e33d21f573afe11d588d20a9fe71fc039948b0ec91f299`.

## Trwała kopia dowodów i niezależny readback

Pakiet zawierający wyłącznie **RSA+AES zaszyfrowany materiał źródłowy**, podpisany manifest źródła, zamrożony split i audyt został przesłany do istniejącego folderu kopii zapasowych:

- [KB3_STEP12_REAL_PITCH_NATIVE_20261026.zip — Google Drive](https://drive.google.com/file/d/1j56rqRA8SnVYi1g65dbfwPaXHH96GzhB/view)
- [Raport niezależnego pobrania i kontroli SHA](../data/audits/STEP12_OFFSITE_CIPHERTEXT_READBACK_2026-10-26.json).

Pakiet pobrano ponownie z Google Drive (115 137 bajtów). Niezależny od GitHub Actions odczyt ZIP sprawdził sumy kontrolne 4 plików, zgodność ciphertext z manifestem szyfrowania, relację łańcucha dowodu do źródła, deterministyczny SHA manifestu i 1520 odrębnych IDs w poprawnym podziale — PASS. **Nie wykonano RSA decrypt/restore surowego źródła:** klucz prywatny właściciela pozostaje poza repo. Dlatego `offsite_ciphertext_readback_verified=true`, ale `independent_plaintext_restore_verified=false`. Nie wolno mieszać tych dwóch poziomów weryfikacji.

## Wynik GATE12 i następna praca

- Chronologiczne rozdzielenie: **PASS w rzeczywistym indeksie 1520/1520**.
- Identyfikatory, unikalność, integralność wersji splitu, brak przecieków w testach regresji: **PASS**.
- Zaszyfrowane źródło i niezależny odczyt kopii Drive: **PASS dla ciphertext**.
- Certyfikowane historyczne wejścia modelowe `TRAIN/VALIDATION/TEST`: **PENDING — 0 kwalifikujących się rekordów**.
- Finalny audyt realnego archiwum źródłowego przez niezależny restore plaintext oraz akceptacja właściciela przed trenowaniem: **PENDING**.

Nie odrzucamy sportowej użyteczności archiwum wyników; rozróżniamy prawdziwe wyniki od dowodu na historyczną dostępność każdego wejścia modelu. Brak certyfikowanych cech oznacza **brak uczciwego historycznego ML/kalibracji z tego manifestu**. Można rozwijać moduły technologiczne i dalej gromadzić prospektywne dane z timestampami, ale **nie deklarować gotowości treningu**.

**GATE12 PENDING • training_allowed=false • completed_steps=11/29.**
