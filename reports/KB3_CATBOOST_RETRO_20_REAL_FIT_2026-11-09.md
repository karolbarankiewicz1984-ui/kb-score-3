# Rzeczywisty eksperymentalny fit CatBoost — 09.11.2026

**Status: TRAINED_RETROSPECTIVE_RESEARCH_ONLY. Nie jest to 87-feature v3 i nie jest certyfikowany PIT.**

W lokalnym środowisku odczytano rzeczywisty SQLite `observations.sqlite` z GitHub Actions artifact `13635728620`, bez pobierania nowych danych od dostawcy. Z 4181 zakończonych obserwacji krajowych sprzed 01.06.2026 skonstruowano 3664 rekordy posiadające co najmniej pięć wcześniejszych meczów każdej drużyny (ta sama liga, ostatnie 5, poprzednik kickoff+3h <= hipotetyczny cutoff target kickoff−2h). Cechy: dla gospodarza i gościa średnia oraz odchylenie standardowe ostatnich pięciu goli zdobytych, straconych, punktów, a także dni od poprzednika; łącznie **20** zmiennych. Bez xG. To retrospektywna rekonstrukcja, a nie potwierdzenie czasu rzeczywistej publikacji danych.

Chronologiczny TRAIN: **2845** spotkań z kickoff <2026-03-01; siedmiodniowe embargo; VALIDATION: **747** od 2026-03-08. Pozostałe 72 rekordy w luce embargo. CatBoost 1.2.8, MultiClass, iterations180, depth3, learning rate .035, L2=8, seed20261109, CPU1. Brak dostrajania na validation.

| Metryka (747 wspólnych meczów) | CatBoost 20 | Baseline częstości TRAIN |
|---|---:|---:|
| Accuracy top1 | 0.4484605087 | 0.4457831325 |
| Brier sum3 | 0.6371830195 | 0.6466203766 |
| Log loss | 1.0556963741 | 1.0694435522 |

Wyniki accuracy per liga (N): BEL .4516 (93), ESP .5043 (115), FRA .4070 (86), GER .3614 (83), ITA .4434 (106), NED .4875 (80), POL .4063 (96), TUR .5114 (88).

Lokalnie utworzono prawdziwe binarium `CATBOOST_RETRO_20_FEATURES_NOT_PIT.cbm`, SHA256 `c0c85b5d19b0026ff65b341123c0b687a7f4737ee8ebbf36f01d1e35e5e3b64d`, i raport JSON. Model nie jest wdrożony do repozytoryjnego M0, nie służy do produkcji i nie posiada dowodów PIT. Nie ma uczciwego bezpośredniego porównania z M0 na identycznych walidacyjnych spotkaniach, a baseline to tylko rozkład częstości TRAIN. Nie wolno nazywać tego treningiem `KB3_CATBOOST_SHARED_ASOF_87_RESEARCH_V3`.

**Dalszy krok techniczny:** doprowadzić wspólny builder 87 cech do działania na osobnym, jawnie niecertyfikowanym, chronologicznym zbiorze historycznym, zachowując oddzielne etykiety i nie udając oryginalnego PIT; następnie rzeczywisty fit i walidacja 87 cech, a dopiero później prospektywny Shadow. Brak promocji Championa i zmiany TEST.
