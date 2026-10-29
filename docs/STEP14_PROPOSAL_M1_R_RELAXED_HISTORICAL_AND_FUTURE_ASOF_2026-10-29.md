# KB Score 3.0 — projekt metodologii M1-R: łagodniejsze historyczne dane i bezwzględna kontrola nowych prognoz

**Data:** 2026-10-29. **Status:** wersjonowana propozycja badawcza do oceny; nie zmienia oryginalnego CatBoost M1, kontraktu Step11, metodologii Elo/Poissona, wag, istniejącego GATE14 ani harmonogramu. Założenie użytkownika: nie próbować udowadniać historycznej daty publikacji każdej statystyki, gdy istnieją wcześniejsze wyniki, lecz zamrażać rzeczywiste dane dla wszystkich przyszłych prognoz.

## Dlaczego warto rozdzielić dwa kryteria

Poprzednie `GATE14` dopuszcza do oryginalnego M1 tylko kompletny zespół natywnych `121+38` wartości z poświadczonymi pierwotnymi czasami publikacji PitchAPI. To nadaje się do ścisłego audytu, ale nie do oceny, czy możliwe jest w ogóle nauczenie alternatywnego modelu na rekonstrukcji z wcześniejszych zdarzeń.

W obecnie zapisanej korekcie [FPL74 v2](STEP14_FPL74_HISTORIC_REAL_XG_CORRECTED_40_TRAIN_2026-10-29.md) istnieje 54/760 rygorystycznych historycznie poświadczonych FORM5 i 40/760 w pełni poświadczonych alternatywnych xG5 TRAIN; 109/380 FORM5 i 107/380 alternatywnych xG5 VALIDATION. Te liczby są **dotychczasowym ścisłym standardem**, a nie prognozą przyszłego pokrycia dla łagodniejszego standardu. Retrospektywny Elo 1140/1140 ma osobne oznaczenie, nie jest samodzielnym PIT.

Nowy **M1-R** (*Research / rekonstrukcja historyczna*) ma odrębny raport jakości i status. Oryginalne GATE14 pozostaje `PENDING`. Nigdy nie zmieniaj starego raportu na `PASS` tylko dlatego, że M1-R uzyska duży zbiór.

## R1. Minimalne twarde warunki HISTORYCZNEGO meczu

1. Dokładny, jednoznaczny ID meczu, liga, sezon, natywne ID obu drużyn, gospodarze/wyjazd, UTC rozpoczęcia, późniejszy wynik 90 minut wyłącznie jako **etykieta** poza wejściowymi cechami modelu. Oryginalny zamrożony podział: **TRAIN 2023/24 + 2024/25, 760; VALIDATION 2025/26, 380; TEST 2026/27, 380 — nadal chroniony**.
2. Wszystkie wejściowe poprzednie mecze mają **rzeczywisty kickoff co najmniej 48 godzin przed docelowym kickoffem**, prawdziwy wynik zakończonego meczu i dokładne przypisanie drużyny. To celowo konserwatywna wersja istniejącego okna `REPLAY_LAG=48h` w `src/kb3_features.py`. Nie korzystaj z żadnej cechy zależnej od docelowego wyniku lub z późniejszego meczu.
3. **Nie wymagamy** starego SHA/bezpośredniego `published_at` dla każdego wcześniejszego meczu, ani dawnego opublikowanego terminarza zawierającego przyszły target. Wynik wcześniejszego spotkania jest **obiektywnie wcześniejszym faktem**; można go odtworzyć ze współczesnego wiarygodnego archiwum, z oznaczeniem `RECONSTRUCTED_CHRONOLOGICAL`, ale nie wolno tego przedstawiać jako historyczny zapis źródła PIT. Weryfikuj daty, wyniki i tożsamość niezależnymi źródłami, gdy dostępne.
4. **Nie wymagamy 5/10/15 pełnych wcześniejszych meczów, wszystkich 121 pól ani xG.** Okna liczymy z tego, co mogło istnieć przed docelowym meczem: `n` jest liczbą prawdziwie dostępnych poprzedników, średnia jest `null`, gdy `n=0`. `0` nie jest równoważne `brak`. Dla xG zawsze oddzielnie przechowuj `source/provider`, `xg_n`, `missing_flag` i poziom wiarygodności.
5. Domyślna reguła jakości **do samodzielnej predykcji M1-R**: co najmniej **3 wcześniejsze zakończone mecze każdego klubu** (może być poprzedni sezon tej samej ligi); mniej oznaczamy `COLD_START/FALLBACK_M0`, bez usuwania rekordu z archiwum. To próg startowy do walidacji, nie stwierdzona empirycznie optymalna wartość.
6. **xG opcjonalny**. Średnia `xG5` może wystąpić jako **częściowa**, gdy dla ostatnich pięciu spotkań istnieją minimum **3 wiarygodne xG** tej samej zdefiniowanej metody; zapisuj `xg_n=3/4/5`, a przy mniej niż 3 `xg_avg=null` oraz `missing=true` dla wariantu M1-R. Nie nazywaj 3/5 `pełnym xG5`. Dla konkretnego meczu oba xG/xGA muszą odnosić się do tego samego spotkania i przeciwnika.
7. Odrzucaj: końcowe tabele i ranking sezonu liczone po docelowym meczu, końcowe średnie całego sezonu, dane skorygowane z wykorzystaniem przyszłych wyników, późniejsze lineup/statystyki docelowego meczu, odds post-kickoff, identyfikatory lub wyniki z chronionego TEST. Data „pobrano w 2026” nie wystarcza do oznaczenia jakiejkolwiek starej wartości jako bezsporny `HISTORIC_PIT`.

## R2. Historyczne źródła i poziomy dowodu

- `A_HISTORICAL_WITNESSED`: starsza wersja źródła z wiarygodnym zewnętrznym zegarem opublikowana przed targetem. Najwyższy priorytet.
- `B_RECONSTRUCTED_PREDECESSORS`: poprzednie **mecze i ich rezultaty** pewne chronologicznie, ale pobrane z archiwum później; ich wyniki nie mogą pochodzić z przyszłych zdarzeń docelowego meczu. Domyślnie można korzystać w odizolowanym M1-R.
- `C_RETROSPECTIVE_XG_UNCERTAIN`: wartości xG pozyskane z późniejszego zapisu wcześniejszego meczu, bez dowodu niezmienności definicji i historycznej publikacji; dopuszczalne wyłącznie do **oddzielnego testu wrażliwości xG** i porównań źródeł. Nie mieszaj ich domyślnie z wersją bez xG.
- `F_PROSPECTIVE_FROZEN`: przyszły mecz rzeczywiście obserwowany i zamrożony **przed prognozą i kickoffem**; wszystkie użyte źródła mają `observed_at_utc` i niezmienny SHA pliku/payload. To docelowy standard faktycznych prognoz.

**Bardzo ważne:** `FPL/Opta player-sum xG`, `Understat team-xG` i `PitchAPI team-xG` są trzema **odrębnymi definicjami** dopóki zgodność nie zostanie zmierzona. Nie zastępuj jednej drugą w oryginalnych kolumnach M1. Każdy wariant treningowy używa spójnej definicji po obu stronach TRAIN i VALIDATION, a następnie tej samej metody w przyszłej predykcji; inaczej uruchamiany jest wariant **bez xG**.

## R3. Minimalny zestaw dla PRZYSZŁEGO meczu, obowiązkowy przed prognozą

| Blok | Co trzeba znać i zapisać | Bez danych? |
| --- | --- | --- |
| Tożsamość | `provider_fixture_id`, liga/sezon, `home_team_id`, `away_team_id`, kickoff UTC, status `not_started` | **Nie generuj M1-R** |
| Czas | `forecast_created_at_utc`, `snapshot_captured_at_utc` i najpóźniejszy `feature_cutoff_utc`, wszystkie rzeczywiście wcześniejsze od prognozy i kickoffu | **Nie generuj M1-R** |
| Historia wyników | Źródłowe wyniki i daty wcześniejszych zakończonych meczów, **48h opóźnienia** dla spójności z TRAIN; min. 3 na klub do M1-R | Przy braku min. 3: `COLD_START/FALLBACK_M0` |
| Elo i forma | Elo obliczone wyłącznie z wcześniej dopuszczonych meczów; punkty, gole zdobyte/stracone, FORM5 i liczniki faktycznej liczby historii | Mniej niż 5: użyj częściowej historii i flag |
| xG/xGA | Jeżeli dostępne, zapis dostawcy/definicji dla poprzednich spotkań, `xg_n`, ostatnie xG5; tylko jedna zdefiniowana metoda w treningu i przyszłości | **Można prognozować bez xG** |
| Dowód | Nieprzetworzony snapshot i SHA256, `observed_at_utc` dla użytych danych, liczba braków i decyzja `M1_R/FALLBACK` | Bez dowodu: **nie generuj oficjalnej prognozy M1-R** |
| Status celu | W chwili zamrożenia **brak wyniku docelowego, brak danych live, mecz niezakończony**; przy przełożeniu meczu wykonaj nowy snapshot | Naruszenie: **wstrzymaj prognozę** |

**Tryby czasu:** wczesna prognoza `EARLY` (np. 24–72 h przed meczem) i późniejsza `NEAR` (np. 60–90 min przed) mają **oddzielne, zamrożone pliki**. Nie wymagamy od prognozy na jutro informacji dostępnych dopiero godzinę przed meczem. Obowiązuje reguła: wszystkie cechy obserwowane nie później niż moment opublikowania **danej** prognozy. Na początku można generować tylko EARLY; aktualizacja NEAR jest dodatkowym zadaniem. Niedostępna obsada, kontuzje, kursy lub skład nie są obowiązkowymi cechami tego wariantu.

## R4. Badanie jakości bez zmiany aktualnej produkcji

1. Zbuduj `M1-R-BASE` na **Elo + poprzednich wynikach + FORM z częściową historią, bez xG**. Zmierz rzeczywistą liczebność rekonstruowalnego TRAIN i VALIDATION, bez zgadywania. Pozostaw wszystkie 121+38 nazwy w archiwum, ale model może trenować tylko wybrane spójne cechy.
2. Osobno `M1-R-XG` tylko z wiarygodnym i metodologicznie spójnym źródłem xG. Oceń opcjonalną częściową `xg_n>=3/5` i wrażliwość na retrospektywne zmiany. Nigdy nie dopisuj sztucznego `xG=0`.
3. Zamroź **TRAIN 760** (bez VALIDATION w `fit`) i sprawdź w **VALIDATION 380** kolejno: log loss, Brier dla 1/X/2, kalibrację i skuteczność względem obecnego M0. Wykorzystuj wcześniejsze mecze z okresu VALIDATION jako historię kolejnych spotkań wyłącznie po ich rozegraniu i po 48 h; **nie używaj etykiet VALIDATION do trenowania**. Nie używaj TEST do strojenia ani wyboru modelu.
4. Porównaj liczebność, jakość kalibracji i wydajność wariantów; warunki decyzji i hiperparametry zamrozić przed ewaluacją TEST. Nie zastępuj M0/M1 i nie obiecuj poprawy trafności bez pomiarów.
5. Osobny nowy status `M1_R_RESEARCH_GATE` oznacza wyłącznie gotowość **eksperymentu**. Oryginalne `GATE14=PENDING` nie zostaje zmienione przez te zasady. Awans do produkcji wymaga odrębnej decyzji i udokumentowanej walidacji.

## Rejestr decyzji i następny faktyczny krok

**Propozycja do przyjęcia:** rozdzielone standardy dla historycznej rekonstrukcji i przyszłych migawek, minimalne 3 poprzednie mecze na drużynę, 48 h opóźnienie poprzedników, opcjonalne częściowe xG i osobny M1-R. **Te liczby są warunkami roboczymi do przetestowania, nie już zatwierdzoną decyzją o wymianie modelu.**

**Najbliższa implementacja badawcza:** wykorzystać istniejące 1140 oryginalnych ID i 3-sezonowy poprzednik Elo; zbudować funkcję, która dla każdego z 760 TRAIN/380 VALIDATION odtwarza liczniki wcześniejszych meczów pod regułą 48 h, oblicza częściowe FORM/Elo, dołącza oddzielne opcjonalne historyczne xG i wylicza rzeczywiste pokrycie nowego progu. Dopiero po audycie kodu i dowodzie braku przecieków uruchamiać nieprodukcyjny trening. Brak nowego płatnego API.
