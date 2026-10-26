# KB Score 3.0 — GATE11: rozszerzony, rzeczywisty audyt xG z trzech lig (PitchAPI)

**26 października 2026 • częściowy PASS, cały GATE11 nadal PENDING (10/29).** Krok 11 kontynuowany bez treningu, typowania i przełączania produkcji. Jeden dostawca danych sportowych: **PitchAPI**.

## Wynik niezależnego odczytu

[GitHub Actions — zakończony, poprawny realny odczyt #40334387182](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40334387182).

| Rozgrywki 2026/27 | Mecze w źródłowym terminarzu | Zakończone i kwalifikujące się | W próbie | Kompletne xG | Różne daty spotkań |
|---|---:|---:|---:|---:|---:|
| Premier League | 380 | 80 | 10 | **10/10** | 10 |
| Liga Europy | 144 | 54 | 10 | **10/10** | 4 |
| Liga Konferencji | 108 | 36 | 10 | **10/10** | 2 |
| **Razem** | **632** | **170** | **30** | **30/30** | — |

Wszystkie 30 feedów strzałowych zawierało kompletne xG obu drużyn. Każda para wynik/statystyka została powiązana po **tym samym natywnym PitchAPI.match_id** i zweryfikowanych natywnych ID drużyn. Zero zapytań do API-Football, zero fuzzy matchingu. W nowym pełnym odczycie **34 wywołania PitchAPI**: 1 katalog, 3 listy rozgrywek, 30 feedów strzałowych.

Próbki wybierano *deterministycznie z rozłożeniem chronologicznym*. **Nie są losowe** i nie obejmują wszystkich 170 zakończonych meczów. W szczególności dostępne rozegrane mecze Ligi Konferencji pochodzą tylko z **dwóch różnych dat**, więc nie można wymagać trzech niezależnych dat w takim teście. Wskaźnik Wilsona 0,7225 dla 10/10 byłby dolną granicą 95% tylko przy stosownym losowym planie próbkowania; tego warunku nie spełniono i **nie wolno** używać go jako potwierdzenia pełnej dostępności xG w lidze.

### Rozszerzenie poprzedniego audytu

Ponownie niezależnie odszyfrowano [wcześniejsze 12 próbek UEFA](https://drive.google.com/file/d/1LdmMRLmtaObUK7gs9r55D6950jTMCwxF/view), porównano ich **oryginalne** natywne ID meczów z nowymi 20 próbkami UEFA. W każdej z dwóch lig UEFA występują **dwa powtórzone spotkania**. Łącznie mamy więc po **14 różnych, kompletnych spotkań** Ligi Europy i Ligi Konferencji, a dodając 10 z nowej Premier League — **38 unikalnych spotkań, 38 z kompletnym xG** w tym potwierdzonym zbiorze. Nie liczymy tej samej obserwacji źródłowej dwukrotnie jako nowego meczu.

Przy zwiększaniu liczby meczów nadal potrzebny jest pełniejszy audyt pokrycia sezonowego i późniejszych faz rozgrywek. Nie deklarujemy „100% pokrycia UEFA”.

## Dowód offsite i rzeczywiste odtworzenie

[Zaszyfrowana kopia 34 źródeł na prywatnym Google Drive](https://drive.google.com/file/d/1ddByW04Sw3bDLxq-h2P-HyvwRtuBI423/view).

- ZIP: **94 686 B**, SHA-256 `95db06fdca31c23c67a3625208d2675a3a882bb86b4dd29ca11f97fccb2d5906`.
- Uwierzytelniony szyfrogram: **92 687 B**, SHA-256 `a355808c5ba2890d4470de7d36429513820cc439d3e8db61a5c2c80a182653db`.
- SHA ostatniej sesji źródła: `6f45ad3e66df9347d2d93818dc6bc995eed976b1eb4b81336637710724809648`.
- Po **ponownym pobraniu z Google Drive** wykonano niezależne odszyfrowanie RSA-OAEP/AES-256-GCM dotychczasowym prywatnym kluczem właściciela poza GitHub. RSA fingerprint, AES-GCM authentication, oryginalny SHA rozpakowanych **888 578 B**, **34/34** indywidualne źródłowe hashe i **34/34** ogniwa hash-chain przeszły PASS.
- Wszystkie **30/30** oryginalnych odczytów strzałów ponownie połączono z meczem po natywnym ID i z właściwymi dwoma team IDs, niezależnie od CI; każdy otrzymał `COMPLETE_SHOT_XG`.
- Klucz prywatny oraz niezaszyfrowane odpowiedzi API nie trafiły do repozytorium ani do raportu. [Manifest bez surowych danych](../data/audits/STEP11_THREE_LEAGUES_XG30_OFFSITE_2026-10-26.json).

## Ograniczenie kosztu i poprawka kontroli

Pierwszy realny odczyt [#40334130610](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40334130610) wykonał 34 zapytania i otrzymał **30/30** kompletnych xG, ale późniejsza asercja błędnie oczekiwała minimum trzech dat we wszystkich ligach. Liga Konferencji miała **dwie rzeczywiście dostępne daty**, więc workflow zakończył się błędem i nie zachował artefaktu źródłowego.

Poprawiono warunek na minimum dwie daty oraz dodano **`if: always()` do uploadu zaszyfrowanych danych**. Uruchomiono drugi, poprawny odczyt [#40334387182](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40334387182), aby otrzymać trwały kryptograficzny dowód. **Łącznie wykonano 68 zapytań PitchAPI w dwóch próbach.** Nie kupowano nowego abonamentu. Ten koszt dodatkowych zapytań jest ujawniony, a nie ukryty w liczniku 34.

## Testy i status bramki

- `scripts/step11_pitch_three_league_xg30_once.py`: ograniczenie do 34 wywołań, odrzucanie błędnych ID i statystyk, źródłowy hash-chain, AES-256-GCM + RSA-OAEP, raport zbiorczy bez danych prywatnych.
- `tests/test_step11_pitch_three_league_xg30.py`: osiem nowych testów kontroli kosztu, formatu ligi, stabilności natywnych ID, selekcji 10 meczów, niedopuszczalności zamiany brakujących xG na zero i statystycznego ograniczenia doboru próby.
- [Pełne CI #40334026441](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40334026441): **239/239 PASS** (200 Step11 +39 starszych). Sieciowe zadanie legacy API-Football **SKIPPED**; jedynie osobny ograniczony workflow wykonał odczyty PitchAPI.

**Stan GATE11: PENDING, 10/29 etapów formalnie zaliczonych.** Pozostają prawdziwy snapshot w **innej dacie kalendarzowej**, porównanie między dniami, szersza obserwacja kompletności nowych spotkań i końcowy podpisany audyt. Każda analiza chronologiczna nadal wymaga `source observed_at <= cutoff < kickoff`. Nikt nie zna oryginalnego `published_at` dostawcy dla historycznych danych. Trening i typy pozostają zabronione; stare modele nienaruszone.
