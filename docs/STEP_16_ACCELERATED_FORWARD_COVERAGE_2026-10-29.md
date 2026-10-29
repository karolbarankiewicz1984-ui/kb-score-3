# KB Score 3.0 — Krok 16: maksymalne bezpieczne przyspieszenie zbierania forward

**Data 29.10.2026 | zakres wyłącznie badawczy M0 SHADOW | GATE16 PENDING | 15/29.**

## Co rzeczywiście zmieniono

- Dotychczas: maksymalnie cztery najbliższe mecze na ligę na każdy dzienny snapshot. Teraz: **do dziesięciu** w każdej z **trzech** lig, ale tylko dla kickoff w ciągu **najbliższych 96 h** oraz z marginesem **minimum 90 minut** względem zamrożenia.
- Od tej pory snapshot SQLite może mieć od 0 do 30 nowych rekordów dziennie (zamiast sztywnego 12), z pełnym audytem rzeczywistej liczby na ligę. Aktualizacja NIE dodaje fałszywych prognoz: nadal najwyżej **jedna faza EARLY i jeden forecast 1/X/2 na identyfikator meczu**, bez ponownego liczenia tego samego spotkania.
- Recepta dla wcześniejszych meczów również wybiera do 10 docelowych spotkań, ale **maksymalnie sześć nowych historii xG na ligę** i stały limit łącznie **43 API calls na dzienny przebieg** pozostaje. Brak zakupu nowego dostawcy i brak dodania lig do wersji M0.
- Dni bez nowych *niepobranych* historycznych shots/stats nie blokują pozyskania dzisiejszych przedmeczowych cech. Natomiast próba pobrania zakończona brakiem poprawnych źródeł xG wciąż daje błąd. Gdy w oknie 96 h nie ma żadnego meczu, źródła nie są sztucznie przekształcane w prognozy.
- W GitHub Actions podczas PR wykonują się tylko testy offline: pobieranie z płatnego PitchAPI i pisanie live do `main` zostało wyraźnie zablokowane.
- Pierwotny domyślny limit cztery oraz jego archiwalne 12-meczowe testy pozostają niezmienione. Historia SQLite, archiwum rzeczywistych prognoz i źródłowe hashe są append-only; parametry prawdopodobieństw, status SHADOW, oryginalny strict PIT i chroniony Premier League TEST 2026/27 bez zmian.

## Dlaczego nie skracamy polityki 100+50

Kalibracja wymaga 100 **unikalnych, rzeczywiście zamrożonych i rozliczonych** meczów niezmienionego parametru SHA / wersji M0 i fazy, a dopiero po *zamrożeniu dopasowania T* minimum 50 dalszych nowych prognoz i rozliczeń na odrębnym holdoucie. Nie da się uczciwie zastąpić tych 50 starszymi meczami, dublem dnia, innym modelem lub historią 374 VALIDATION. Próbki M0 SHADOW z parametrami ilustracyjnymi **nie są automatycznie próbkami do kalibracji przyszłego, dopasowanego modelu Champion**; dla zmienionej wersji będzie osobny licznik i osobny fit.

## Czy na pewno będzie szybciej?

Limit cztery był realnym ryzykiem utraty części jednoczesnych meczów z weekendu. Teraz większa część kolejki może zostać zamrożona przed kickoff, bez zwiększenia dziennego limitu provider calls. Przepustowość wynikowa zależy jednak od faktycznego terminarza, odsetka odrzuceń za późny capture, zgodności tożsamości, limitów API i poprawności źródłowych timestampów. **Nie ma gwarancji 30 próbek dziennie**: to maksimum *otwartych migawek*, nie liczbę niezależnych zakończonych meczów; w zwykłym tygodniu w trzech ligach jest najwyżej liczba naprawdę rozegranych meczów (orientacyjnie 29 na pełną kolejkę).

## Testy i odbiór

- Offline: testy bazowe SQLite, PIT, kryptograficznej chronologii i realnego freeze przechodzą po rozszerzeniu. Przy PR nie odpytywano PitchAPI (skip).
- [GitHub Actions #40930196678](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40930196678) — cztery suity PASS, 35 testów, prawdziwy API capture na PR celowo SKIPPED.
- Live: następny pełny dzienny przebieg **po włączeniu tej zmiany na main** będzie pierwszą kontrolą faktycznej wielkości nowego batchu (maksymalnie 30). Bez runu źródłowego nie podawać liczby rzeczywiście nowych próbek ani tempa tygodniowego jako faktu.

**Rekomendowana dalsza decyzja:** po kilku rzeczywistych kolejkach policzyć skuteczne unikalne prognozy z potwierdzonym zewnętrznym freeze i wykluczenia; w razie potrzeby osobno audytować dodatkowe ligi/limity PitchAPI. Nie zwiększać zużycia API ponad istniejące 43 na dzień ani nie kupować pakietów bez oddzielnego pozwolenia.
