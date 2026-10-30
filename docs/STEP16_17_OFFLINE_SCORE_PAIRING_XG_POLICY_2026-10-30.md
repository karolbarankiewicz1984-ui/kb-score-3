# KB Score 3.0 — krok 16/17: kontrola punktacji, 100+50, porównanie lig i reguły xG

**Data:** 30.10.2026 (Europe/Warsaw). **Zakres:** statyczny audyt istniejących źródeł, niezależne wektory matematyczne offline oraz dodanie *odseparowanych, niewykonywanych automatycznie* kontraktów testowych. **Stan:** KROK 16 i GATE17 nadal PENDING, formalnie 15/29. **Nie wykonywano** zapytań PitchAPI, treningu, GitHub Actions, zmian prognoz ani zapisów w produkcyjnej/badawczej SQLite.

## 1. Ustalenia z odczytanego kodu

| Kontrola | Odczytane źródło | Wynik oceny / ograniczenie |
|---|---|---|
| Dokładna kolejność klas | `src/kb3_step14_m1_math_calibration.py::CLASSES`, `score_one` | Klasy `("1","X","2")`; istnieje kontrola sumy P=1. |
| Brier multiclass | `src/kb3_step14_m1_math_calibration.py::score_one`; `src/kb3_step17_engine_comparison.py::loss` | `sum_{c in 1,X,2}(p_c-y_c)^2`; bez dzielenia przez 3, zakres [0,2]. |
| Log loss | Te same funkcje | `-ln(max(p_wyniku, 1e-15))`, logarytm naturalny, średnia po unikatowych rozliczonych spotkaniach. |
| Rozliczenie 90-minutowe | `src/kb3_step16_m0_720_eight_forward.py::settle_sqlite` | `1` dla goli gospodarzy więcej, `X` dla równości, `2` dla przewagi gości; wymagany `finished`, zgodność match/team/kickoff, >=3h od kickoff, brak rozliczenia bez realnego wyniku. |
| Dobór 100+50 | `src/kb3_step16_m0_720_calibration.py::eligible_settlements`, `calibrate_if_eligible` | Tylko wersja M0/stały SHA parametrów i dowód hosta; pierwsze 100 według kickoff, temperatura dopasowana raz po tych wynikach; niezależne 50 musi mieć **zarówno** freeze, jak i kickoff po `fitted_at_utc`, i wynik obserwowany przed oceną. Bez automatycznej aktywacji. |
| Krok 17 | `src/kb3_step17_engine_comparison.py`, `src/kb3_step17_forward_challengers.py` | Istnieje parowanie po wspólnych fixture i bootstrap blokowy po tygodniach; dotychczasowy scorer zwraca pokrycie lig, ale nie kompletne **osobne sparowane metryki każdej ligi**. To uzupełnia osobny kontrakt offline, bez ingerencji w aktywny scorer. |

**Ważne rozróżnienie:** sprawdzenie implementacji i zgodność z wektorami syntetycznymi **nie dowodzą poprawności wszystkich rzeczywistych rozliczeń**. Do tego potrzebny jest przyszły read-only eksport źródłowych rozliczeń wraz z rzeczywistymi, niezależnymi dowodami GitHub. Nie wolno oznaczać rzeczywistego Brier/log loss jako PASS na podstawie zerowej próby.

### Wektory kontrolne wykonane niezależnie w Pythonie offline

Dla `P(1)=0,6, P(X)=0,3, P(2)=0,1`:

| Wynik 90 min | Brier sum3 | Log loss |
|---|---:|---:|
| 1 | 0,26 | 0,5108256238 |
| X | 0,86 | 1,2039728043 |
| 2 | 1,26 | 2,3025850930 |

Niezależne testy wyboru liczności w izolacji: 99 < 100 = brak fitu; 100 = próg fitu; 49 < 50 = brak review; 50 = próg review, **pod warunkiem** nowych prognoz po fit i poświadczenia w rzeczywistym archiwum. Te kontrole referencyjne wykonano poza repo i dały oczekiwane wartości. Pełnego nowego zestawu `unittest` w środowisku repo **nie uruchomiono**, bo wyczerpany limit GitHub Actions i brak prywatnego checkoutu w lokalnym środowisku. Nie twierdzić, że CI zaliczyło nowe testy.

## 2. Dodany niezależny kontrakt offline

- `src/kb3_step16_17_offline_controls.py`: funkcje read-only `score`, `outcome_from_90min`, `verify_settlements`, `calibration_100_50`, `compare_three_by_league`, `native_xg_last5`. Nie importują runnera ani nie zapisują baz/forecastów, nie pobierają API i nie wywołują `fit()`.
- `tests/test_step16_17_offline_controls.py`: nowe kontrolne przypadki dla Brier/log loss/wyniku 1X2, fałszywego hasha/poświadczenia danych przekazanego przez eksportera, poprawności liczb 99/100 i 49/50, rozdziału cutoff, wspólnej trójki M0/Elo/CatBoost oraz braków xG. Testy nie są podpięte do aktualnych harmonogramów.
- Jawny warunek integracji: w przyszłości read-only eksporter **musi sam zweryfikować** z oryginalnego historycznego artefaktu GitHub SHA prognozy i serwerowy czas przed kickoff. Samo ustawienie pola `host_attested=True` **nie stanowi dowodu**. Nie włączać automatycznie kalibracji ani nie używać tej biblioteki do zatwierdzenia produkcji.

## 3. Protokół porównania kroku 17

**Pierwszy etap (trzy silniki)**: `M0_ELO_POISSON_720TRAIN`, `ELO_ONLY`, `CATBOOST_NO_XG`. Wyłącznie osiem lig ESP, ITA, GER, FRA, NED, BEL, TUR, POL, mecz 90 minut, phase EARLY z >=90-minutowym wyprzedzeniem. Wspólny wynik może być użyty dopiero po ukończeniu meczu.

Wymagane są na **tym samym meczu**: identyczny ID providera i liga, wersja silnika niezmienna w całej kohorcie, identyczny źródłowy M0 forecast SHA, `feature_sha256`, `frozen_at_utc` i potwierdzony host-side dowód zamrożenia **każdego** silnika. Brak któregoś = brak wiersza w sparowanej trójce; nie wolno generować po czasie, korygować, dopasowywać, imputować lub tworzyć retrospektywnie brakujących Challengerów. Stare 73 M0 nie są sztucznie uzupełniane.

**Dla każdej ligi osobno** zapisywać: wszystkie kwalifikowane spotkania z M0, n trzech jednocześnie zamrożonych i rozliczonych, braki każdego silnika, średni Brier sum3, log loss, trafność top-1, delty Challenger − M0 policzone wyłącznie na wspólnych meczach, liczbę niezależnych tygodni oraz status niepewności. Dodatkowo suma ośmiu lig i braków. Nie deklarować przewagi z samej różnicy trafności albo z jednej ligi.

W istniejącym głównym scorerze krok 17 ma bootstrap parowany po całych ISO tygodniach, minimum osiem bloków; nowa kontrola ligowa **nie liczy sama przedziałów CI**, wyłącznie zgłasza gotowość do takiego obliczenia. Potrzebne są niezależne okna forward i ocena niepewności, a dobór Championa musi być osobną decyzją. `GATE16` nadal poprzedza `GATE17`.

## 4. CatBoost z xG — kompletność i braki

Oryginalny natywny PitchAPI xG (te same definicje `matches.shots[].expected_goals` i statystyka całego meczu `Expected goals (xG)`, tolerancja pary max 0,15) musi mieć dokładne ID meczu i obu drużyn. `observed_at` musi poprzedzać przyszły cutoff; brak znanej daty pierwszej publikacji providera nie może być nazywany udowodnionym historycznym PIT.

- Dla każdego przyszłego meczu wybiera się **faktycznych pięć ostatnich zakończonych poprzedników** gospodarzy i pięć gości; wybór musi nastąpić **przed** sprawdzaniem, dla ilu z nich mamy xG.
- Wymagane xG i xGA obu drużyn z każdego z tych dziesięciu pozycji (przy wspólnych przeciwnikach możliwe jest pokrywanie się identyfikatorów), ten sam provider i definicja, wartości weryfikowane i obserwowane przed cutoff.
- `0 xG` jest dopuszczalne tylko jako naprawdę zmierzona wartość 0; brak, odrzucona semantyka, zły team ID, zbyt późna obserwacja, brak wcześniejszych pięciu lub inny provider => `None` i **`xg_last5_complete=False`**, nigdy fikcyjne zero, wybiórczy backfill ani średnia z 2–4 dostępnych.
- Raportować po ligach liczbę `complete / missing`, powody braków, potencjalne przesunięcie populacji i koszt odrzucenia. Badanie kompletnego podzbioru nie jest automatycznym dowodem przewagi nad modelem bez xG. Maski braków w osobnym wariancie przyszłego modelu wymagają jawnej bramki/metodologii, nie zmian w starym CatBoost.
- Stan źródłowy 29.10.2026: **7/8** pobranych par semantycznie poprawnych; jedna odrzucona ze względu na różnicę shots vs team stats; **0/74** przyszłych celów miało obie pełne formy last5. `CATBOOST_WITH_XG=NOT_TRAINED`. Historyczna alternatywa FPL/Opta 40/760 TRAIN i 107/380 VAL nie jest natywnym PitchAPI i nie daje uprawnień do użycia historycznego xG jako as-of.

**Bramka xG:** brak certyfikowanych 720 TRAIN / 374 VAL w oryginalnym natywnym xG; dopuszczalna będzie wyłącznie odpowiednio duża, odseparowana przyszła kohorta z archiwizacją prematch źródeł, maskami braków opracowanymi przed treningiem, chronologicznym podziałem i niezależną walidacją. Żadnego treningu z xG ani generowania jego prawdopodobieństw teraz.

## 5. Odbiór i ryzyka

**Wykonano:** niezależne wektory offline arytmetyki, analizę istniejącego kodu, zapis kontraktu i testów syntetycznych oraz reguł bramek. **Nie wykonano:** GitHub CI nowych testów, rzeczywistych rozliczeń (ostatnio 0), nowego fitu temperatury, treningu xG, serwerowego eksportu zamrożonych 73 pozycji do nowych testów, zmian workflow, prognoz albo parametrów. `PASS` dotyczy wyłącznie arytmetycznych wektorów kontrolnych; status pełnej weryfikacji rzeczywistych danych: **PENDING**.

Następny odbiór po dostępności runnerów: uruchomić nowy unittest offline, wykonać read-only eksport poświadczonych rozliczeń, sprawdzić odchylenia 1X2/Brier/log loss, a gdy jest wspólna rzeczywista próbka nowych M0/Elo/CatBoost — zbudować raport ligowy i parowane CI. Aktualne `GATE16=PENDING`, `GATE17=PENDING`, **15/29**.
