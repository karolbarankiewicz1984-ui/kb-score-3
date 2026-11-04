# KB Score 3.0 — P1-01: wspólny as-of kontrakt TRAIN/FORWARD v2 (04.11.2026)

**Stan:** osobna nowa implementacja badawcza, bez zmiany dotychczasowego M0, M1-R, historii, prognoz lub regulaminu kwalifikacji FIT. Jej przejście w CI potwierdza semantykę kodu, **nie historyczną certyfikację PIT** ani dopuszczenie CatBoost do prognoz.

## Dlaczego nowa wersja?

W starym rekonstruowanym zbiorze M1-R używano stałego opóźnienia +48h od rozpoczęcia poprzedniego meczu i liczenia dni od poprzednika względem kickoff celu. Dotychczasowe cechy forward korzystały z czasu snapshot/cutoff, minimalnego opóźnienia +3h i liczenia dni względem chwili otrzymania danych. PR #149 zablokował przedwczesny awans, ale nie wyrównał reguł. Ten wariant nie nadpisuje dawnych wyuczonych 85 cech ani ich SHA — wprowadzamy odrębny identyfikator **kb3-p1-shared-train-forward-asof-v2**.

## Kod

- src/kb3_p1_shared_asof_features_v2.py: wspólny build_shared_features(purpose="TRAIN"|"FORWARD", ...) wywołuje **tę samą** istniejącą czystą agregację formy/Elo/xG Step11 (_compose_features). Purpose służy jedynie oznaczeniu zastosowania; zmiana TRAIN na FORWARD przy identycznych inputach i tym samym cutoff **nie może** zmieniać wektora, maski braków, lineagu, zegarów ani kanonicznego SHA.
- Jedyny zegar cech to **rzeczywisty UTC cutoff snapshotu**, wymagany co najmniej 90 minut przed kickoff celu. Poprzedni wynik 90-minutowy może być wykorzystany, jeżeli faktyczny dowód obserwacji/pobrania wyniku i receipt znajduje się **po kickoff poprzednika +3h i przed cutoff celu**, a rekord nie jest poprawiony po chwili archiwizacji. 48h jest **wyłącznie niegwarantującą historii heurystyką** i nie steruje dopuszczeniem w v2.
- xG i xGA mają **osobne** nieujemne wartości, hash dowodu oraz obserwowane zegary; brak lub późna obserwacja pozostaje **NULL i missing flag**, a nie sztucznym xG=0. Nie wolno użyć późniejszej obserwacji xG do retrospektywnego przypisania jej wcześniejszego czasu. Wartości źródłowe 0 są dopuszczalne tylko gdy mają rzeczywiste źródło.
- Źródło o klasie HISTORICAL_RECONSTRUCTED_NOT_ORIGINAL_PIT jest **odrzucane**, nie zostaje automatycznie dostosowane. Własny source_sha256 i deklarowany observed_at nie stanowią **niezależnego** potwierdzenia bajtów przez GitHub ani daty pierwszej publikacji dostawcy. W związku z tym **training_allowed=false, production_approved=false** w każdym wyniku nawet gdy przypadek przejdzie same walidacje semantyki.
- Nie wczytujemy etykiety meczu celu, zakazane są także przekazane wyniki celu, ENG Premier League 2026/27, duplikaty i przyszli poprzednicy, niespójność drużyn czy nieprawidłowe źródło. Wynik zawiera deterministyczny SHA, cały lineage, kompletną mapę obserwacji dla każdej wartości i jawne powody wykluczeń.
- compare_same_asof() porównuje bajty niezależnie od trybu i odmawia uznania różniących się par za jedną wersję treningową/forward.

## Oddzielne testy i kryteria

- tests/test_kb3_p1_shared_asof_features_v2.py: identyczny TRAIN/FORWARD, poprzednik poniżej 48h dopuszczony **tylko** przy faktycznie istniejącym wcześniejszym receipt, dni względem cutoff (nie kickoff), późno zapisane/za wcześnie obserwowane wyniki, późne xG, brak xG różny od 0, brak opublikowanego SHA, odmowa historii z późnej retrospekcji, wynik meczu celu, cutoff po 90-minutowym deadline, chroniony ENG, duplikaty, mutacja rezultatu po receipt, odmowa różnych cutoff oraz stabilność kolejności.
- .github/workflows/kb3-p1-shared-asof-v2-offline.yml: PR-only, Python 3.11 + 3.12, brak sekretów, bez API, bez fitu, regresja starego Step11, kontrola git diff danych, modeli i starych skryptów. Wynik prawdziwego CI musi być odczytany przed nadaniem PASS.
- Wersja v2 nie jest jeszcze adapterem do oryginalnego 85-kolumnowego, wytrenowanego M1-R. Nie podłączać go przez dowolną transformację. Trzeba osobno zbudować jawny mapujący kontrakt i przebudować/wytrenować **nowy** model, po niezależnym potwierdzeniu chronologii train/forward i danych źródłowych. Oryginalnych 720 TRAIN, 374 VALIDATION, zamkniętej Premier League TEST nie przemianowywać.

## Dalsza bramka

1. Odbiór CI nowego v2 i audyt wszystkich output fields na danych syntetycznych, plus kontrola że dotychczasowy M0 nie uległ zmianie.
2. Autentyczny materiał PIT (prematch cutoff, rzeczywiste źródła i bajty/hash sprzed cutoff) dla **tych samych** meczów train/forward. Gdy brak rzeczywistych wcześniejszych snapshotów historycznych, **nie certyfikować ich fikcyjnym 48h**, tylko oznaczyć jako reconstructed do ostrożnego research lub czekać na dane prospektywne.
3. Wersjonowane dopasowanie 85/nowych cech, obliczenie rzeczywistej ilości używalnych przypadków, kontrolowane TRAIN/CV w oddzielnym kandydacie (bez poruszania M0), potem sparowane prospektywne próby i Gate16/Gate17.
4. P1-01 = PARTIAL, #143 nadal DRAFT/NO-GO, #150 niezależny draft read-only audytu, M0 bez zmian, 100 FIT + 50 nowych HOLDOUT bez zmian, formalny plan 15/29.

**Brak automatycznego merge, wyboru Championa, zmian modeli produkcyjnych lub kodu starego M1-R.**

## Zgodność nazewnictwa z historycznymi 85 cechami M1-R

Dodatkowo zaimplementowano **candidate_m1r_85_schema_bridge()**, który odczytuje **rzeczywistą** listę frozen_feature_names z istniejącego audytu `data/audits/STEP14_M1R_BASE_CATBOOST_720_374_REAL_METRICS_2026-10-29.json` (720 TRAIN / 374 VALIDATION), wymaga 85 niepowtarzalnych nazw, zachowuje typy num/miss, rozróżnia brak numeryczny NULL i flagę missing oraz wylicza osobne SHA. To wyłącznie kontrola **kształtu** 85-kolumnowego wejścia. **Nie oznacza zgodności statystycznej ze starymi wagami** M1-R; źródła, czas odcięcia i dystrybucja cech się zmieniły, zatem trzeba wytrenować odrębny model z nowym SHA i nowym identyfikatorem. Dla każdej kandydackiej próbki pozostają `safe_to_score_with_frozen_original_m1r=false` i `training_allowed=false` do właściwych dowodów i decyzji.

## Rzeczywisty odbiór offline CI

- [GitHub Actions #41911645305](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/41911645305) — **SUCCESS**, obydwa joby Python **3.11** i **3.12**. W każdym z nich **17 nowych testów PASS** i **21 istniejących Step11 PASS**. Kontrole compileall, niezmienionych data/models/config oraz bazowych plików źródłowych także PASS.
- Przetestowany kod na source HEAD `4f7404c07193a6b91da8f730bb8780423e95b784`. W pierwszym przebiegu [#41911317531](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/41911317531) wychwycono dwie błędne asercje kierunku xGA w testach, poprawiono je i wykonano ponownie pełną regresję. Oryginalna logika Step11 i M0 nie była modyfikowana.
- Zewnętrzny dowód historii oryginalnych bajtów źródła, provider first-published i prawdziwa ilość adekwatnych TRAIN dla v2 nadal NIEPOZYSKANE. P1-01 ma status **PARTIAL / CODE-LEVEL PARITY TESTED**, nie pełny GATE PASS. Cały PR pozostaje **DRAFT** bez merge.
