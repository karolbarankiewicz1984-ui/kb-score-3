# KB3 — 720 TRAIN: chronologiczne eksperymenty badawcze bez walidacji 374

1 XI 2026. Status: izolowany eksperyment, **bez zmiany M0, oryginalnego CatBoost, TEST oraz reguły 100+50**.

**Cel:** zbadać bez przecieku przyszłych wyników trzy z góry ustalone warianty CatBoost: oryginalne parametry, płytszy model regularizowany oraz wersję tylko Elo + FORM5. Źródło: istniejąca zamrożona macierz rekonstrukcji 1140 (48h, *nie* pełny dawny PIT). Program pobiera wyłącznie dwie sezony TRAIN 2023/24 i 2024/25 za maksymalnie 3 wywołania PitchAPI; nie pyta o 2025/26 VALIDATION ani 2026/27 TEST. Retrospektywne wyniki z 720 TRAIN są etykietami, a nie wejściami do cech przedmeczowych.

**Metoda:** 3 kolejne wewnętrzne chronologiczne okna: około 360→100, 480→100, 600→100; nierozdzielanie meczów o identycznym kickoff. W każdym fold wybieramy zmienne cechy wyłącznie z wcześniejszego TRAIN. Liczymy Brier sum3, log loss, trafność i ECE na następnej części dotychczasowego TRAIN. Żaden wynik walidacji 374 nie służy do strojenia. Raport agregatowy to badanie, nie licencja na automatyczną promocję.

**Brak xG:** wariant FORM5 korzysta z gole/formy/Elo, nie z alternatywnych FPL/Opta ani z niekompletnego PitchAPI xG. Zbieranie i ewidencja native xG w osobnym, istniejącym kolektorze są kontynuowane bez zmiany kosztu lub wersji modelu. Priorytetowy selektor PR #125 nadal osobny, nieaktywny w main.

**Wynik docelowy:** rzeczywisty raport GitHub Actions z 3 foldów w artefakcie, testy offline, archiwum zmian; bez oficjalnego GATE16 PASS/GATE17 PASS. Przygotować późniejszy porównawczy eksperyment na rzeczywiście zamrożonych nowych meczach, nie wielokrotnie oglądanej walidacji 374.
