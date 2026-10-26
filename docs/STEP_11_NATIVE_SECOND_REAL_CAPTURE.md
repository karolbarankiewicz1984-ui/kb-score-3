# Krok 11 — drugi autentyczny odczyt PitchAPI i wynik porównania

**26 października 2026 r.** Druga obserwacja w jednym dniu: **PASS**. Cały **GATE11 nadal PENDING (10/29)**.

## Rzeczywiste pobranie i bezpieczne zachowanie

Wykorzystano wcześniej zatwierdzony mechanizm pobierania i szyfrowania PitchAPI. Drugie uruchomienie: [GitHub Actions #40321588543](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40321588543), `SUCCESS`. Dokładnie **7 odczytów PitchAPI**, zero API-Football i żadnego nowego abonamentu.

- Pierwszy pełny snapshot: **2026-10-26 11:29:09.681040 UTC**, 380 fixture, 5 odpowiedzi xG.
- Drugi pełny snapshot: **2026-10-26 12:19:16.338115 UTC**, 380 fixture, 5 odpowiedzi xG.
- Odstęp: **50,11 min**. Obie obserwacje zostały naprawdę pobrane z sieci i zapisane w dwóch **niezależnych** rejestrach, nie zduplikowano pliku ani nie nadano sztucznej wcześniejszej daty.
- Drugi szyfrogram i manifest: [Google Drive — kopia 12:19 UTC](https://drive.google.com/file/d/1X27ol04hWczbRCKin_pcKeiyVcLeF_x7/view), 67 902 B. ZIP SHA-256 `7849b3dcebaa7b906f6a36df9584e8043d028cd20d7c2a1b8d77d136d4b09163`, ciphertext SHA-256 `3355a181d82f2d5f5ad1c474962fedaca6d8f314c1dccd315b3e62ecd4e3ce80`. [Pierwsza kopia 11:29 UTC](https://drive.google.com/file/d/18AeQOY7it5F58S4EqHKk8GDpqOD_TtUg/view).
- Nowy backup **przesłano do Google Drive, potem z niego ponownie pobrano**. CRC ZIP, SHA ZIP, SHA szyfrogramu i SHA manifestu zgadzają się.

## Niezależny audyt dwóch odtworzonych baz

Oba archiwa *oddzielnie* odszyfrowano posiadanym dotychczas kluczem prywatnym właściciela, poza GitHubem. Dla każdego pliku ponownie obliczono hashe **385** zapisanych rekordów, hash każdej z **6** sesji, strukturę łańcucha `previous_sha256` i jej końcowy hash. Sprawdzono zgodność SHA SQLite, `PRAGMA integrity_check=ok` oraz `PRAGMA foreign_key_check=0`. Weryfikacja **PASS**. Klucza prywatnego i surowych wyników ani feedów xG nie publikowano.

Porównano rekord po rekordzie **380 meczów**, dokładnie według `PitchAPI.match_id`.

| Rodzaj różnicy między 11:29 i 12:19 UTC | Wynik |
|---|---:|
| Zmienione dowolne źródłowe dane meczu | **0/380** |
| Zmiana godziny rozpoczęcia | 0 |
| Zmiana statusu meczu | 0 |
| Korekta wyniku | 0 |
| Zmiana nazwy klubu | 0 |
| Zmiana natywnego `team_id` | 0 |
| Zmienione odpowiedzi strzałowe xG tych samych pięciu spotkań | **0/5** |

Obie pełne odpowiedzi terminarza mają identyczny SHA-256 `3f68e047863fe6e4c2ffef3b84013fbe121a19b2054503ffa766520c072fc2da`. Oddzielne hash-chains mają **różne** prawidłowe sumy końcowe, ponieważ czas rzeczywistego pobrania jest inny; nie należy łączyć ich w jeden fałszywy łańcuch.

[Manifest audytu bez surowych danych](../data/audits/STEP11_PITCH_NATIVE_TWO_REAL_CAPTURES_20261026.json).

## Co to potwierdza, a czego nie

Wynik potwierdza **stałość dwóch autentycznie pobranych źródłowych obrazów Premier League przez około 50 minut tego samego dnia** i odtwarzalność zaszyfrowanych archiwów. Oznacza też usunięcie poprzedniego blokera „brak drugiego prawdziwego snapshotu”.

Nie dowodzi stabilności między różnymi dniami, oryginalnego czasu pierwszego opublikowania danych przez PitchAPI, kompletności xG wszystkich lig, licencyjnej gotowości produkcyjnej ani wiarygodności historycznych symulacji przedmeczowych 2023–2025. Nie uruchomiono kalibracji ELO, treningu, generowania typów lub migracji produkcyjnej. Starsze archiwa API-Football i inne modele bez zmian.

**Stan: GATE11 PENDING, 10/29 formalnie zaliczonych, `training_allowed=false`.** Następne zadanie: nowa rzeczywista obserwacja z innego dnia i jej porównanie z niniejszym materiałem oraz końcowy audyt jakości cech, bez datowania wstecznego.
