# KB Score 3.0 — GATE 06: ponowiony audyt PitchAPI (25.10.2026)

**Wynik techniczny: PASS dla audytu źródła danych** po aktualizacji klucza PitchAPI. **Model ML nie został uruchomiony ani wytrenowany.** Wcześniejsze nieudane próby HTTP 401 pozostają zachowane w [STEP_06_BLOCKER.md](STEP_06_BLOCKER.md).

## Dowody wykonania

- [GitHub Actions — ponowna próba #40220569321, attempt 2](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40220569321): zadanie **collect SUCCESS**; **7/7 testów offline PASS**. Cały workflow zakończył się oznaczeniem failure wyłącznie dlatego, że późniejszy job publikujący raport nie wypchnął commitu przy równoczesnej zmianie gałęzi `main` (non-fast-forward).
- W tym samym przebiegu poprawnie przeszedł test schematu i limitu żądań w jobie publikującym. Log podał: `AUDIT_COLLECTED`, zero błędów dostawców.
- **Archiwum ZIP zawierające pełny JSON (48 meczów) oraz raport MD (30 liga×sezon):** [Google Drive — KB3_PITCHAPI_STEP06_2026-10-25.zip](https://drive.google.com/file/d/1y3z4EdkkNJHb0oiuyFLU5elFVTiJoa_k/view). To **trwała kopia**, niezależna od 30-dniowej retencji artefaktu Actions.
- [GitHub Actions — artefakt w udanym jobie collect](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40220569321): oryginalny ZIP jest dołączony do uruchomienia, artefakt #12614348502.

## Co zostało sprawdzone

| Pozycja | Faktyczny wynik |
|---|---:|
| Ligi objęte audytem | 5: Premier League, La Liga, Serie A, Bundesliga, Ligue 1 |
| Kombinacje liga–sezon (2021/22–2026/27) | 30 |
| Kombinacje wymienione w katalogu PitchAPI | **24/30** |
| Nieobecne kombinacje | **6/30: La Liga, każdy badany sezon** |
| Liczba rozegranych meczów na dostępnych listach | 7301 |
| Wybrane próbki ze strzałami | **48** |
| Próbki z kompletnym liczbowym xG strzałów | **48/48** |
| Brakujące/częściowe xG w tej próbce | 0 |
| Jednoznacznie potwierdzone ID meczu API-Football | 14 |
| Potencjalne dopasowania aliasów — **niezweryfikowane** | 6 |
| Pozostałe: 24 nieporównane, 4 niejednoznaczne | 28 |
| Błędy PitchAPI / API-Football | **0 / 0** |
| Wywołania PitchAPI | 73 (limit audytu 110) |
| Wywołania API-Football | 24 (limit audytu 45) |
| Nowe zakupy | **0 zł** |

## Konkretny przykład — prawdziwe wartości ze sprawdzonych strzałów

- Watford – Southampton, 30.10.2021: **xG 1,05 / 1,75**, 22 strzały, PitchAPI `m_3nXDAl`, API-Football `710654`, dopasowanie jednoznaczne.
- Aston Villa – Chelsea, 16.10.2022: **xG 1,83 / 0,87**, 26 strzałów, PitchAPI `m_2mXJPL`, API-Football `868046`, dopasowanie jednoznaczne.
- Monza – Udinese, sezon 2023/24: **xG 0,53 / 1,11**, 20 strzałów, PitchAPI `m_23sPne`, API-Football `1052350`, dopasowanie jednoznaczne.

Wartości xG są statystykami **zakończonych meczów**, nie prognozami prematch. W modelu wolno korzystać z xG meczu dopiero do tworzenia cech dla **późniejszych** spotkań.

## Ograniczenia i przyszłe bramki

1. **La Liga brak w katalogu konta według aktualnego wyszukiwania; nie traktujemy tego jako 0 xG.** Trzeba rozważyć źródło alternatywne, ale bez kupowania czegokolwiek teraz.
2. **48/48 jest wynikiem próbek, nie potwierdzeniem pełnego pokrycia 7301 spotkań.** Pełną kompletność zweryfikujemy podczas importu i oczyszczania danych w krokach 09–10.
3. Spośród 48 próbek tylko 14 zostało **jednoznacznie** dopasowanych do API-Football. Dalsze mapowanie identyfikatorów i aliasów zostawiamy do kroku 07. Alias bez weryfikacji nie staje się automatycznie prawdziwym powiązaniem.
4. Bieżący odczyt historycznego meczu nie potwierdza, kiedy statystyka została opublikowana; przyszłe modele mają rygorystycznie stosować odcięcie informacji czasowej.
5. Cały Actions run ma status **failure** przez techniczny konflikt `git push origin HEAD:main`; **job collect i test danych osiągnęły SUCCESS**. Pełna, niezmieniona kopia raportu znajduje się na Dysku Google, a ten plik utrwala decyzję po odczycie artefaktu.
6. Nie odczytano ani nie zapisano kluczy API w raporcie. Nowe hasło działa w sekretach `kb-score-3`.

## GATE 06 — warunki odbioru

- [x] PitchAPI zwraca katalog lig po aktualizacji klucza.
- [x] Sprawdzono deklarowane sezony i dostępne mecze, z jawnym raportem brakującej La Ligi.
- [x] Potwierdzono rzeczywiste xG dla reprezentatywnej próbki 48 meczów i podano przykładowe identyfikatory.
- [x] Wyodrębniono 14 jednoznacznych dopasowań API-Football, a 6 aliasów pozostawiono jako niepotwierdzone.
- [x] Braki oddzielono od rzeczywistych zer oraz zastrzeżono postmatch i czas dostępności danych.
- [x] Testy 7/7 PASS, trwałe archiwum, kontrola limitów 73+24 żądań.

**Decyzja:** GATE 06 **PASS / ZALICZONO** jako audyt źródła danych, nie jako walidacja pełnej bazy ani modelu. Kolejny krok 07 — mapowanie meczów i identyfikatorów, dotąd NIE ROZPOCZĘTY. [Plan główny Google Docs](https://docs.google.com/document/d/10wjHL3r3OAuxtezwcIeWztxS8lwjhYon5GM3BLhI0xE/edit).
