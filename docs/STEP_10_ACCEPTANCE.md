# KB Score 3.0 — GATE 10 — PASS / ZALICZONO

**Data odbioru:** 26.10.2026 (Europe/Warsaw). **Zakres bramki:** historyczna spójność wyników i terminarzy, wykrywanie duplikatów, kontrola dat i faz oraz negatywne testy *no-lookahead*. **Ważne:** to PASS audytu źródeł i importu pilota, **nie** zgoda na trening ani twierdzenie, że wszystkie ligi lub ich statystyki są już w SQLite.

## 1. Dowody wykonania — rzeczywiste dane, odrębne workflow

| Sprawdzian | Rezultat i dowód |
|---|---|
| Pierwszy audyt SQLite Premier League 2024/25 | 380/380, 20 zespołów, 19 meczów u siebie i 19 na wyjeździe, 0 błędów krytycznych; [GitHub Actions #40278994874](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40278994874) |
| Kontrole negatywne i ochrony chronologii | 35/35 testów; 4/4 celowo uszkodzone kopie rzeczywistej bazy poprawnie odrzucone |
| Ponowna kontrola całego katalogu źródła | **5 lig × 6 sezonów = 30 kombinacji, 10 679 wpisów**, 0 krytycznych błędów źródła; [Actions #40280361413](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40280361413) |
| Rozstrzygnięcie 10 historycznych kombinacji z anomaliami | **10/10 sklasyfikowanych** według autentycznej rundy dostawcy; [Actions #40280931156](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40280931156) |
| Regresja końcowej wersji | **54/54 testy PASS** (35 Step10, 10 Step09, 9 Step08), dodatkowo wcześniej 4/4 negatywne mutacje SQLite |
| Trwałe manifesty, brak sekretów | [Manifest końcowy](../data/audits/STEP10_FINAL_2026-10-26.json), [pełny audyt 30 sezonów, prywatny Google Drive](https://drive.google.com/file/d/1duA2TFr00dggF0zCcOVLAHlF2RpJjJIH/view), [lista faz/wyjątków, prywatny Drive](https://drive.google.com/file/d/1Lu44F_j8fNugCIJICx12nJpxtkK4ZoEN/view) |

Zob. również [raport pierwszego audytu](STEP_10_PROGRESS.md), [skrypt weryfikacji 30 kombinacji](../scripts/step10_crossleague_qa.py), [skrypt szczegółowy faz](../scripts/step10_phase_resolution.py) i [reguły no-lookahead](../scripts/step10_quality_audit.py).

## 2. Liga × sezon — skąd wzięły się „nadmiarowe” mecze

Liczby w komórkach odnoszą się do **odpowiedzi źródła**, nie do rekordów faktycznie zaimportowanych do SQLite. Rok jest początkiem sezonu (2024 = 2024/25). Zapis `306 + 2` oznacza pełne 306 spotkań rundy zasadniczej i 2 dodatkowe baraże, które są zachowane w audycie, ale wyłączone z normalnych etykiet ligowych.

| Liga | 2021/22 | 2022/23 | 2023/24 | 2024/25 | 2025/26 | 2026/27 |
|---|---:|---:|---:|---:|---:|---:|
| Premier League | 380 | 380 | 380 | 380 | 380 | 380* |
| La Liga | 380 | 380 | 380 | 380 | 380 | 380* |
| Serie A | 380 | 380 + 1 | 380 | 380 | 380 | 380* |
| Bundesliga | 306 + 2 | 306 + 2 | 306 + 2 | 306 + 2 | 306 + 2 | 306* |
| Ligue 1 | 380 + 2 | 380 | 306 + 2 | 306 + 2 | 306 + 2† | 306* |

*Gwiazdka: sezon 2026/27 trwa, terminarz zawiera przyszłe mecze, więc żadnej z pięciu kombinacji nie uznajemy za zamkniętą historię wyników.*

†Ligue 1 2025/26: jeden mecz rundy zasadniczej ma stan `AWD` — **API-Football fixture ID 1388000**, a nie zwykły wynik 90-minutowy. Nie jest automatycznie uznawany za standardową etykietę do treningu. Wciąż zachowujemy go w pełnym terminarzu źródła, z informacją o kwarantannie.

**Wynik dla 25 zakończonych sezonów:** 8908 wpisów rundy zasadniczej, **8907 zwykłych wyników kandydackich** i **1 jawnie wyłączony wynik przyznany decyzją**; dodatkowo 19 meczów barażowych / rozstrzygających, które nie powinny zanieczyszczać modelu standardowej ligi. To liczby z pełnego źródłowego katalogu po klasyfikacji — **nie** informacja, że 8907 rekordów zaimportowano już do treningowej bazy.

Zidentyfikowano dokładnie źródła historycznych różnic: dodatkowe mecze o utrzymanie Bundesligi, baraże Ligue 1 i `Relegation Decider` Serie A 2022/23. W żadnym z tych przypadków nie kasowano rekordu ani nie wymuszano dopasowania identyfikatora.

## 3. Zasada bez przyszłej wiedzy

- Wynik końcowy meczu stanowi **etykietę** tego spotkania, nigdy własną cechę predykcyjną.
- Informacje z wcześniejszego meczu można wykorzystać w prognozie późniejszego spotkania **tylko gdy** istnieje dowód zakończenia meczu źródłowego, publikacji i faktycznej dostępności danych nie później niż `feature_cutoff` oraz jednoznaczne ID meczów.
- Jeśli publikacja/obserwacja nastąpiła po `feature_cutoff`, użycie jest **zablokowane**. Brak potwierdzenia dostępności także blokuje; opóźnienie źródła nie może zostać zignorowane.
- Testy obejmują celowo fałszywe: daty poza sezonem, powielone IDs, brak wyniku 90 min, anonimowe mecze, odwrócone chronologie, retrospektywnie oznaczone źródła jako prematch, wynik docelowego meczu w jego cechach i brak dowodu końca wcześniejszego spotkania.
- Błąd krytyczny → `FAIL`, rekord nierozstrzygnięty → **kwarantanna**, brak metryki → **NULL/BRAK, nie 0**. Zmiany nie nadpisują zamrożonych prognoz.

## 4. Czego GATE 10 *nie* zatwierdza

1. **Rzeczywisty trwały import SQLite nadal obejmuje tylko 380 spotkań Premier League 2024/25.** Pozostałe 29 kombinacji obejrzano w audycie źródła, bez dodawania pełnych historii do bazy.
2. W SQLite z pilota nie ma danych statystyk, zdarzeń, xG ani historycznych kursów. Sonda PitchAPI wykazała dostępność xG w próbkach na etapie 06, ale **nie** kompletność 8907 kandydatów. Brakujące statystyki nie są zerami.
3. **Nie ma zweryfikowanego archiwum przedmeczowych cech point-in-time.** Dla historycznych obserwacji pobranych dziś nie wolno po prostu założyć, że były dostępne przed dawnym meczem.
4. **`training_allowed = false`**, nie wykonano ML, nie wygenerowano nowych typów i nie uruchomiono raportowania produkcyjnego. Dalszy audyt konkretnego już zaimportowanego zbioru musi zachować reguły GATE10 także po rozszerzeniu bazy.
5. Co najmniej 1 wynik z `AWD` pozostaje na liście wyjątków; nie ma automatycznego „domyślenia” rezultatu ani promocji niezatwierdzonych par PitchAPI.

## 5. Decyzja o odbiorze

**GATE10 = PASS** w zakresie określonym planem: wykonano audyt jakości i chronologii wszystkich dotychczas zaimportowanych meczów, skontrolowano 30 kombinacji katalogu źródła, wyjaśniono nadmiarowe fazy, wyłączono wyjątek `AWD`, zaimplementowano negatywne testy lookahead, wygenerowano raporty per liga/sezon, a wszystkie krytyczne ryzyka blokują dopuszczenie do szkolenia modelu.

**Postęp projektu: 10/29.** Następny etap: **KROK 11 — cechy przedmeczowe** z rzeczywistymi datami dostępności, maskami braków, ostrożną integracją xG i chronologicznym rolling/ELO. **Bez nowych zakupów; bez modyfikacji KB Score 2.1, API Market i MultiModel.**
