# KB Score 3.0 — 02.11.2026 — przyspieszenie bez nowych żądań API

**Decyzja:** monitorowanie M0 i porównywanie challengerów każdego dnia, zamiast cotygodniowego wywołania. Nie zmieniamy M0, cech, żadnych prognoz, formatu próbki, PIT, budżetu PitchAPI ani 100 FIT + 50 nowych HOLDOUT.

## Kod i działania
- `.github/workflows/kb3-step16-progressive-shadow.yml`: zastąpienie tygodniowego harmonogramu raportem codziennym 23:49 UTC, po standardowym nocnym rozliczeniu M0; pozostają na PR offline testy, brak sekretów, uprawnienie `contents:read`, 90-dniowy artefakt.
- Jeden przebieg czyta aktualne, niezmienne M0 SQLite do `src/kb3_step16_progressive_shadow.py` (prequential dynamiczna temperatura, tylko wcześniejsze rozliczone wyniki), a następnie `scripts/step17_offline_three_engine_audit.py` (M0 vs Elo-only vs CatBoost bez xG, wyłącznie host-attested same-fixture z settled FT). Drugi skrypt używa temp-copy bazowego pliku.
- Zainstalowanie wyłącznie `cryptography>=42,<47` potrzebnego do importów lokalnych weryfikatorów; brak klienta PitchAPI, brak uprawnień do wywołania API oraz zapisu do repo. Dwa osobne JSON w jednym artefakcie runu z SHA wejścia dla Step17 i śladami Step16.
- Odpala się raz dziennie jako raport, a nie nowy prognozujący model ani dodatkowe pobieranie. Nie przyspiesza matematycznie liczby meczów, ale usuwa bezproduktywne oczekiwanie między audytami oraz umożliwia wcześniejszą diagnostykę występujących wstrząsów danych.

## Obecne potwierdzone wartości przed zmianą
Receipt 02.11 18:24 UTC: 75 oryginalnych prognoz, 66 host-verified settlement, do 100 FIT brakuje 34; później wymaga 50 nowych po dopasowaniu. Pierwszy read-only SHADOW PR #132 sprawdzony na 27 later games po co najmniej 30 starszych wynikach: RAW Brier=0.52172/logloss=0.89068; dynamic T Brier=0.48327/logloss=0.83323. Wyłącznie diagnostyka na małym n, bez werdyktu Champion. Kod Step17 może obecnie zwracać 0 kwalifikowanych trójek — nie ma prawa wyprodukować fikcyjnych metryk.

## Bezpieczniki
Nie wolno używać wyników tych raportów do retroaktywnej zmiany prawdopodobieństw ani do wyboru produkcyjnego Championa. Istniejące workflow `forecast` wciąż maksymalnie raz na dobę w zamrożonej kohorcie, a zwiększenie liczby płatnych pollów nie ma dowodu, że spowoduje dodatkowe kwalifikowane mecze. Nie dokupujemy API, nie otwieramy TEST PL 2026/27, nie włączamy modeli xG bez certyfikowanego PIT. Formalny stan 15/29, GATE16/17=PENDING. Coś uznaje się za PASS dopiero po CI Python 3.11 i read-only audycie bieżącej bazy.
