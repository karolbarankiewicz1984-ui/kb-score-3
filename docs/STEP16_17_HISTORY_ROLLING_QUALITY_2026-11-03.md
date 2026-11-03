# KB Score 3.0 — kroki 1–3: historia, rolling 5/10/15, audyt (3 XI 2026)

## Krok 1 — prawdziwa historia PitchAPI i przyspieszenie
- Stan przed: [pierwszy realny run #41649130585](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/41649130585): 48 rzeczywistych meczów ze statystykami, 40 zweryfikowanych xG, 8 bez pełnej weryfikacji, 34 zakresy liga×sezon. POL 2023/24 i 2024/25 brak w katalogu PitchAPI.
- Poprzedni wybór 48 meczów rozpraszał próbkę po 34 ligach×sezonach. Zmiana: uzupełnianie spójnych, najnowszych grup do 180 spotkań danej ligi/sezonu, potem dalsze pogłębianie starszej historii. Priorytet 2025/26, 2024/25, 2026/27, rozgrzewka 2023/24. Limit bezpieczeństwa nadal 48 meczów / 150 zapytań na przebieg, prawdziwa liczba może być niższa. Harmonogram 02:15, 10:15 i 18:15 UTC oraz GitHub Actions workflow_dispatch.
- Wszystkie zakończone i co najmniej 3-godzinne mecze z list ligowych trafiają do osobnej nowej tabeli SQLite finished_fixture_index: identyfikatory, drużyny, liga, sezon, kickoff, wynik, czas obserwacji i hash źródła. Ta lista zawiera także mecze, dla których nie pobrano jeszcze xG ani statystyk. Zablokowane UPDATE/DELETE, rozbieżności źródła powodują kwarantannę/FAIL. Surowe odpowiedzi dostawcy nadal szyfrowane RSA/AES-GCM.
- Przechowywanie i analiza jedynie w oddzielnej badawczej bazie data/research/historical_multistat/observations.sqlite. Nie dotykać istniejących forecastów, M0, ML, ani Premier League 2026/27 TEST.

## Krok 2 — zestawy cech 5/10/15
- Kod src/kb3_historical_feature_quality.py bierze faktycznie ostatnie N zakończonych meczów drużyny, które rozpoczęły się co najmniej 3 godziny przed target kickoff. Nie wybiera ostatnich N meczów z xG; nawet jedno brakujące xG w faktycznej piątce oznacza niepełne xG5.
- Dla obu drużyn, oddzielnie wszystkie mecze i domowe/wyjazdowe, liczymy okna 5, 10, 15: gole, punkty, zweryfikowane xG/xGA, strzały, faule, rożne, kartki, podania i inne jawnie wymienione klucze całomeczowe.
- Każda statystyka ma valid_n, complete i mean wyłącznie przy pełnym N/N; braki nie są zerami. Rekordy pochodzące z dzisiejszych odczytów historycznych zawsze research_only / HISTORICAL_RECONSTRUCTED_NOT_ORIGINAL_PIT, bez wymyślonych dawnych dat pierwszej publikacji i bez dopuszczenia do oficjalnego treningu.
- Pochodne rolling_feature_cache można przeliczać po dopłynięciu statystyk, natomiast źródłowe observations i finished_fixture_index są append-only. Żaden wynik meczu docelowego nie trafia do jego własnych cech. UCL ma obecnie tylko formę z meczów UCL; łączenie z ligami krajowymi wymaga niezależnego mapowania drużyn.

## Krok 3 — audyt kompletności i błędów
- Każde pobranie automatycznie oblicza ROLLING_FEATURE_QUALITY.json: liczebności pełnych historycznych poprzedników, statystyk ogółem, xG, podstawowych pól oraz kompletnych PAR obu drużyn 5/10/15. Raport per liga i liga×sezon, powody niezweryfikowanych xG i obecność liczbowych pól u obu drużyn, tylko agregaty — bez surowych odpowiedzi.
- Realnie zebrane pola samego meczu zachowują wartości, lecz gdy shots i stats nie potwierdzają xG, szczegółowa wartość xG pozostaje null. Do uruchomienia CatBoost z xG potrzeba realnego pełnego przedmeczowego zestawu, nie tylko liczników xG w katalogu.
- 8 źródłowych braków xG wymaga odrębnych wersjonowanych, weryfikowalnych prób ponownego pobrania (nie wolno nadpisywać starego dowodu). Brakujące POL 2023/24 i 2024/25 wymaga osobnego przetestowanego dostawcy. Bez certyfikacji historycznego provider first-published_at nie twierdzić, że ten materiał jest oryginalnym PIT.

## Protokół odbioru
- PR: testy bez sekretów i bez odpytania PitchAPI obejmują rzeczywiste last5/10/15, rozdział home/away, fake-zero, xG, własny target, brak PIT, niemutowalny fixture index, zgłoszenie zmian provider, właściwy TEST oraz kontynuację pełnej historii po pierwszych 180 spotkaniach.
- Live: dopiero po CI na main i odczycie realnego GitHub Actions SUCCESS, raportu ROLLING_FEATURE_QUALITY.json, HISTORICAL_BACKFILL_REPORT.json, manifestu RSA/AES, bazowego SQLite i ich liczników. Nie mylić przygotowania kodu z potwierdzonym pobraniem.
- Formalne GATE16/GATE17 pozostają PENDING, bez zmian kalibracji 100 FIT + 50 nowych po dopasowaniu HOLDOUT.

## Historia kolejnych kroków — kolejność, wejścia i bramki
1. N1: kontynuować gęsty historyczny backfill 2025/26, 2024/25, 2026/27 i 2023/24; dowodem tylko autentyczne zakończone joby oraz rosnące unikalne źródła.
2. N2: uzyskać realnie pełne pary xG5, następnie xG10 i xG15 dla obu drużyn. Osobno podać brakujące faule, rożne, kartki i liczbę strzałów. Gate: N/N prawdziwych poprzedników i statystyk bez null.
3. N3: sprawdzić brakujące sezony POL, fazy rozgrywek NED/BEL oraz mapowanie drużyn UCL ↔ liga krajowa; bez zmyślonych identyfikatorów.
4. N4: przygotować niezależny chronologiczny dataset TRAIN/VALIDATION w wariancie retrospective-research, osobno od obecnego forward i chronionego TEST; potwierdzić definicje statystyk i brak przecieków.
5. N5: eksperymentalny, odseparowany CatBoost z xG i dodatkowymi statystykami, porównany z M0 i CatBoost bez xG na tych samych meczach oraz Brier/log loss per liga; brak automatycznej promocji.
6. N6: zachować odrębną docelową kalibrację forward 100 FIT + 50 nowych po-fit HOLDOUT; produkcyjny Champion tylko po odrębnej decyzji właściciela.
7. N7: niezależna, szyfrowana kopia źródłowej bazy z potwierdzonym odtwarzaniem i hashami, nie jedynie git repository.

Status przed końcowym odbiorem: implementacja na izolowanej gałęzi i testy do sprawdzenia przez CI; rzeczywiste wyniki należy dopisać po sukcesie live.