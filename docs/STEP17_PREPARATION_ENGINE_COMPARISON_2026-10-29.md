# KB Score 3.0 — Krok 17: start porównania silników (przygotowanie badawcze)
**29.10.2026 | STATUS: W REALIZACJI — FAZA PRZYGOTOWAWCZA | GATE17 PENDING (zależność GATE16) | formalnie 15/29**

## Zgodność z pierwotnym 29-punktowym planem
Krok 17 wymaga porównania: ELO, ELO + Poisson, CatBoost bez xG, CatBoost z xG i ewentualnego ensemble. Bramka: **wspólne mecze i rynki, identyczny horyzont przedmeczowy, przedziały niepewności, koszt brakujących danych i brak wyboru zwycięzcy na podstawie pojedynczej serii**. Formalnie zależy od kroku 16, który nadal oczekuje na dopuszczone wyniki forward 100+50. Wykonujemy techniczną część kroku 17 już teraz, bez awansu i bez użycia chronionego Premier League TEST 2026/27.

## Stan silników — odrębne etapy i uczciwe liczby

| Silnik | Istniejący dowód | Ograniczenie |
|---|---|---|
| ELO-only | Elo jako cecha i komponent M0 | Oddzielna, zamrożona prognoza ELO-only 1X2 na identycznych meczach jeszcze nie istnieje; nie wolno wymyślić metryk |
| M0 Elo + Poisson 720 TRAIN | Dokładny kandydat 720 TRAIN; na 374 historycznych VAL: **Brier sum3 0,62029851**, **log loss 1,03510770**; na ośmiu ligach forward 73/73 oryginalnych SHA potwierdzonych przez GitHub Actions, zero realnych settled na dzień startu | Domena walidacji historyczna Premier League, badanie wejść B-reconstructed; brak dowodu wyniku wieloligowego forward |
| CatBoost bez xG (M1-R) | Ten sam historical VAL 374: **Brier sum3 0,63171117**, **log loss 1,04835205**, 85 cech, rzeczywiście wytrenowany na 720 TRAIN | Brak ośmioligowego forward na tych samych grach; źródło historyczne nie jest certyfikowanym natywnym PIT |
| CatBoost z xG | Są badania źródeł i semantyki xG, a w kroku 15 dwa modele bramek *bez* xG | Nie mamy jeszcze niezależnego rzetelnego modelu z xG z uczciwie zamrożonymi analogicznymi predykcjami, więc na ten moment brak metryk |
| Ensemble | Na etapie konstrukcji reguł | Wagi muszą pochodzić z TRAIN albo z przyszłego oddzielnego okna, **nie mogą być dopasowane do 374 VALIDATION ani do testu** |

Wynik dwóch historycznych silników jest przytoczony ze źródłowego [audytu M1-R vs M0](../data/audits/STEP14_M1R_BASE_CATBOOST_720_374_REAL_METRICS_2026-10-29.json) oraz [kroku 15](../data/audits/STEP15_ML_VS_M0_374_FULL_REPORT_20261029.json). Różnica ML minus M0: Brier **+0,01141266** i log loss **+0,01324435**, niższe jest lepsze. Z tych liczb **nie powstają nowe prognozy ani niezależny test po korektach**. W tej wersji kroku 17 NIE liczymy ponownie CI na podsumowaniach historycznych bez niezależnych wspólnych wierszy.

## Nowe narzędzia i algorytm porównania
- [src/kb3_step17_engine_comparison.py](../src/kb3_step17_engine_comparison.py): czysty, odtwarzalny scorer dla 5 silników. Przyjmuje jawne, wystandaryzowane rekordy prognoz i wyniku, **ten sam mecz, rynek 1X2-90min, horyzont EARLY >=90 min**, stały model/version i sprawdzony czas. Oba silniki w parze punktowane tylko na przecięciu identycznych fixture ID. Nie dolicza meczów, na które jeden silnik niczego nie zamroził.
- Raportuje liczbę i procent brakujących prognoz dla każdego silnika oraz ilość wspólnych meczów dla każdej pary i wszystkich pięciu. Nie imputuje brakującego xG ani nie zakłada, że model z brakami byłby równie skuteczny na odrzuconych spotkaniach.
- Dla dopuszczonych wierszy liczy **log loss, Brier sum3, accuracy i top-1 ECE**. Różnice i **bootstrap parowany po tygodniach ISO** oblicza na tych samych spotkaniach (z ustalonym seed), a nie na niezależnie losowanych meczach. Przy mniej niż ośmiu niezależnych tygodniach zamiast fikcyjnego CI zwraca `INSUFFICIENT_INDEPENDENT_WEEKS`. Interwały są opisowymi statystykami, nie automatycznym wyborem Championa.
- `FORWARD_GITHUB_HOST_ATTESTED` przyjmuje wyłącznie dane **wcześniej niezależnie poświadczone** przez audyt GitHub; sam scorer sprawdza wymagany zapis w rekordzie, ale **nie jest źródłem zaufania**. Eksport do scorer musi wiązać się z utrwalonym upstream dowodem SHA i host timestamp. `HISTORICAL_RECONSTRUCTED_RESEARCH` jawnie oznacza odmienną klasę źródeł, nie scala ją z rzeczywistym forward.
- [scripts/step17_preflight_engine_readiness.py](../scripts/step17_preflight_engine_readiness.py) odczytuje **istniejące** oryginalne raporty 720/374 oraz źródłowy wynik 73/0 i tworzy powtarzalny, niezmienny raport [data/audits/STEP17_PREP_ENGINE_COMPARISON_2026-10-29.json](../data/audits/STEP17_PREP_ENGINE_COMPARISON_2026-10-29.json) (po successful main workflow). Nie odpytuje PitchAPI ani nie czyta chronionego 2026/27 TEST.
- [tests/test_step17_engine_comparison.py](../tests/test_step17_engine_comparison.py) i [workflow](../.github/workflows/kb3-step17-engine-preparation.yml): kontrola braków, niezmiennych SHA, pary, late-freeze, niecertyfikowanego forward, rozdzielenia domen, braków tygodni oraz braku autoawansu, bez kosztu API.

## Kolejność dalszej implementacji
1. **Zacząć od źródłowych, zamrożonych przyszłych 1X2** tego samego zestawu spotkań i stworzyć osobny ELO-only forward z wersją parametrów i źródłową tożsamością, bez fit na tych wynikach.
2. **Dodać CatBoost bez xG** jako challenger w osobnym kontenerze/prognozie na te same identyfikatory. Model wytrenowany na historycznej Premier League może mieć problem z transferem do innych lig, należy ocenić osobno każdą ligę.
3. **Dopiero po audycie xG i modelu z xG** dopuszczać `CATBOOST_WITH_XG` do porównania. Testować brak danych i ich koszt na wspólnym zbiorze, a nie wypełniać historycznego xG z przyszłości.
4. **Ensemble** dopiero z uprzednio zamrożonymi wagami i spójnymi wersjami składników. Bez uczenia wag na sealed TEST lub 374 VAL.
5. Formalne GATE17 dopiero po GATE16, wynikach forward na tej samej populacji, rynkach i horyzontach, uczciwej niepewności i sprawdzeniu stabilności na oddzielnych oknach. Dane z historycznego 374 to jedynie punkt odniesienia, nie ostateczna decyzja Champion.

**Bez zakupu dodatkowego API, bez zmian kalibratora M0 720 TRAIN, bez automatycznego awansu i bez cofania 15/29.**
