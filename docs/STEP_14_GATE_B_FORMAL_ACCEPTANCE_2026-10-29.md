# KB Score 3.0 — odbiór kroku 14, wariant B (zmiana kryteriów)

**Decyzja właściciela: 29.10.2026.** Na wyraźne polecenie właściciela projektu („Wprowadź wariant b, zrób audyt i zamknijmy w końcu pkt 14”) **zmieniono wyłącznie kryteria formalnego odbioru KROKU 14**. Pozostałych 28 kroków, chronionego TEST, modelu M0, struktury oryginalnego M1 i dowodów źródłowych **nie zmieniono**.

**NOWY FORMALNY STATUS: KROK 14 — ZALICZONO wg GATE14-B; postęp 14/29.**

**Ważne:** historyczna, pierwotna bramka `GATE14_ORIGINAL_STRICT_NATIVE_PIT=PENDING` pozostaje jawnie **niespełniona**; przejście formalnego kroku 14 odbywa się **na podstawie jawnie zrewidowanych kryteriów**. Nazwanie jej `PASS` byłoby mylące, gdyż oryginalne pierwsze opublikowanie 121+38 wartości PitchAPI sprzed historycznych meczów nie zostało dowiedzione.

## Poprzednie i zmienione wymagania

| Aspekt | Pierwotna interpretacja / ograniczenie | Zatwierdzony wariant B, wersja 2026-10-29 |
|---|---|---|
| Przedmiot odbioru | Pierwszy CatBoost 1/X/2 z historycznych cech i pełnych oryginalnych PIT; oryginalny M1 | **Samodzielny wariant M1-R BASE, wyraźnie research**, faktycznie wytrenowany i oceniony, bez awansu do produkcji |
| Historyczne pochodzenie | Każde z oryginalnych 121+38 danych certyfikowane jako historyczne `as-of` PitchAPI | Retrospektywnie odtworzone **wyłącznie wyniki wcześniejszych meczów**, znany ich rzeczywisty kickoff, konserwatywne 48h; nie nazywać oryginalnym PIT |
| Braki cech | Oryginalny cały kontrakt PitchAPI wymaga udokumentowanych źródeł | Braki dopuszczone i jawne `null` + maska; 121 pól i 38 flag zachowanych w archiwum, **85 rzeczywistych aktywnych kolumn BASE bez xG** |
| Próg historii | Pełne źródła FORM5/10/15 i natywne xG | Min. **3 poprzednie mecze na klub**; reszta jako COLD_START, nie fikcyjny zero-xG |
| Trening i walidacja | Oryginalny rygorystyczny TRAIN=0 certyfikowanych, stąd fit zablokowany | Odrębny **720 TRAIN** (2023/24+2024/25) i **374 VALIDATION** (2025/26), w zamrożonym podziale 760/380 |
| TEST | W planie pierwotnym „metryki TEST”, ale pierwotnie TEST zablokowany do finalnej oceny | **Ocena odbiorowa na VALIDATION**; TEST Premier League 2026/27 pozostaje nietknięty i nie jest używany do treningu, wyboru parametrów ani tego odbioru |
| Bramki | Oryginalny `GATE14=PENDING` | **Nowa `GATE14_B=PASS` dla realizacji kroku 14**, stary certyfikat nadal `PENDING` i niedomniemany |
| Wdrożenie | Potencjalny oryginalny M1 po uzyskaniu dowodów | **Brak automatycznej promocji**; Champion M0 pozostaje bez zmian; wytrenowany M1-R jest tylko Challenger research |

Zrewidowany GATE14-B wymaga: (1) wyraźnej decyzji o zmianie zakresu; (2) 1140 oryginalnych tożsamości i niezmienionego splitu; (3) chronologicznego odcięcia 48h i obsługi braków; (4) izolowanego, odtwarzalnego treningu CatBoost 1/X/2 na REAL TRAIN; (5) zamrożonych prognoz VALIDATION bez użycia jej etykiet do fit; (6) potwierdzenia sumy prawdopodobieństw 1/X/2 = 1 i niezależnej metryki log loss, Brier/ECE/kalibracji klas; (7) kontroli SHA, powtórnego odczytu modelu, testów negatywnych i zakazu jakiejkolwiek promocji modelu; (8) zachowania pierwotnego stanu PIT i ochrony TEST.

## Wynik audytu niezależnego

**Przegląd #40916193143: SUCCESS, GATE14-B PASS**, 29.10.2026. Odrębny audyt [Python](../scripts/step14_gate_b_independent_final_audit.py) i [testy](../tests/test_step14_gate_b_independent_final_audit.py) wykonuje niezależnie od skryptu treningowego:

- 1140 **realnych** oryginalnych fixture IDs / trzy sezony, 4 rzeczywiste wywołania PitchAPI; kontroluje IDs, drużyny, kickoff UTC i zamrożony podział 760/380. Brak sezonu TEST w pobraniach.
- Porównuje SHA256 źródłowej [1140-meczowej macierzy](../data/audits/STEP14_M1R_RELAXED_1140_48H_121x38_RESEARCH_2026-10-29.jsonl.gz), [374 prognoz](../data/audits/STEP14_M1R_BASE_CATBOOST_374_FROZEN_PROBS_2026-10-29.jsonl.gz) oraz [prawdziwego pliku modelu CatBoost](../models/research/M1_R_BASE_CATBOOST_720_TRAIN_2026-10-29.cbm).
- Ponownie wczytuje oryginalny **.cbm**, 85 wybranych z TRAIN cech; **odtwarza wszystkie 374 predykcje 1/X/2** i ich sumowanie do 1. Zamrożone prognozy nie zawierają wyniku meczu.
- Niezależnie pobiera 374 właściwe wyniki, przelicza **log loss, Brier sum3 oraz /3, top1 accuracy, top1 ECE, 5 przedziałów kalibracyjnych oddzielnie dla 1/X/2** i porównuje liczby z uprzednio zapisanym raportem.
- Na nowo odtwarza TRAIN-only parametry M0 Poisson dla **tych samych 720 meczów** i sprawdza 374 prognozy kontrolne M0.
- Utrzymuje rozdzielność danych treningowych i walidacyjnych, jawne historyczne klasy `B_RECONSTRUCTED_PREDECESSORS` (nie dowody PIT), 48h symulację, brak xG BASE i TEST.
- Testy negatywne: odrzucanie nieznormalizowanego P(1/X/2), niewłaściwej liczby walidacyjnych meczów, jawne fail-closed; testy anty-przecieków z poprzednich etapów także przechodzą.

Wynik porównania 374 meczów:

| Metryka (realne 90 min, mniej lepiej poza accuracy) | CatBoost M1-R BASE | M0 z tym samym 720 TRAIN |
|---|---:|---:|
| Log loss | 1.0483520509 | **1.0351077037** |
| Brier sum3 | 0.6317111749 | **0.6202985149** |
| ECE 5-bin top1 | 0.0518897952 | **0.0235967153** |
| Trafność 1/X/2 | 0.4625668449 | **0.5000000000** |

**Odbiór techniczny PASS nie oznacza zwycięstwa modelu.** Eksperyment na prawdziwym TRAIN i odizolowanej VALIDATION spełnia **nowy, jawny cel badawczy**; CatBoost jest obecnie słabszy od M0, zatem **nie dopuszczać awansu produkcyjnego ani zmian pierwotnego Championa**.

## Dowody i decyzja

- [Rzeczywiste CI treningu i modelu z `main` — #40908796346](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40908796346), model SHA256 `07af285ff9dd45fa13dd54fd5e805270aff469434955cce998b601875f8fdab8`.
- [Niezależny CI audytu GATE14-B — #40916193143](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40916193143) (nowy test GATE14-B), [raport końcowego audytu](../data/audits/STEP14_GATE_B_INDEPENDENT_FINAL_ACCEPTANCE_2026-10-29.json).
- [Rekonstrukcja 1140 z oryginalnego PitchAPI #40906468219](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40906468219), [raport 720+374](STEP14_M1R_RELAXED_REAL_1140_720_TRAIN_374_VALIDATION_2026-10-29.md).
- [Wersjonowany eksperyment 720/374 i dokładna metodologia](STEP14_M1R_REAL_CATBOOST_720_TRAIN_374_VALIDATION_VS_M0_2026-10-29.md), [oryginalna propozycja łagodnych kryteriów](STEP14_PROPOSAL_M1_R_RELAXED_HISTORICAL_AND_FUTURE_ASOF_2026-10-29.md).

**Zatwierdzający zmianę kryteriów:** właściciel projektu w rozmowie 29.10.2026. **Wykonujący audyt:** odrębny, nieedytujący modelu kod + testy GitHub Actions na realnych danych. **Decyzja:** `GATE14_B=PASS`, **KROK 14 — ZALICZONO (wariant B)**, oficjalny licznik **14/29**. Stary pierwotny `GATE14_ORIGINAL_STRICT_NATIVE_PIT=PENDING` wciąż jest informacją o niedostępnej certyfikacji, a nie statusem otwartym kroku 14 po zmianie kryteriów. Historyczny audit trail nie jest usuwany, a zmiany są append-only.

**Następny formalny krok: 15 — Modele goli i spójność rynków (O/U, BTTS, team totals)**. Zanim modele pójdą do publikacji, wciąż obowiązują etapy kalibracji, Champion–Challenger i formalny odbiór stosownych późniejszych kroków, szczególnie 16–18 i 21–25. Nie ma nowych zakupów.
