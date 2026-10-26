# KB Score 3.0 — Krok 12: DWA SPOSOBY HISTORII w walk-forward

**Data:** 2026-10-26. **Źródło:** zamrożony target-free terminarz PitchAPI 1520 meczów.  
**Uzgodniona zmiana metodyki:** porównanie historii rozszerzającej się (EXPANDING) oraz historii przesuwnej 24 miesięcy kalendarzowych (ROLLING).  
**Status:** porównanie granic czasowych i liczebności PASS. To nie jest jeszcze porównanie skuteczności predykcyjnej. `training_allowed=false`, GATE12 PENDING.

## Co dokładnie porównujemy?

Obie strategie wykorzystują te **same mecze walidacyjne** w 4 kwartalnych foldach sezonu 2025/26, a różnią się tylko okresem historii kandydatów do treningu. Nie trenujemy modeli, nie wyznaczamy prognoz ani trafności, dopóki odrębne bramki danych (cechy dostępne as-of, etykiety obserwowane w czasie, brak przecieku) nie zostaną spełnione.

| Kwartał VALIDATION | Czas startu walidacji UTC | EXPANDING: liczba spotkań wcześniej | ROLLING: ostatnie 2 lata | Wspólne spotkania VALIDATION |
|---|---|---:|---:|---:|
| VII–IX 2025 | 2025-07-01 | 760 | 760 | 60 |
| X–XII 2025 | 2025-10-01 | 820 | 753 | 126 |
| I–III 2026 | 2026-01-01 | 946 | 750 | 123 |
| IV–VI 2026 | 2026-04-01 | 1069 | 776 | 71 |
| **Łącznie** | | | | **380** |

**EXPANDING:** najstarszy możliwy mecz od 2023-07-01; kolejne poznane mecze dodawane dopiero przy rozpoczynaniu późniejszego folda.  
**ROLLING:** w każdym foldzie wyłącznie ostatnie 24 pełne miesiące kalendarzowe wstecz od momentu startu walidacji. Minimalne daty to kolejno 2023-07-01, 2023-10-01, 2024-01-01, 2024-04-01. Starsze mecze wypadają z okna.

W obu metodach mecz do kandydującej historii musi mieć kickoff i minimalne 3 godziny opóźnienia zakończenia **przed** początkiem folda. W praktycznym uczeniu to wciąż za mało: liczy się faktyczna, historycznie ustalona dostępność wyniku i każdej cechy modelu przed danym cutoff. Brak takiego dowodu = odrzucenie z treningu.

## Zakazy przecieku i uczciwa ocena

- Nie zamieniamy identyfikatora meczu, jego daty ani skrótów pochodzących od etykiet w fikcyjne predyktory. Modelowi przyszłości mogą służyć wyłącznie wcześniej zidentyfikowane wejścia, nigdy raport audytowy zawierający `source_record_sha256`.
- Ta sama walidacja musi być porównywana w obu strategiach: łącznie 380 meczów, brak nakładania się foldów i brak jakiegokolwiek spośród 380 spotkań TEST w zbiorach treningowych lub walidacyjnych.
- Docelowa kolejność metryk porównawczych to **wieloklasowy log loss** (główny), wieloklasowy **Brier** i kalibracja (pomocnicze). Dotyczą prognoz 1/X/2 po otrzymaniu niezależnie zatwierdzonych danych. Nie wykonano jeszcze żadnego porównania wyniku sportowego tych wariantów.
- Wybór długości historii tylko na podstawie VALIDATION. TEST jest końcowym zamrożonym egzaminem — żadnej zmiany parametrów po spojrzeniu na wynik TEST.

## Dowody technologiczne — rzeczywiste dane, bez płatnego API

- [Kod źródłowy `src/kb3_step12_windows.py`](../src/kb3_step12_windows.py): 2 metody, kwartalne granice UTC, restrykcyjne potwierdzenie SHA istniejącego bezpiecznego widoku.
- [Zamrożony nowy manifest porównawczy](../data/splits/STEP12_DUAL_WINDOWS_REAL_2026-10-26.json): zestawy ID dla wszystkich foldów i obu wariantów. SHA256 `25242ed4a626aba2669ea86605b31664cb17bf10a6a74e4e3548470954c81198`.
- [Niezależny realny audyt](../data/audits/STEP12_DUAL_WINDOWS_AUDIT_2026-10-26.json): liczebności i dowód braku wycieku TEST.
- [Offline CI PASS](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40353630051): testy negatywne obcych etykiet, zmienionego SHA, duplikatów, błędnych ról, niewłaściwej chronologii i freeze. 0 nowych zapytań do PitchAPI.
- Oryginalne `STEP12_NATIVE_REAL_SPLIT` i `STEP12_SAFE_MODEL_VIEW` oraz ich sumy kontrolne pozostają niezmienione.

**Formalny następny krok:** zaakceptować pełny finalny protokół dwóch wariantów walk-forward i zachować `GATE12` oddzielony od późniejszego dopuszczenia danych do rzeczywistego treningu. Rozpoczęcie KROKU 13 nie może sugerować, że niezatwierdzona historia jest autentycznym dawnym PIT.

**Krok12: metodologiczne testy PASS, formalnie GATE12 PENDING do zatwierdzenia; `training_allowed=false`.**

## 26.10.2026 — KOŃCOWY ODBIÓR METODYKI KROKU 12

**GATE12 PASS wyłącznie dla metodologii TRAIN/VALIDATION/TEST i porównania EXPANDING vs ROLLING.** [Samodzielny, zamrożony protokół odbioru](../data/audits/STEP12_METHOD_GATE_PASS_2026-10-26.json), rekord SHA `0332edf73cd893f9848ffb23ea7821a09f5c183e6add77fc7cfdd7378959c5be`. [Raport rzeczywistych blokad danych](../data/audits/STEP12_REAL_PIT_GAP_REPORT_2026-10-26.json): `1220` historycznych odczytów RETROSPECTIVE i `300` nadchodzących meczów z niezatwierdzonymi cechami; łącznie **0** dopuszczonych do treningu. Wcześniejsze wzmianki „PENDING” są zapisem stanu sprzed odbioru. Po potwierdzeniu przez użytkownika kontynuacji obu metod porównania i zaliczeniu testów programu protokół metody ma PASS, natomiast **`training_allowed=false`** i osobna bramka PIT pozostają w mocy. Krok 13 nie jest jeszcze rozpoczęty; dopasowywanie modeli, publikowanie prognoz lub fałszywe backtesty są zabronione.
