# CODEX-03 — protokół selekcji przed porównaniem A/B

Baza: main `eabab06139b185d34450d314989783bdc980b088`. Protokół zapisany
przed oceną A/B; nie zmieniamy reguł po obejrzeniu wyników.

1. Prawdziwe, zakończone mecze ośmiu krajowych lig; ENG i UCL wykluczone
   z nowego selektora. Natywne ID bez wymyślania mapowań. Jeden indeks przez
   sezony, bez resetu last N na granicy sezonu. Wynik poprzednika dopuszczony
   od kickoff+3h, tak jak w obecnym raporcie historycznym. To plan poboru,
   nie certyfikowane cechy przedmeczowe.
2. Jednostka korzyści: komplet obu drużyn w rzeczywistym oknie 5/10/15,
   osobno all oraz venue (gospodarz: domowe, gość: wyjazdowe). Brakującego
   poprzednika nie zastępujemy starszym. Brak xG pozostaje brakiem.
3. Deterministyczny greedy wybiera całe uzupełniające się zestawy źródeł,
   maksymalizując bieżącą ważoną liczbę domknięć na koszt pary shots+stats.
   Wagi all5/10/15=16/8/4, venue5/10/15=4/2/1. To heurystyka, bez dowodu
   globalnego optimum. Gdy cały zestaw nie mieści się w budżecie, finansujemy
   postęp ku brakującemu oknu, potem gęstą historię.
4. Zachowujemy zasadę PR #142: przy paczce >=32, co najmniej trzech dostępnych
   ligach i rozstępie pokrycia >=64, cała paczka służy najmniej pobranej lidze.
   Reguła działa przez wszystkie dostępne sezony i rotuje po zapisaniu paczki.
   Niezweryfikowane istniejące xG kierowane są do źródłowego recheck, a nie
   ponownie wstawiane do immutable observations.
5. Nowy selektor widzi tylko dotychczasowe źródła. Nie zna powodzenia żadnego
   przyszłego pobrania. Wyłącznie plan zakłada, że wybrane pary przejdą
   walidację; prognozowany przyrost jest osobno oznaczonym sufitem, nie wynikiem.
6. Rzeczywisty, zamknięty replay: wcześniejszy stan przed run 41692857683-1
   oraz dokładnie te same 240 później zapisanych ID i ich archiwalne statusy
   dla A/B. Pełny indeks poprzedników pozostaje identyczny; ograniczamy tylko
   pulę kandydatów, nie historię. Baseline to obecny selektor z identycznym
   filtrem dostępności kandydatów. Nie oznaczamy pozostałych braków jako znane.
7. Punkty pomiaru: 48/96/144/192/240 par, bez podglądu statusów niewybranych
   rekordów. Ten replay jest warunkowy względem zapisanej puli wybranej przez
   wcześniejszy kolektor. Nie dowodzi skuteczności na niepobranych meczach.
   Po wykorzystaniu całej identycznej puli wynik musi być identyczny — to
   kontrola poprawności, nie powód do tworzenia fikcyjnego zysku. Jeśli baseline
   nie wypełni paczek, osobno porównujemy prefiksy przy jednakowej liczbie par.
8. Główna wspólna populacja celów: wszystkie zaindeksowane krajowe wyniki.
   Osobno stałe ID szczegółowych obserwacji sprzed replay, zgodne z pojęciem
   targets w starych raportach; nie mieszamy przyrostu źródeł z podmianą próby.
   Raportujemy oba okna all/venue, ligi, sezony i przyczyny braków. Zachowujemy
   istniejące statusy źródła; raw encrypted receipts nie są tu ponownie
   odszyfrowywane/uwierzytelniane. Odbiór CODEX-01 nadal wymagany.
9. Osobny plan następnych 5×48 na pełnym obecnym indeksie podaje prawdziwe ID,
   koszt i wyłącznie optymistyczne domknięcia. Bez wykonywania API/backfillu.
10. Limit 48/paczkę, 150 requestów/paczkę, do pięciu paczek, dotychczasowe
    RSA/AES i observed-at bez zmian. Bounded retry transportu ma jeden
    ponowny request i rezerwę na pozostałe pary. Sukces w danym zasobie jest
    memoizowany w paczce; niepełna para po awarii transportu pozostaje poza
    immutable observations i może wrócić w następnej paczce. Statystyki już
    odebrane pozostają w zaszyfrowanym archiwum, nie stają się pełnym xG.
    Kontrola SDK 0.1.6 wykazała domyślne dwa ukryte retry: w historycznych CLI
    wyłączone (`max_retries=0`), ponowienia rozliczane jawnie wraz z rezerwą.
    Ten problem transportu nie zmienia rankingu ani wyników zapisanych źródeł.
11. Domyślny kolektor i harmonogram zachowują selektor current. Window-yield
    jest jawną opcją. Przed jego użyciem live: przegląd kodu, CI, odbiór źródeł,
    kontrolowany pomiar nowych źródeł na ustalonej próbie i porównanie kosztu.
    Bez automatycznego merge, zmiany M0, TEST, kalibracji lub klasy dostępności.

Korekta techniczna po pierwszej próbie replay, przed oceną przyrostów: błędne
założenie kontrolne o zużyciu wszystkich 240 rekordów w pięciu paczkach nie
zachodzi dla starego selektora w ograniczonej puli (233 zamiast 240).
Weryfikator nie wymusza już fikcyjnego domknięcia starej metody; wylicza wspólne
prefiksy 48/96/144/192/233 oraz osobno wykorzystanie paczek. Nie zmieniono
wag, rankingu, puli ani statusów źródeł w odpowiedzi na wyniki jakościowe.
