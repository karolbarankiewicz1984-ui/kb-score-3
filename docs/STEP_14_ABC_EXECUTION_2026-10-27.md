# KB Score 3.0 — krok 14: A+B+C bez złamania historycznego PIT (27.10.2026)

**Status: 13/29, krok 14 W REALIZACJI, GATE14 PENDING.** Jest to oddzielny program badawczo-dowodowy, bez zmian w M0, 20 zamrożonych prognozach, oryginalnym archiwum Step12 lub etykietach TEST. Nie zakupiono nowej usługi i nie zużyto odpłatnych odczytów PitchAPI.

## A. Historyczne migawki, pilotaż 40 TRAIN + 20 VALIDATION

Zamrożono [60 target-free identyfikatorów](../data/research/STEP14_PIT_PILOT_40_TRAIN_20_VALIDATION_2026-10-27.json), dobranych deterministycznie i równomiernie z chronologii oryginalnego [SAFE MODEL VIEW](../data/splits/STEP12_SAFE_MODEL_VIEW_2026-10-26.json): 20 z PL 2023/24, 20 z PL 2024/25, 20 z VALIDATION 2025/26. **Nie dołączono żadnych wyników, kursów, xG ani meczów TEST.**

Skrypt [`kb3_step14_archive_probe.py`](../src/kb3_step14_archive_probe.py) odpytuje wyłącznie bezpłatną publiczną historię commitów pliku sezonowego [OpenFootball](https://github.com/openfootball/football.json), ograniczając kandydatów do zapisów starszych niż **48 godzin przed kickoff**. GitHub Actions [#40487391948](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40487391948) **PASS**; wyniki:

| Sezon | Wybrane mecze | Co najmniej jeden wcześniejszy commit dla pliku sezonowego | Faktycznie certyfikowany snapshot konkretnego meczu |
| --- | ---: | ---: | ---: |
| 2023/24 TRAIN | 20 | **0** | **0** |
| 2024/25 TRAIN | 20 | **19** | **0** |
| 2025/26 VALIDATION | 20 | **20** | **0** |
| **Suma** | **60** | **39** | **0** |

**39 to liczba rekordów pilotażu z co najmniej jednym *kandydatem na commit*; nie liczba różnych commitów, nie potwierdzenie 39 poprawnych meczów.** Oryginalne snapshoty mogą nie zawierać właściwego meczu, a Git committer_date jest elementem metadanych commita, nie niezależnym dowodem momentu pierwszego publicznego udostępnienia. Brak również niezależnej, zweryfikowanej mapy tożsamości meczów OpenFootball ↔ PitchAPI. Konieczna weryfikacja zawartości historycznego bloba w wybranym SHA i jej rzeczywistej daty publikacji (np. niezależny archiwalny HTTP/Wayback receipt), plus dopasowanie nazwy drużyn/dat do autentycznych IDs PitchAPI. Do tego czasu **0/760 oficjalnych TRAIN legalnie dopuszczonych**.

## B. Rzeczywisty CatBoost badawczy — nie produkcyjny M1

Wykonano na CPU CatBoost 1.2.8 w niezależnym, nieprodukcyjnym skrypcie [`kb3_step14_public_research.py`](../src/kb3_step14_public_research.py). Źródło to otwarty zbiór OpenFootball (CC0), inny niż oryginalne archiwum PitchAPI; **nie wykonano walidowanego join na oryginalnych IDs**. Model wykorzystuje tylko pięć wartości: różnicę Elo z premią gospodarza, średnie punkty z maksymalnie pięciu poprzednich meczów dla każdej strony oraz rozmiary próbek tych średnich. Nie wykorzystuje xG, kursów, wyników przyszłych meczów ani TEST 2026/27. Każdy wcześniejszy wynik może wpłynąć na cechy dopiero po **trzech pełnych dniach kalendarzowych (ścisłe porównanie)**; jest to założenie rekonstrukcyjne, **nie dowód publikacji**.

**Podział:** 760 TRAIN (2023/24–2024/25), 380 chronologicznie późniejszych VALIDATION (2025/26), 0 TEST. Parametry wybrane przed oceną: seed `141027`, `iterations=150`, `depth=4`, `learning_rate=0.045`, `MultiClass`, CPU 1 wątek, bez strojenia na VALIDATION. Porównanie z nieruchomą referencją częstości klas policzoną tylko z TRAIN.

| Miara na 380 VALIDATION | CatBoost retrospektywny | Rozkład klas TRAIN (referencja) |
| --- | ---: | ---: |
| Accuracy 1X2 | **0.50000000** | 0.42631579 |
| Multiclass log loss | **1.03921945** | 1.08517423 |
| Brier sum3 | **0.62628833** | 0.65656163 |
| ECE top1 (10 koszyków) | **0.07793496** | 0.00789474 |

M1 uzyskał niższy log loss/Brier i wyższy odsetek trafnych klas względem *prostej referencji częstości*, ale **gorszą miarę ECE**. Nie jest to porównanie z produkcyjnym Elo+Poisson M0 ani udowodniona przewaga poza próbką w rzeczywistym PIT.

**Hash pliku badawczego `.cbm` (SHA256):** `21fe9199ca6efeef74a488e10ec8720b67ccd704a30ff502c078ff34169900ec`. Źródłowe SHA256:
- 2023/24: `03e13eafbf78dfe00d7e89dd3bf6643986eb6e8fd86c7664aeb8c5bc0bed88d0`
- 2024/25: `c3d18f552d83382cd4b6b21127adbbfe38e7f8618ddc979fb5404f2df07d0a75`
- 2025/26: `d6070bdf731546ccf97767f062e8af4bd26dd309dee69f6092025bf9c78f43c1`

[GitHub Actions #40487391948](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40487391948) wykonał **10/10 testów PASS**, faktyczny fit, ocenę i zapisał odrębny 14-dniowy artefakt `step14-nonproduction-research-only` z JSON raportów i plikiem `M1_RESEARCH_ONLY_NOT_PIT.cbm`. Archiwum tylko do badań; żadna kopia nie jest kandydatem do wdrożenia albo formalnego GATE14.

## C. Prospektywny publiczny rejestr pomocniczy

Zaimplementowano [`kb3_step14_public_sidecar.py`](../src/kb3_step14_public_sidecar.py) i [codzienny workflow](../.github/workflows/kb3-step14-public-schedule-sidecar.yml) (**05:35 UTC**), bez nowego zakupu i bez klucza płatnego dostawcy. Odczytywana jest jedna darmowa publiczna migawka terminarza 2026/27. Ekstrahowane są **wyłącznie wydarzenia zaplanowane na co najmniej trzy kolejne dni kalendarzowe**; wynik `score`, kursy, xG ani jakiekolwiek wyniki TEST nie są kopiowane do rejestru. Po zakończeniu odczytu zapisywany jest rzeczywisty `observed_at_utc`, SHA surowego pobrania oznaczony AUDIT-ONLY, hash całkowicie target-free projekcji i jednorazowy receipt SHA.

Ścieżka przyszłego trwałego zapisu: `data/pit_sidecar/step14_openfootball/YYYY-MM-DD.json`, wyłącznie nowy plik, nigdy overwrite, nieużywany jako cechy ani etykiety. Bot zapisuje go do prywatnej historii GitHub tylko z default branch; uruchomienia z gałęzi eksperymentalnych nie commitują archiwum. Testy negatywne potwierdzają zero score/odds w projekcji, UTC, niezmienność oraz brak dostępu do funkcji treningowej.

**Ten rejestr dotyczy tylko metadanych terminarza i nie jest certyfikacją kompletnego Elo, formy, xG ani identyfikatorów PitchAPI.** Jest drugim, kontrolnym źródłem, które **nie zastępuje PitchAPI jako głównego dostawcy**. Dane sezonu 2026/27 nie są przenoszone do TRAIN; zbiór TEST pozostaje odseparowany. Do przyszłych *pełnych* PIT wymagany jest zachowany przed kickoff odczyt **wszystkich** modelowanych cech i pochodzenia historycznych wyników z właściwego dostawcy.

## Oryginalny plan

Wynik A: kandydaci na odtworzenie, jeszcze bez PIT. Wynik B: badawczy CatBoost na realnych zakończonych meczach, lecz bez historycznych PIT receipts i bez dowodu zgodności z manifestem PitchAPI. Wynik C: przyszłe pomocnicze źródło terminarza z rzeczywistym zegarem odczytu, nie pełny trening. **GATE14 PENDING**; nadal 13/29; `training_allowed=false`, `production_approved=false`, M0 oraz 20 pierwotnych zamrożonych prognoz bez zmian.

Kolejne działania wewnątrz tego samego kroku: sprawdzić zawartość blobów z kandydackich commitów i weryfikację niezależnych czasów publicznego udostępnienia oraz poszukać dowodu historycznej tożsamości drużyn; rozwinąć oryginalny PitchAPI PIT zapis kompletu cech bez dotykania TEST; dopiero po odrębnej certyfikacji i legalnym TRAIN uruchomić formalny M1.
