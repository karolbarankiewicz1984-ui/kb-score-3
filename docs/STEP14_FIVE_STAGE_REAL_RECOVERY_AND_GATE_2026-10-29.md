# KB Score 3.0 — etap 14: pięć zadań wykonanych w zakresie dopuszczalnym przez prawdziwe dane

Data: 29.10.2026. Właściciel polecił wykonać kolejno (1) rekonstrukcję historycznych źródeł, (2) rozstrzygnięcie xG, (3) macierz danych, (4) realny trening CatBoost M1, (5) odbiór GATE14. **Nie wolno zaliczać kroków 4 i 5 bez kompletnego, naprawdę historycznego źródła 121+38.** Ani zmieniać automatycznie kontraktu kroku 14, ani odczytywać chronionego TEST.

## 1. Dane historyczne

Przeprowadzona ponowna kontrola ostatnich oryginalnych, już dopasowanych 1140 native spotkań i 13 wcześniej wiarygodnie datowanych publicznych źródeł. 760 TRAIN +380 VALIDATION, 106 przykładów **częściowej**, przedmeczowo dostępnej FORM5 (58+48+0, z czego 0 w 2025/26), ale **0 pełnych** oryginalnych native-PIT 121+38. Rozszerzony workflow rzeczywiście ponawia sprawdzenie 5 wskazanych SHA dawnego FPL (w tym 4 źródła 2025/26) przez GHArchive PushEvent i rzeczywiste oryginalne bajty. Wynik z wykonania publikowany jako `STEP14_2025_REAL_ARCHIVE_RECHECK_2026-10-29.json`. Jeśli dowód źródła odnaleziono, zwiększa to tylko **publiczne świadectwa** i nie dopuszcza automatycznie natywnej cechy PitchAPI.

## 2. xG

Dla PitchAPI w danych historycznych 2023–2025 brak `first_published_at` przypisanego do oryginalnego `fixture_id, team_id, period=All` oraz brak oryginalnej wersji archiwalnej statystyki w chwili przed meczem. 2023/24 FPL/Opta player-xG jest inną definicją wartości; nie zastępuje oryginalnego team-xG PitchAPI. **Z_XG oficjalnie BLOKOWANY**. **BEZ_XG oficjalnie BLOKOWANY** z innego powodu: 73 cechy i 14 flag non-xG też nie mają oryginalnych autentycznych historycznych receipts. Warianty pozostają oddzielnymi badaniami, bez zmiany oryginalnego modelu.

## 3. Macierz 1140 x 159

Nowy `scripts/step14_final_gate14_recheck.py` czyta *tylko* oryginalne `TRAIN/VALIDATION` z wcześniej zamrożonego SAFE splitu, oryginalny twardy `real_pit_gate`, źródłowy 1140-wierszowy audyt, zakres xG i prawdziwy wynik wznowionego 2025/26 harvest. Produkuje **1140 wierszy, 181260 komórek** (121 numeric +38 flag na mecz) w kompresowanym JSONL.gz, jawny raport i SHA. Brak dowodu jest oznaczany stanem `NO_ORIGINAL_NATIVE_PREMATCH_PUBLICATION_AND_CAPTURE_RECEIPT`, a nigdy 0 lub wymyślonym timestampem. Testy blokują zmianę podpisanego splitu, duplikaty, fałszywe uznanie dostępności i odczyt TEST. Kompresja nie jest szyfrowaniem.

## 4. Trening CatBoost M1

Zgodnie z oryginalną bramką TRAIN 0/760 i VALIDATION 0/380 są dopuszczone. Test wywołuje istniejącą funkcję odmowy treningu `check_real_fit_admission` i oczekuje `REAL_M1_FIT_DENIED_NO_CERTIFIED_PREMATCH_TRAIN`. **Realny oryginalny CatBoost M1 NIE został wytrenowany**, nie istnieją realne metryki M1 ani model do eksportu; byłoby niepoprawne ogłaszać tu sukces. Dotychczasowy syntetyczny demo-CatBoost oraz badawczy retrospektywny OpenFootball nie są zaliczane jako prawdziwy M1.

## 5. Odbiór GATE14

Automatyczne, odtwarzalne testy sprawdzają rozmiar macierzy, pierwotny hash SAFE, źródłowy lineage SHA, kontrolę PITS i odmowę treningu. Bramka formalna **GATE14=PENDING**, postęp **13/29**. Oryginalnego TRAIN/VALIDATION/TEST ani ustawień Elo/Poisson/SHADOW nie zmieniamy. Raport testów i macierz trafiają do artefaktu GitHub Actions, a po udanym przebiegu na `main` do prywatnego repozytorium. Sukces testu *odmowy niedopuszczonego treningu* nie oznacza sukcesu bramki modelu.

## Co dokładnie odblokuje krok 14

Albo uzyskanie autentycznych źródeł `as-of` i historycznych wersji zgodnych z oryginalnym kontraktem 121+38 dla TRAIN+VALIDATION, albo **jawna osobna decyzja właściciela o zmianie specyfikacji** z nową metodyką i nowym GATE. Ani brak dawnych xG, ani obecna liczba 106 nie pozwalają uznać oryginalnego CatBoost M1 za zatwierdzony.
