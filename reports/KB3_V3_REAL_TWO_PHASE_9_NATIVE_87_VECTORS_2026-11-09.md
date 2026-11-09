# KB Score 3.0 — dwufazowy prawdziwy zapis i oryginalny builder v3 — 9 listopada 2026

## Decyzja

**SOURCE_ARCHIVE_BEFORE_EXACT_CUTOFF = PASS. ORIGINAL_VERIFIED_VIEW_87 = PASS (9/9). RESEARCH ONLY.**

To jest zakończony **rzeczywisty** eksperyment na nowo pobranych odpowiedziach PitchAPI; nie symulacja i nie wstecznie przebudowany historyczny dataset.

- Realny workflow na **main**: [GitHub Actions run 42594056216](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/42594056216), wszystkie trzy joby **success** (offline safety tests, source-archive, verified-v3-freeze). Workflow `.github/workflows/kb3-v3-native-two-phase.yml`, wdrożony przez PR #169 i poprawiony przez PR #170.
- Pinned i odtwarzalny kod badawczy `scripts/kb3_v3_native_two_phase.py` w commicie `0310159b2c37760039ac69c0b2b96ad92af2e45b`. To on wywołuje **oryginalne** `src.kb3_catboost_research_v3.verified_view` i `vector`, a nie rekonstrukcję 87 pól z osobnego eksperymentu.
- Źródłowe **6 serializowanych natywnych odpowiedzi SDK PitchAPI**: 3 ligi ESP/ITA/GER × 2 sezony (2025/26, 2026/27), do 7 istniejących wywołań API, bez nowej licencji. Zapis wejść jest tworzony w tej samej fazie A.
- GitHub-hosted **source artifact ID 13661918237**, name `KB3_V3_NATIVE_PREMATCH_SOURCE_42594056216`, **created_at 2026-11-09T09:31:34Z**. Odczytana niezależnie od zegara programu kontrola SHA-256 całego ZIP = **784a4877479cf2513c131496b5894012da4c004d67420f81a23126827bc41ed6**, zgodna z GitHub API.
- Planowany i utrzymany **feature cutoff = 2026-11-09T09:37:33.400068Z**; rzeczywiste archiwum istniało na serwerze GitHub **359.400068 sekundy PRZED cutoff**. Żadnej manipulacji starymi zegarami, nie archiwizowano go po cutoff.
- W etapie B sprawdzono raw member SHA, obecność/identity i scores każdego wcześniejszego spotkania oraz wszystkie źródłowe zegary; niezależny audyt przez skrypt kontrolny w tej sesji wykazał **4 128/4 128** pasujących wierszy historycznych.
- **9/9** nowych realnych, zarchiwizowanych wektorów × **87/87** oryginalnie wyliczonych cech = **783 pola**, w podziale ESP 3 / ITA 3 / GER 3. Wejścia dotyczą spotkań z **20–21 listopada 2026**.
- **original builder validated_at**: `2026-11-09T09:37:33.400727Z`, czyli faktycznie po cutoff; teraz/po zakończeniu archiwum, a nie przed.
- **Output artifact ID 13662304326**, name `KB3_V3_87_NATIVE_RESEARCH_CANDIDATES_42594056216`, **created_at 2026-11-09T09:37:37Z**, ZIP SHA256 `84fee2093343ea184006e61b7bc696357aca62ebc7d450b9db2a88c972f59c8f`. Wewnątrz `KB3_V3_PREMATCH_87_NATIVE_INPUTS.json`, schema `kb3-v3-frozen-native-input-verified-no-model-fit-v1`. Jego kanoniczny raport SHA jest sprawdzony. W output NIE ma prognozy ani wyniku meczu.

## Istotne rozróżnienia

- To dowodzi autentycznej **obserwacji danych w archiwum hostowanym przed konkretnym cutoff**, a NIE historycznej daty pierwszej publikacji źródła przez PitchAPI.
- **Formal v3 TRAIN admitted: 0** (brak nowych etykiet tych przyszłych spotkań; builder research `training_allowed=false`). **Official trained v3 CatBoost: 0. Forward model predictions: 0.**
- Na tym etapie dostępny jest **wiarygodny strumień kandydackich danych dla dalszego uczenia i testów Shadow**, nie automatyczne zastąpienie M0 czy nowy model o potwierdzonej skuteczności.
- Przez przerwy ligowe rozszerzono horyzont wykrywania terminarza do **28 dni**. W dni bez docelowych meczów źródłowe archiwum 6 odpowiedzi nadal zostanie zachowane, bez dopisywania fikcyjnych forecastów.
- Workflow na `main` ma plan codziennie **05:10 UTC**, maksymalnie 7 dodatkowych wywołań bieżącego PitchAPI/dzień i **90 dni retencji** archiwów GitHub Actions (o ile ustawienia repo na to pozwalają). Kolejne rekordy tego samego meczu muszą być deduplikowane przed fit/validation; nie wolno traktować powtarzających się snapshotów jednego fixture jako niezależnych meczów.
- **M0/Champion/TEST bez zmian**, brak operacji na ich bazach, brak płatnych dodatkowych subskrypcji.

## Techniczne dowody

- [Działający realny run](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/42594056216)
- [PR #169 — aktywacja](https://github.com/karolbarankiewicz1984-ui/kb-score-3/pull/169)
- [PR #170 — horyzont + puste dni](https://github.com/karolbarankiewicz1984-ui/kb-score-3/pull/170)
- [Offline parity tests, Python 3.11/3.12](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/42593856611)

**Następny logiczny etap:** automatyczne przypięcie etykiet meczów po zakończeniu, host-attested settlement i chronologiczny FIT/HOLDOUT po deduplikacji. Nie nazywać 9 wejść zakończonym treningiem.
