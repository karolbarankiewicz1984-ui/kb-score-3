# KB Score 3.0 — audyt jakości nowych danych 1 XI 2026

**Wersja:** 1 | **Zakres:** dotychczasowe prognozy prospektywne M0 (75), 38 weryfikowalnych rozliczeń, 4 prognozy challengerów i natywne xG (8 par), bez odblokowywania chronionego TEST.
**Charakter:** niezależny odczyt istniejących artefaktów GitHub i rzeczywistych logów Actions. Brak ponownego pobrania danych z API, dostępu do zaszyfrowanych wierszy źródłowych albo nowego fit. Wniosek jakościowy jest zakresowy, nie stanowi formalnego GATE16 ani GATE17.

## Wynik i klasyfikacja

| Warstwa | Rzeczywisty dowód | Jakość i decyzja |
|---|---|---|
| Źródło M0, indeksy i czas | Oryginalny freeze 73 z 29 X; kolejny freeze 2 z 1 XI, te same 8 lig i jeden param SHA; 90-minutowa reguła przedmeczowa w SQLite/kodzie; archiwum zaszyfrowanego oryginalnego provider | **Technicznie poprawne — dopuszczać do dalszego gromadzenia.** Tylko prognozy po poświadczeniu hosta mogą przejść do FIT |
| Rozliczone M0 | 38/75, **38/38** ocenione przez kontrolę read-only z porównaniem zapisanego i niezależnie policzonego Brier i log loss (tolerancja <1e-9); **73/75** host-attested M0 | **Jakość spójności dobra; statystyka wstępna.** 2 nowe bez osobnego host proof i aktualnych wyników; nie liczyć do próby |
| Skuteczność nowych M0 | 38 unikalnych rozliczeń: trafność **21/38 = 55,26%**, Brier sum3 **0,5793652008982196**, log loss **0,9748187123592499**, ECE5 **0,12651272655552404** | **Wstępnie obiecujące, ale niestabilne.** ECE5 ok. 12,65 pp; 38 przypadków nie wystarczy do uzasadnienia kalibracji ani awansu |
| Porównanie trzech modeli | 4 challengery (ELO_ONLY/CATBOOST_NO_XG) na tych samych 2 nowych fixture; **0 host-attested challengers** w ostatnim offline read i **0 rozliczonych wspólnych trójek** | **BRAK DANYCH DO OCENY PORÓWNAWCZEJ.** Żadnych delta Brier/log loss nie można obecnie uczciwie podawać |
| Natywne xG | 8 par źródłowych, 7 zweryfikowanych semantycznie, 1 odrzucona `NATIVE_SHOT_VS_FULL_MATCH_XG_DISAGREE`, 0/74 pełnych last5 | **Dobre odrzucanie błędu, bardzo niska kompletność.** Niedopuszczone do treningu CatBoost-xG; first-published provider UTC nieznane |
| Historyczne 720/374 | 720 TRAIN, 374 VALIDATION, zachowany podział i 85 cech CatBoost; raport 374 realnych etykiet, lecz historyczne natywne PIT nieudowodnione | **Do analiz retrospektywnych, nie równoważne rygorystycznemu historycznemu PIT.** Nie mieszać z nowymi prognozami ani z chronionym TEST |

## M0 — przegląd po ligach na 38 kwalifikujących meczach

| Liga | Potwierdzony FIT-like n | Trafność 1X2 | Brier sum3 | Log loss |
|---|---:|---:|---:|---:|
| BEL | 5 | 60,0% | 0,55254 | 0,94004 |
| ESP | 5 | 80,0% | 0,47362 | 0,82336 |
| FRA | 4 | 75,0% | 0,51306 | 0,87235 |
| GER | 7 | 28,6% | 0,68030 | 1,11593 |
| ITA | 3 | 66,7% | 0,49608 | 0,85078 |
| NED | 4 | 75,0% | 0,52422 | 0,89893 |
| POL | 6 | 50,0% | 0,61837 | 1,03952 |
| TUR | 4 | 25,0% | 0,69385 | 1,13501 |
| **Razem** | **38** | **55,3%** | **0,57937** | **0,97482** |

Per-liga po 3–7 meczów nie upoważnia do kalibracji ligowej ani wyłączania lig. Zróżnicowanie formy może wynikać wyłącznie z losowości tej małej próby.

## Kontrole identyfikowalności i uczciwości

1. Zamrożone M0: `model_version=M0_ELO_POISSON_RESEARCH_720TRAIN_V1`, `params_sha256=55310f0e1dd3842e6d876069ef21b1380901b3a6cc6884cf6ec6ea351a5812d1` dla 29 X i 1 XI. Zmienia się liczba meczów, nie model.
2. `src/kb3_step16_m0_720_eight_forward.py` ma SQLite constraint `captured_at_utc < kickoff_utc-90m`; `src/kb3_step16_m0_720_calibration.py` (funkcja `eligible_settlements`) dodatkowo weryfikuje server-publication proof, hash treści prognozy i zgodność modelu, rozliczenie co najmniej +3h po kickoff, wyklucza duplikaty. Log audytu #41285923937 wykazuje 38/38 takich kwalifikacji.
3. `scripts/step16_m0_offline_readonly_audit.py` niezależnie przelicza Brier, log loss, trafność i ECE z zamrożonych wartości, nie zgadza się na `p=0`, `p=1`, NaN, brak sumy 1 ani odchylenie zapisanych score’ów >1e-9. **Run CI PASS**. Historyczne `forecast_sha256` i liczba 73 server proof są zachowane. Obecne 2 prognozy mają artefakt GitHub [#41285607283](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/41285607283), server-created **2026-11-01 07:39:52 UTC**, `artifact ID=13075720057`, ważny do **2026-12-01**, ale brak ich aktualnego formalnego `m0720_github_push_proofs`; **nie twierdzić, że już eligible**.
4. Nowe challengery mają potwierdzenie wspólnej tożsamości meczów i zamrożenia w tym samym czasie, lecz audyt [#41285923937](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/41285923937) wykazuje `total_challenger_forecast_rows=4`, `host_attested_challenger_rows=0`, `same_fixture_attested_settled_triplets=0`. Nie ma jeszcze skuteczności porównawczej.
5. xG przechodzi rygorystyczne sprawdzenie dwóch semantycznie zgodnych niezależnych endpointów; 1 niezgodność **odrzucona**, nie uzupełniana statystycznie. Rzeczywisty provider publication clock historyczny 2023–25 i kompletność xG last5 nie są zweryfikowane.
6. Przy kontroli struktury sezonów w 1 XI receipt historyczna NED/2025–26 ma **309** zakończonych pozycji, choć sezon 18-zespołowy standardowo ma 306 meczów regularnych: nie rozstrzyga to o błędzie (mogą występować mecze dodatkowe/play-off), ale przed korzystaniem z formy poprzednich meczów należy osobno dowieść `league_id` i dozwolonej struktury sezonu. BEL/2025–26 **313** pozycji również wymaga jawnej polityki rozgrywek dodatkowych, a nie automatycznego uznania za kompletność regularnego sezonu. Nie przerabiać w ciemno istniejących serii.
7. Raport 374 VALIDATION z badań historycznych wskazał **M0 Brier=0,62030 / log loss=1,03511 / 50%**, **CatBoost bez xG Brier=0,63171 / log loss=1,04835 / 46,3%**. To osobna próba historyczna z **niepełnym first-published PIT**, a nie dowód, że M0 jest lepszy na przyszłych ośmiu ligach.

## Decyzje

- **Dopuszczamy** dalsze automatyczne, niezmienione zbieranie M0, wyników i oryginalnych zaszyfrowanych źródeł, zapis ze świadectwem GitHub.
- **Nie dopuszczamy jeszcze** kalibracji, treningu xG, zwycięzcy Elo vs M0 vs CatBoost ani produkcyjnego awansu.
- Wykonać kolejny `settle` z rzeczywistą weryfikacją dwóch nowych M0 i ich czterech challengerów oraz ekspozycją `host proof=4/4`, dopiero gdy data i wynik meczu pozwalają na rozliczenie. Nie dopuszczać do licznika przedwcześnie.
- Dla natywnego xG: znaleźć poprawną semantykę dla 1/8 odrzuconych lub utrzymać kwarantannę, dozbierać rzeczywiste brakujące last5, a jednocześnie zachować twarde 33 requesty i odrębne zestawy PIT.
- Kontynuować do 100 unikalnych **zweryfikowanych** rozliczeń do FIT, następnie dopiero 50 świeżych HOLDOUT; potrzeba jeszcze **62 FIT-like** w aktualnym liczniku. Chroniony TEST 2026/27 nietknięty.

## Źródła audytu

- [Actions #41285923937 — niezależne aktualne 38/75 i potwierdzenie braku parowanych challengerów](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/41285923937).
- [Actual frozen M0 01.11 receipt](../data/pit_sidecar/m0_720_eight/2026-11-01/forecast/RECEIPT.json); [freeze M0 29.10](../data/pit_sidecar/m0_720_eight/2026-10-29/forecast/RECEIPT.json).
- [Actual xG 29.10 source receipt](../data/pit_sidecar/step17_native_xg_eight/2026-10-29/XG_READINESS_RECEIPT.json).
- [Historical research audit / independent 720/374](../data/audits/STEP14_GATE_B_INDEPENDENT_FINAL_ACCEPTANCE_2026-10-29.json).
- [Post-match 3-league 12 results, separately and not part of 38 unique eight-league sample](../data/pit_sidecar/m0_postmatch/2026-11-01/run-013026824188/M0_POSTMATCH_AND_CALIBRATION_REVIEW.json).

**Wniosek:** M0 jest **wystarczająco dobre technicznie do dalszego prospektywnego zbierania danych** i ma 38 audytowalnych przypadków; próba jest zbyt mała do ostatecznych stwierdzeń o dokładności i kalibracji. Challengery i natywne xG są wciąż **niekompletne do porównania/treningu**. Status formalny 15/29; GATE16/GATE17 PENDING.
