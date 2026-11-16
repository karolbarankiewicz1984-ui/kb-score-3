# Rejestr decyzji KB Score 3.0 — V3-R chronologiczna wersja badawcza (16.11.2026)

**Decyzja właściciela:** rozwijać drugą, równoległą wersję KB Score 3.0 bazującą na historycznych wynikach i statystykach odtworzonych chronologicznie. Zachować oryginalną V3 i rygorystyczne PIT. To **nie jest zgoda na obniżenie oryginalnych wymagań formalnych ani na promocję modelu produkcyjnego**.

## Zakres wdrożenia

1. Oddzielna nazwa eksperymentu: **V3-R_CHRONOLOGICAL_RECONSTRUCTION**, własny skrypt `scripts/kb3_v3r_walkforward.py`, własne raporty CI. Nie nazywać tej wersji oryginalną V3 121+38 ani 87-vector builderem.
2. Wejście: istniejące, rzeczywiste archiwum SQLite `observations.sqlite.gz` z przypiętym SHA256 i kontrolą odtworzenia. Źródło to historyczne obserwacje pobrane retrospektywnie w 2026 roku; **nie stanowi niezależnego dowodu ich publikacji przed ówczesnym meczem**. Zakaz nadpisania bazy danych.
3. Istniejący builder `scripts/kb3_p1_retro_catboost_1007_376.py` (nie kopiować kodu) odtwarza cechy wyłącznie z **zakończonych poprzednich meczów** przed hipotetycznym cutoff (kickoff minus 2 godziny), z wymaganym opóźnieniem dostępności wyniku poprzednika. Wynik meczu docelowego służy wyłącznie jako etykieta po wytworzeniu cech.
4. Osobne warianty CatBoost 1/X/2: **bez xG (14 cech)** oraz **z retrospektywnymi xG (18 cech)**; każdą brakującą statystykę zachować jako NaN, nigdy jako fikcyjne 0. Kontrola against Laplace train-only baseline. Nie interpretować historycznego xG jako certyfikowanego pre-match xG.
5. Dwa testy *expanding walk-forward* wyłącznie **wewnątrz istniejącego research TRAIN**: granice po 55% i 75% chronologii, siedmiodniowe embargo, grupowanie jednakowych godzin kickoff, zestawy walidacji rozłączne. Parametry CatBoost ustalone przed testem, bez strojenia na walidacji.
6. Po testach wewnętrznych wykonać **jedną oddzielną historyczną walidację** z istniejącego splitu research TRAIN/VALIDATION. Nie używać tej walidacji do fit w żadnym z wcześniejszych foldów. To nadal nie jest prospektywny HOLDOUT.
7. Raport z CI zawiera liczniki, wyniki log loss/Brier/top1, SHA danych wejściowych i modeli badawczych w lokalnych artefaktach. Do artifact przesyłać **tylko raporty agregatów**, a nie pliki źródłowe, surowe dane dostawcy i modele .cbm. Zależności przypięte; zero wywołań PitchAPI lub innych płatnych API.
8. Obowiązujące zakazy: bez dotykania oryginalnego Step14/PIT, 760/380, chronionego ENG 2026/27 TEST, aktywnego M0, oryginalnego modelu M1-R 720/374, kalibracji produkcyjnej, rejestrów prognoz i automatycznego wyboru Championa.

## Kryteria odbioru technicznego

- Testy odrzucają duplikaty, dołączanie oryginalnego VALIDATION lub ENG, niespełnienie 7-dniowego embargo, wspólne kickoffi po obu stronach granicy i zmianę wyników baseline przez etykiety walidacji.
- Raport ma dokładnie dwa niezależne okresy testowe, komplet mierników i dwie odrębne rodziny cech.
- Artefakt powstaje po zakończonym przetworzeniu **rzeczywistych istniejących danych** w GitHub Actions z niezmienną bazą źródeł, a nie tylko po kompilacji kodu.
- Utrzymać `GATE14_ORIGINAL_STRICT_NATIVE_PIT=PENDING`, `GATE16/17=PENDING`, `production_approved=false`, `official_fit_increment=0`. Wariant B kroku 14 nadal jest zaliczony według kryteriów badawczych — nie należy tego cofać ani mylić z oryginalnym PIT.

## Granice interpretacji wyników

Walka z przeciekiem etykiety i chronologiczny podział **nie rozwiązują** ryzyka późniejszej korekty historycznych statystyk (revision bias), braku daty pierwszej publikacji źródła ani driftu dostawcy. Współczynnik trafności z tego eksperymentu nie jest udokumentowaną skutecznością przyszłych zakładów, a porównanie z produkcyjnym M0 będzie wymagało **tych samych przyszłych spotkań i niezależnie zamrożonych prognoz obu modeli**.

## Dalsza kolejność

1. Zweryfikować zielony przebieg CI V3-R i zapisać rzeczywiste metryki, nie przewidywane.
2. Zdecydować o odrębnym, kontrolowanym generatorze nowych, niezależnie archiwizowanych przedmeczowych prognoz V3-R (tylko po sprawdzeniu zgodności cech train/forward). Nie dopuszczać historycznie wygenerowanych prognoz jako `forward`.
3. Na dopiero przyszłych, wspólnych meczach porównywać M0/V3-R i odchylenia kalibracji; bez automatycznej zmiany Championa. Do tego czasu decyzja **RESEARCH_ONLY**.
4. Oddzielnie prowadzić poszukiwanie historycznych źródeł PIT dla pierwotnej V3.

**Uruchamianie:** GitHub Actions `KB3 V3-R chronological reconstructed research (offline only)` — tylko pull_request lub świadome ręczne workflow_dispatch, bez dodatkowego cyklicznego obciążenia i bez nowego kosztu API.
