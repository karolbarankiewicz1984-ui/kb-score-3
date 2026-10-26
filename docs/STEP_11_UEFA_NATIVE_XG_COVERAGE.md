# KB Score 3.0 — GATE11: rzeczywiste natywne xG Ligi Europy i Ligi Konferencji

**26 października 2026 • audyt częściowy PASS • cały GATE11 nadal PENDING (10/29).**

## Cel

Sprawdzić, czy nowy tor oparty **wyłącznie na PitchAPI** zawiera strzałowe xG dla Ligi Europy i Ligi Konferencji 2026/27, bez historycznej krzyżowej identyfikacji API-Football. Badanie ma pokazać **rzeczywiste dane próbek**, a nie tylko listę rozgrywek w katalogu.

## Wynik prawdziwego pobrania

[Run #40318301119 — SUCCESS](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40318301119)

| Dane PitchAPI | Liga Europy | Liga Konferencji |
|---|---:|---:|
| Spotkania w sezonowej liście (nie cały format rozgrywek) | 144 | 108 |
| Zakończone dostępne w chwili audytu | 54 | 36 |
| Zakończone mecze wybrane chronologicznie | 6 | 6 |
| Liczba odmiennych dat w próbce | 4 | 2 |
| **Kompletne strzałowe xG obu drużyn** | **6/6** | **6/6** |
| Brakujące/częściowe xG | 0/6 | 0/6 |

W sumie **12/12** kompletnych obserwacji xG. Mechanizm wymaga zgodnego natywnego `PitchAPI.match_id`, a nie podobnych nazw z innych źródeł. Próba jest **celowo rozłożona w czasie**, ale nie jest losowa ani pełna; szczególnie w Lidze Konferencji objęła tylko dwie daty. Nie można na tej podstawie zagwarantować xG dla każdego meczu w sezonie lub dla przyszłych faz rozgrywek.

**Koszt dostępu:** dokładnie **15 wywołań PitchAPI**, w tym 1 katalog, 2 listy spotkań i 12 odpowiedzi shot xG; **0 wywołań API-Football**. Nie uruchomiono nowego abonamentu ani zadania cyklicznego.

## Dowód źródłowy i kopia

Każdą z 15 odpowiedzi zapisano w niezmiennym pakiecie źródłowym zawierającym **rzeczywiste czasy pobrania, oryginalne dane dostawcy, ich SHA-256 i łańcuch hashy**. Własny typ szyfrogramu `KB3UE1` używa AES-256-GCM + RSA-OAEP-SHA256 do istniejącego publicznego klucza odbiorcy. Nie przesłano klucza prywatnego do GitHuba.

- [Zaszyfrowany backup w Google Drive](https://drive.google.com/file/d/1LdmMRLmtaObUK7gs9r55D6950jTMCwxF/view) — ZIP 44 599 bajtów.
- ZIP SHA-256: `4401fa6be34bad08ddf3729f563506b231851ef45554d0389b524ea34ce30ac4`.
- Szyfrogram SHA-256: `fc49dc39502a2c73a8883d0732797a284075845bac9161f183bf9a496d4c6b16`.
- Hash ostatniej obserwacji: `aef1c98c5dfc6cecb60ab810a13b5ed5ca82fd956b79fb4ad5c33b0b2b9ccc06`.
- Wykonano **niezależne ponowne pobranie z Google Drive**. Porównano ZIP SHA, CRC plików oraz SHA zaszyfrowanego payloadu z manifestem — **PASS**.
- **Ważne:** ponowne odszyfrowanie kopii Drive kluczem prywatnym **nie zostało jeszcze przeprowadzone**. Pełną zgodność oryginalnych 15 odpowiedzi i łańcucha zweryfikowano w GitHub Actions **przed szyfrowaniem**, a kontrola po pobraniu potwierdza tylko integralność zaszyfrowanej kopii. To osobny punkt do zaliczenia w GATE11.

Nie umieszczono publicznie oryginalnych danych wszystkich strzałów, identyfikatorów par z próby ani prywatnego klucza. Dane surowe znajdują się w zaszyfrowanym pakiecie. [Manifest zbiorczy z hashami i ograniczeniami](../data/audits/STEP11_PITCH_UEFA_XG12_2026-10-26.json).

## Kod i testy

- `scripts/step11_uefa_native_xg_capture_once.py` — jedno uruchomienie, ograniczenie do 15 wywołań, sześć chronologicznych próbek z każdej ligi, odrzucanie niedokończonych meczów i błędnych ID, brak podstawiania zera za nieobecne xG.
- `src/kb3_pitch_uefa_evidence.py` — kanoniczne hashe oryginalnych źródeł, rzeczywiste timestampy i AES/RSA koperta z osobnym MAGIC/AAD; syntetyczny odczyt nie może być wydany jako źródłowy dowód rzeczywisty.
- `tests/test_step11_uefa_native_xg.py` — dwanaście nowych testów, w tym brakujący xG, różny ID meczu w shot feedzie, niedozwolone cofanie czasu, próby modyfikowania łańcucha, uszkodzenie szyfrogramu oraz dobór próbki bez duplikatów.
- [Pełna regresja #40318219204](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40318219204): **187/187 PASS** (148 testów Step11, 39 poprzednich), bez wywołań dostawców.

## Następne wymagania GATE11

1. Wykonać **rzeczywiste odtworzenie** zaszyfrowanego backupu UEFA z kopii Drive przez prywatny klucz właściciela i porównać wszystkie rekordy; nie ujawniać klucza w CI.
2. Zbadać xG na większej, bardziej zróżnicowanej próbce, nie deklarując pełnego pokrycia tylko z 12/12.
3. Zarejestrować **rzeczywiste korekty wyników i terminów z kolejnych dat**; nie udawać historycznych obserwacji wykonanych wcześniej.
4. Potwierdzić warunki licencyjne/dopuszczalne sposoby wykorzystania PitchAPI oraz jakość dla kolejnych lig przed decyzją o przełączeniu produkcyjnym.

**Wciąż `GATE11 PENDING`, formalnie 10/29.** Zero treningu, zero typów, brak przełączenia produkcyjnego. Dawne KB Score 2.1, API Market i MultiModel oraz ich archiwa nie zostały zmienione.
