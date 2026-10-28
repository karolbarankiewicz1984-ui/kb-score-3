# Krok 14 B — realne xG PitchAPI vs FPL/Opta na tych samych spotkaniach (28.10.2026)

**Status technicznego eksperymentu: wykonany.** [GitHub Actions #40739852904](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40739852904) SUCCESS, 4+16 testów offline PASS i **14 prawdziwych odczytów SDK PitchAPI** z uprzednio skonfigurowanego sekretu GitHub, **bez podawania klucza na Windows**. Zamrożony [raport](../data/audits/STEP14_B_REAL_PITCHAPI_FPL_XG_EXACT_6_MATCHES_2026-10-28.json) i artifact `KB3_STEP14_B_REAL_PITCHAPI_XG_AGGREGATE_NO_SECRETS` zawierają tylko liczbowe agregaty różnic, żadnych źródłowych xG/ID.

**Identyfikacja:** wszystkie 380/380 mecze Premier League 2023/24 połączono dokładnym kickoff, stroną home/away i pełnym 20-klubowym układem 38 spotkań z oryginalnym, historycznym FPL `fixtures.csv`, w którym xG 29 725 zawodników jest przypisane do dokładnego `fixture + FPL team`. Wybrano mechanicznie 6 meczów z indeksów chronologicznych 20, 84, 148, 212, 276, 340 = 12 stron drużynowych. Nie stosowano porównania wyników, nazw drużyn po fuzzy matching ani testowego holdoutu. Odczytano aktualne historyczne `matches.shots` i `matches.stats` dla natywnych ID.

**Definicja wykryta w prawdziwym SDK:** team `expected_goals` w okresie `All` występuje w **dwóch grupach**, `Expected goals (xG)` i `Top stats`. Poprawiono parser, aby preferował oryginalną grupę `Expected goals (xG)`, a powtórzona wartość z `Top stats` była wymagana zgodna w tolerancji 0,02. Inne zdublowania i `xGOT`/`npxG` nadal odrzucane; 16/16 testów statystyki jednostkowej PASS.

| Miara dla 12 stron drużynowych | MAE | Mediana absolutnej różnicy | Maksimum | ≤ 0,02 | ≤ 0,10 |
| --- | ---: | ---: | ---: | ---: | ---: |
| **PitchAPI shot xG → PitchAPI team xG** | **0,015** | 0,01 | 0,06 | 9/12 | 12/12 |
| **FPL/Opta sum player xG → PitchAPI team xG** | **0,0525** | 0,02 | 0,24 | 7/12 | 10/12 |

**Interpretacja:** 0,015 sugeruje, że PitchAPI `stats` odpowiada strzałowemu xG z niewielkim zaokrągleniem lub różnicą modelową; ale **3/12** różnią się o ponad 0,02, więc nie twierdzimy, że to dokładnie ta sama suma. FPL/Opta średnio różni się o 0,0525, miejscami do 0,24, więc **równoważność obu dostawców nie jest udowodniona** i niedozwolona jest cicha zamiana. Nie porównywano meczowych wyników ani rynków.

**Nierozwiązany, niezależny problem:** FPL/Opta stary snapshot jest publicznie poświadczony **27.05.2024 18:05:12 UTC**, a rzeczywisty odczyt historycznej statystyki PitchAPI wykonano **dopiero 28.10.2026 17:53:03 UTC**. Dostawca nie dołączył historycznego `first_published_at` ani wersjonowania team xG 2023–2025. Dzisiejsze statystyki nie są dowodem PIT przed dawnymi kickoffami. Nadal potrzebna autentyczna historia wersji lub pisemne i sprawdzalne poświadczenie dostawcy.

**Status oryginalny: 13/29, GATE14 PENDING, TRAIN 0/760 i VALIDATION 0/380, M1 niewytrenowany, TEST/20 zamrożonych prognoz nietknięte.**
