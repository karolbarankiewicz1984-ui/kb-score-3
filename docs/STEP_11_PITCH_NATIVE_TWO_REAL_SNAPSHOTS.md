# KB Score 3.0 — krok 11: pierwszy PRAWDZIWY audyt zmian dwóch natywnych archiwów PitchAPI

**Data: 26.10.2026.** Dwa rzeczywiste odczyty Premier League 2026/27 z tego samego dnia. Stan: **częściowy PASS, GATE11 PENDING (10/29)**. Brak treningu i prognoz.

## Rzeczywiste odczyty, a nie symulacje

| Kontrola | Odczyt 1 | Odczyt 2 |
|---|---|---|
| Godzina pełnego terminarza UTC | 11:29:09.681040 | 12:19:04.753366 |
| Spotkania z natywnym ID PitchAPI | 380 | 380 |
| Odrębne odpowiedzi źródłowe | 6 | 6 |
| Liczba rekordów z SHA-256 | 385 | 385 |
| Kompletne próbki xG | 5/5 | 5/5 |
| Wywołania PitchAPI | 7 | 7 |
| Wywołania API-Football | 0 | 0 |
| Zaszyfrowany backup | [Drive — pierwsze źródło](https://drive.google.com/file/d/18AeQOY7it5F58S4EqHKk8GDpqOD_TtUg/view) | [Drive — drugie źródło](https://drive.google.com/file/d/13idXMzj3dIn_luUdVi7LbcxKROjeLeZ5/view) |

**Drugi realny odczyt:** [GitHub Actions #40321560312](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40321560312), SUCCESS, świadomie wywołany raz, bez harmonogramu. Klucz prywatny pozostał poza Githubem.

Drugie źródło zostało ponownie pobrane **z Google Drive**, a oba archiwa niezależnie odszyfrowane kluczem właściciela w lokalnym środowisku. Potwierdzono odcisk RSA odbiorcy, klucze sesji OAEP, uwierzytelnienie AES-GCM, rozpakowanie, SHA nieskompresowanego SQLite, `integrity_check=ok`, `foreign_key_check=0`, **12 z 12 sesji hash-chain** i **770 z 770 indywidualnych SHA rekordów**. Kopie rozszyfrowane były tylko tymczasowe, nie są zapisane w repozytorium. [Raport kontrolny SHA](../data/audits/STEP11_PITCH_NATIVE_TWO_REAL_SNAPSHOTS_20261026.json).

## Wynik porównania pełnych 380 meczów

| Wykryta kategoria zmiany | Liczba |
|---|---:|
| Przesunięte godziny spotkań | **0** |
| Skorygowane wyniki | **0** |
| Zmiany statusu | **0** |
| Zmiany wyświetlanych nazw drużyn | **0** |
| Zmiany jakichkolwiek pól pełnej odpowiedzi źródłowej | **0** |
| Zmiany identyfikatorów meczów lub ID drużyn | **0** |

Hash pełnej listy obu odczytów jest identyczny: `3f68e047863fe6e4c2ffef3b84013fbe121a19b2054503ffa766520c072fc2da`. Poszczególne SHA zaszyfrowanych pakietów i hash-chain różnią się **prawidłowo**, ponieważ oddzielne źródłowe obserwacje mają inne, rzeczywiste czasy i niezależne szyfrowanie. To **rzeczywisty dowód braku zmian w przedziale około 50 minut**; nie twierdzimy, że nie wystąpiły zmiany w innych godzinach ani w kolejnym dniu.

## Udostępniony kod do powtarzania audytu

- `src/kb3_pitch_native_drift.py` — porównanie tylko dwóch odrębnych, uwierzytelnionych źródeł po natywnych ID, bez fuzzy aliasów API-Football. Blokuje nieoczekiwane przepięcie identyfikatorów drużyn i niepełny terminarz.
- `scripts/step11_pitch_native_compare_offsite_zip.py` — **lokalny, offline** odczyt dwóch zaszyfrowanych ZIP, weryfikacja zaszyfrowanej koperty i całej bazy, używa klucza prywatnego tylko na komputerze wykonującym audyt, automatycznie usuwa tymczasowe rozpakowane SQLite, wynik zawiera wyłącznie liczniki i SHA. Nie ma dostępu do API ani przesyłania klucza.
- Poprawiono istotny przypadek w `src/kb3_pitch_native_ledger.py`: funkcja `verify` nie wykonuje już prób zapisu struktury na bazie otwartej w SQLite `mode=ro`. Poprzednie `CREATE TABLE IF NOT EXISTS` mogło błędnie kończyć audyt błędem tylko do odczytu, mimo poprawnych danych. Dodano test otwarcia realnie read-only pliku.
- `tests/test_step11_pitch_native_offsite_zip.py`: sześć testów bezpieczeństwa ZIP, m.in. zakaz dodatkowego jawnego SQLite, niezgodnego manifestu, traversal, nadmiernego rozmiaru i udawania dwóch obserwacji przez dwukrotne wykorzystanie tej samej kopii.

[GitHub Actions #40322588669](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40322588669): **206/206 PASS** — 167 testów Step11 oraz 39 regresyjnych, bez nowych płatnych wywołań dostawcy. Samo źródło drugiego odczytu zostało pobrane osobnym jednorazowym workflow.

## Co dalej blokuje GATE11

- **Wielodniowe obserwacje:** dwa dzisiejsze odczyty nie są dwoma niezależnymi dniami. Następny realny snapshot trzeba zarejestrować po zmianie daty, z prawdziwym timestampem, aby przetestować przełożenia, statusy FT i korekty. Nie wolno backdatować.
- **Całosezonowe pokrycie xG:** 5/5 PL i 12/12 prób UEFA potwierdzają ich próbki, ale nie cały sezon i wszystkie ligi.
- **Oryginalny provider `published_at` nadal nieznany; źródła historyczne 2023–2025 pozostają `RETROSPECTIVE`, nie certyfikowanym prematch PIT.
- **Trening i produkcyjne przełączenie pozostają zabronione.** Bez nowych zakupów, bez zmian w KB Score 2.1, API Market i MultiModel. Formalnie nadal 10/29 zaliczonych etapów.

GATE11: **PENDING**.
