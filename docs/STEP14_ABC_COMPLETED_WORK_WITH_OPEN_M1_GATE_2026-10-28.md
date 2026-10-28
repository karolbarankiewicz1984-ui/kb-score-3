# KB Score 3.0 — wykonanie A → B → C w kroku 14, 28.10.2026

**Czynności technicznie wykonane w kolejności A, potem B, potem C. Formalne zaliczenie oryginalnego kroku 14 nie jest możliwe — oryginalna pełna historyczna dostępność cech nadal nieudowodniona.**

## A — wszystkie pozostałe cechy poza xG

- [Scalony PR #74](https://github.com/karolbarankiewicz1984-ui/kb-score-3/pull/74), [GitHub Actions #40738870670](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40738870670) **SUCCESS, 6/6 testów**.
- Rzeczywisty audyt zamrożonego Step12: **760 TRAIN + 380 VALIDATION × (73 cechy nie-xG + 14 flag braku) = 99 180 skontrolowanych pól**. Cała macierz w skompresowanym `KB3_STEP14_A_REAL_1140_NOXG_FIELD_PIT_MATRIX` załączniku tego przebiegu Actions.
- Wynik nie upoważnia do fit: w oryginalnym SAFE manifeście **brakuje dokładnych historycznych cutoffów, pojedynczych autentycznych receiptów oryginalnych cech i potwierdzonej pełnej zgodności każdej obserwacji native team/fixture**. Niezależnie poświadczone starsze publiczne snapshoty dostarczają poszlak, ale nie oryginalnych 73 pól PitchAPI. **0/760 TRAIN i 0/380 VALIDATION ma kompletny PIT. Oficjalny wariant M1_BEZ_XG nie został wytrenowany**, aby nie naruszyć metodologii; istniejący oddzielny CatBoost OpenFootball pozostaje badawczy i retrospektywny.
- [Pełny audyt A](STEP14_A_73_NONXG_FULL_PIT_MATRIX_2026-10-28.md).

## B — prawdziwe porównanie xG tych samych meczów i drużyn

- [Scalony PR #75](https://github.com/karolbarankiewicz1984-ui/kb-score-3/pull/75), [Actions #40739852904](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40739852904) **SUCCESS**, 14 realnych zapytań do już skonfigurowanego PitchAPI GitHub secret, 20 testów offline.
- **380/380 historycznych meczów 2023/24 dokładnie zmapowanych** między PitchAPI i autentyczną FPL/Opta z oryginalnym home/away i kickoff; **6 meczów = 12 stron drużynowych** porównano numerycznie.
- PitchAPI strzałowe vs meczowe xG: **MAE 0,015, median 0,01, maksimum 0,06**. FPL/Opta player sum vs PitchAPI team xG: **MAE 0,0525, median 0,02, maksimum 0,24**. Prawdziwy feed ma zduplikowany klucz `expected_goals` w grupach `Expected goals (xG)` i `Top stats`, dlatego przyjęto ścisłą kontrolę zgodności obu.
- To jest dowód odtworzenia i pomiaru **dzisiejszej historycznej statystyki**, **nie** pierwotnego `PitchAPI first_published_at` dla lat 2023–2025 ani tożsamości modeli matematycznych obu dostawców. Nie wolno automatycznie podstawiać FPL xG zamiast oryginalnego PitchAPI.
- [Wyniki B](STEP14_B_REAL_PITCHAPI_FPL_6_GAMES_SEMANTIC_RESULTS_2026-10-28.md), [nieidentyfikujący JSON](../data/audits/STEP14_B_REAL_PITCHAPI_FPL_XG_EXACT_6_MATCHES_2026-10-28.json).

## C — rzeczywista automatyczna, dzienna archiwizacja

- [Scalony PR #76](https://github.com/karolbarankiewicz1984-ui/kb-score-3/pull/76). Pierwszy eksperyment [Actions #40740405701](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40740405701) **SUCCESS, 7/7 testów, realny RSA-public-key archive z 28.10.2026 17:56 UTC**. Po scaleniu **rzeczywisty automatyczny MAIN run [#40740578644](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40740578644) SUCCESS**, `2026-10-28T17:57:50.154451Z`, natywny zapis **4 przyszłych spotkań + 2 zakończonych predecessor shot/stats**, 6 rzeczywistych zapytań API. Encrypted data, manifest, source receipt committed to original main GitHub as `06bef12` — **zweryfikowano istnienie**.
- **Trwały rzeczywisty append-only zapis:**
  - [Dzienny bezpieczny receipt](../data/pit_sidecar/step14_pitchapi_native/2026-10-28/KB3_PITCH_NATIVE_ASOF_RECEIPT.json)
  - [Manifest zaszyfrowanego oryginału](../data/pit_sidecar/step14_pitchapi_native/2026-10-28/KB3_PITCH_NATIVE_ASOF.manifest.json)
  - `data/pit_sidecar/step14_pitchapi_native/2026-10-28/KB3_PITCH_NATIVE_ASOF.enc` — AES-GCM zaszyfrowane właścicielskim **publicznym** RSA, nigdy PEM prywatnym na GitHub.
- Workflow `.github/workflows/kb3-step14-c-native-asof-daily.yml` w `main` ma rzeczywisty cron **04:42 UTC codziennie**, bez właścicielskiej obsługi; limit **6 wywołań PitchAPI / dobę**, bez nowych tajnych danych, licencjonowanych uprawnień czy ręcznego klucza. Kolejne codzienne wykonania są harmonogramem, nie twierdzeniem o rezultatach z przyszłości.
- [Dokumentacja C](STEP14_C_DAILY_REAL_PITCHAPI_ASOF_ARCHIVE_2026-10-28.md).

## Ostateczna prawdziwa bramka oryginalnego M1

Nadal **13/29, GATE14 PENDING, oryginalny TRAIN PIT 0/760 i VALIDATION PIT 0/380**. A nie udowodniło pełnego no-xG PIT i **nie powstał oficjalny M1**, B nie odnalazło pierwszego historycznego czasu publikacji team xG PitchAPI, a C **dopiero od 28.10.2026** utrwala autentyczne nowe obserwacje. Zachowane M0, parametry Elo, zamrożone 20 prognoz, oryginalne podziały i TEST. Wszystkie faktyczne czynności A/B/C zapisane, użytkownik nie został poproszony o ponowne podanie API ani PEM.
