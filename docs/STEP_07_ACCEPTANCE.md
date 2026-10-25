# KB Score 3.0 — KROK 07: protokół odbioru łączenia identyfikatorów

**Data:** 25.10.2026 (Europe/Warsaw). **GATE 07: PASS / ZALICZONO** w zakresie **mechanizmu** bezpiecznego łączenia i kontrolowanej próbki. **Nie oznacza automatycznej zgodności całej historycznej bazy ani aprobaty 22 nierozstrzygniętych par.**

## Rzeczywiście wykonane działania i dowody

1. **Źródło PitchAPI:** niezmieniony zbiór 60 przykładowych meczów z [GATE 06](../data/audits/PITCHAPI_STEP06_2026-10-25.json), po 2 dla 30 kombinacji pięciu lig i sześciu sezonów 2021–2026.
2. **Źródło API-Football:** 30 osobnych odczytów `/fixtures?league&season`, razem **10 679 rekordów meczowych** do porównania. Bez nowych zakupów i ponownego pobierania xG.
3. **Silnik dopasowania:** [scripts/step07_identity_audit.py](../scripts/step07_identity_audit.py): liga+sezon, ścisłe nazwy klubów po ograniczonej normalizacji, UTC kickoff ±20 minut, ten sam wynik i status zakończonego meczu, **unikatowe przypisanie 1:1**.
4. **Weryfikacja negatywna:** [17 testów offline](../tests/test_step07_identity_audit.py), m.in. polskie/niemieckie znaki, UTC/DST, zamiana gospodarzy i gości, inne wyniki, przesunięcie terminu, identyczny identyfikator przypisany do dwóch meczów, różne nazwy, wcześniejszy błędny odczyt.
5. **Uruchomienie początkowe z poprawnie wykrytą rozbieżnością:** [Actions #40236350417](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40236350417) — FAIL, celowo **nie uznano jako bramki PASS**; 15/15 testów jednostkowych OK, znaleziono jedną godzinę różnicy przy poprzedniej deklaracji „EXACT”.
6. **Poprawiony test:** [Actions #40236615477](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40236615477) — **success**, 17/17 testów PASS; 30 odczytów API, 60 rekordów, 0 niezgodności faktycznego identyfikatora, 0 duplikatów.
7. **Trwały zapis:** [Actions #40236771701](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40236771701) — **success**, porównał artefakt z kryteriami odbioru i opublikował oba pliki do prywatnego repo: [mapa JSON](../data/audits/STEP07_MATCH_CROSSWALK_2026-10-25.json), [raport i kolejka przeglądu](audits/STEP07_MATCH_CROSSWALK_2026-10-25.md).

## Wynik pomiarowy

| Wskaźnik | Wynik |
|---|---:|
| Liczba przebadanych par (PitchAPI) | 60 |
| Grupy liga × sezon | 30 |
| Liczba meczów z API-Football sprawdzona jako pulę kandydatów | 10 679 |
| **STRICT: wiarygodne automatyczne przypisanie 1:1** | **38** |
| **REVIEW_CANDIDATE: bez przypisanego ID** | **22** |
| Niepewne dopasowania automatycznie uznane za pewne | **0** |
| Konflikty identyfikatorów w porównaniu z poprzednią próbką | **0** |
| Zduplikowany klucz PitchAPI lub API-Football w STRICT | **0** |
| Wcześniej zatwierdzone pary ponownie potwierdzone | 19 |
| Poprzednio zatwierdzona para wycofana z automatycznego łączenia | **1** |
| API-Football request count | 30 |
| Testy | 17/17 PASS |
| Nowe abonamenty/koszty zakupu | 0 zł |

**Ważne:** `STRICT` oznacza bezpieczne łączenie w **historycznym zbiorze**, gdzie wynik już znamy i służy do niezależnej identyfikacji tego samego wydarzenia. Wyniku meczu **nie wolno używać jako cechy przedmeczowej dla tego wydarzenia**. Przed przyszłym spotkaniem obowiązuje osobny tryb identyfikacji bez wyniku, który trzeba przetestować przy budowie bazy i prognoz.

## Reprezentatywna ręczna kontrola

Zestawienie zostało przejrzane na podstawie dwóch źródeł dla przykładów zgodnych oraz niepewnych:

| PitchAPI | API-Football | Klasyfikacja |
|---|---|---|
| Watford — Southampton, 30.10.2021 | ID 710654 | STRICT; te same nazwy, wynik, kickoff |
| Getafe — Celta Vigo, 25.10.2021 | ID 720833 | STRICT |
| Atlético Madrid — Real Sociedad (przykład jednostkowy) | Atletico Madrid — Real Sociedad | NFKD/normalizacja akcentów; test automatyczny |
| West Ham United — Everton, 29.10.2023 | ID 1035135, „West Ham — Everton” | REVIEW: skrócona nazwa, niezatwierdzona automatycznie |
| Bochum — Eintracht Frankfurt, 08.10.2022 | ID 871241, „VfL Bochum — Eintracht Frankfurt” | REVIEW: różne nazwy klubu |
| Brest — Toulouse, 02.04.2023 | ID 871758, „Stade Brestois 29 — Toulouse” | REVIEW: nazwy różnią się mocno |
| Liverpool — Brighton & Hove Albion, 02.11.2024 | Kandydat ID 1208116 „Liverpool — Brighton”, inny mecz o tym samym wyniku także pojawia się w liście | REVIEW: odmienne nazwy; brak samoczynnego wyboru |
| Lyon — Auxerre, 27.10.2024 | ID 1213822 | **REVIEW TIME OFFSET:** identyczne drużyny i 2:2, ale kickoff w danych różni się o 60 minut; nie przyjmować jako automatycznie pewnego |

**Nie traktować przeglądu przedstawionych kandydatów jako ręcznej zgody na wpisanie ID do produkcyjnej mapy!** Nawet trafnie wyglądające aliasy wymagają osobnej reguły i jej testu, a kolejka pozostaje niezatwierdzona.

## Polityka tożsamości — zakazy

- W razie niezgodności czasu, nazw, wyniku albo wielu podobnych kandydatów: `REVIEW` lub `UNMATCHED`, nigdy przypisanie „najbardziej podobnego” na ślepo.
- Niezgodność godzin między API powinna być widoczna; DST/zmiany strefy są **hipotezą**, nie automatycznym usprawiedliwieniem różnicy.
- Wynik 0:0/1:0 czy xG nie wystarcza do identyfikacji samodzielnie.
- Jedno Pitch ID i jedno API-Football ID mogą tworzyć maksymalnie jedną zaakceptowaną parę; konflikt blokuje.
- W kroku 08 zaprojektować tabelę `fixture_provider_map` z `match_quality`, `review_status`, `source_snapshot`, `reviewed_at`, `kickoff_utc` i datą ważności aliasów; w kroku 09 rozwijać mapowanie dla pełnych sezonów; w kroku 10 sprawdzić anomalie/duplikaty.
- Dla dopiero zaplanowanych meczów osobna metoda bez wyniku spotkania i z uwzględnieniem przełożeń; nie używać historycznego `STRICT` jako dowodu testu tego wariantu.

## Decyzja bramki

**GATE 07: PASS** na podstawie 38 potwierdzonych par, 22 prawidłowo zatrzymanych do kontroli, braku nieuprawnionych automatycznych połączeń i 17 testów. **Kolejka nie zostaje oznaczona jako rozwiązana.** Nie uruchomiono modelu ML, nie zmieniono starszego KB2.1 ani nie kupiono nowych usług.

**Następny krok: 08 — projekt bazy danych i archiwum**; nie zaliczać go na podstawie samego GATE 07. Plan i status: [Google Docs](https://docs.google.com/document/d/10wjHL3r3OAuxtezwcIeWztxS8lwjhYon5GM3BLhI0xE/edit).
