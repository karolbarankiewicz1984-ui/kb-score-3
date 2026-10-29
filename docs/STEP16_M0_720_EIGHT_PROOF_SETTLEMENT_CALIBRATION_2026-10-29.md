# KB Score 3.0 — krok 16: audyt czasu zamrożenia, rozliczenia i kalibrator 100+50
**29.10.2026 | M0_ELO_POISSON_RESEARCH_720TRAIN_V1 | 8 lig | 15/29, GATE16 PENDING**

## Problem i rozstrzygnięcie
Wcześniej odrębny 8-ligowy M0 720-TRAIN wyliczał niezmienne 1/X/2 i automatycznie rozliczał wynik realnego meczu minimum 3 godziny po kickoff, lecz własny zapis `generated_at_utc`, SHA w SQLite ani `git commit author date` nie dowodzą, kiedy **GitHub** przyjął rzeczywisty blob prognozy. Nie wolno z tego wyliczać fikcyjnych próbek ani dopasować przedwczesnego T.

Dodano osobny audyt publikacji:
1. W działającym `main` pobieramy **prawdziwe PushEvent z GitHub API**, gdzie pole `created_at` pochodzi od serwera GitHub (nie od użytkownika).
2. Weryfikujemy `payload.head` jako rzeczywisty obiekt commit w historii `git`. Odczytujemy **dokładne bajty oryginalnego historycznego pliku SQLite** z tej rewizji, kontrolujemy jego integralność, SHA identycznego rekordu i identyczny stały SHA parametrów M0 720-TRAIN.
3. Zalicza się dopiero wtedy, gdy `captured_at_utc <= github_PushEvent_created_at_utc <= kickoff_utc - 90min`. Nie dopuszcza się dowodów z edytowalnej daty commita, samodzielnej deklaracji `generated_at_utc`, późniejszego dopasowania wyniku, późniejszego nadpisania prognozy ani obcego modelu. GitHub events mogą wygasnąć albo być chwilowo niedostępne — wtedy **brak kwalifikacji, `PENDING`**, nie sztuczna data. To dowód repo-hosted, a nie publikacji źródłowych danych u dostawcy sprzed lat.
4. Osobna append-only tabela `m0720_github_push_proofs` wiąże każdy forecast SHA z eventem, commit SHA i host timestamp. Brak automatycznego oznaczania jako prawdziwy przez Git SHA.

## Rozliczenia bez domysłów
Nadal używany rzeczywisty, dwukrotnie dziennie wywoływany `settle_sqlite` 8-ligowego M0 z poprzedniego wdrożenia; wymaga `finished`, zgodności ID meczu, klubów, kickoff i wyniku 90 min, +3h. Osobny nowy post-process nie zmienia oryginalnej prognozy i nie przepisuje wyników. Zapisuje osobno łączny **Brier sum3**, **log loss** i dodatkowo per-liga wyniki wyłącznie próby z poświadczonym PushEvent. Rozróżnia trzy liczniki: wszystkie freeze, wszystkie settlement i **potwierdzone, rozliczone, dozwolone próbki**.

## Automatyczny kandydat kalibracji tylko po uzyskaniu dowodów
- Strumień jest ściśle przypięty do `M0_ELO_POISSON_RESEARCH_720TRAIN_V1` oraz niezmiennego SHA parametrów. Próbki oryginalnego demonstracyjnego SHADOW nie są włączane.
- Po co najmniej **100 różnych, faktycznie rozliczonych i dopuszczonych** spotkaniach `EARLY` automatycznie dopasowujemy samą **temperaturę T** przy pomocy `src.kb3_step14_m1_math_calibration.fit_temperature`; tylko pierwsze 100 chronologicznie. Nie trenujemy wag Elo, Poissona ani CatBoost.
- Powstaje jeden niezmienny `m0720_calibrators` z SHA 100 identyfikatorów i datą dopasowania. **Nie jest aktywowany produkcyjnie** i nie zmienia surowych prognoz.
- Nowy niezależny holdout powstaje dopiero z **co najmniej 50 nowych prognoz o czasie utworzenia PO dopasowaniu T i kickoff PO dopasowaniu T**, rozliczonych oraz z osobnym dowodem PushEvent; nigdy starsze mecze. Pierwsze 50 chronologicznie jest użyte do jednorazowego sprawdzenia raw vs temperatura na Brier/log loss/ECE. `m0720_holdout_reviews` jest append-only, produkcja zawsze wymuszona jako `production_approved=0`.
- W danych braku dowodu GitHub lub niewystarczającej próby: wskaźniki `missing_to_fit`, `missing_post_fit_holdout`, `eligible_per_league`, `git_server_push_verified_forecasts` i `GATE16 PENDING` są jawne. Nie ma ukrytego przesuwania 100+50, ani dotykania chronionego Premier League TEST.

## Harmonogram, koszty, pliki
Zachowano dotychczasowy cron GitHub Actions: 06:21 UTC zamrażanie, 08:17 i 22:17 UTC rozliczenia. **Brak dodatkowych odczytów PitchAPI** (9 na rozliczenie, 17 na zamrożenie), tylko dostęp przez już aktywny `github.token` do zdarzeń GitHub. Nowy audyt jest dołączony po realnym rozliczeniu, działa na całej lokalnej historii `fetch-depth:0`. Dane źródłowe wyników PitchAPI nadal są szyfrowane; nowe reporty bez tokenu.

Pliki: `src/kb3_step16_m0_720_calibration.py`, `src/kb3_step16_m0_720_eight_forward.py` (połączenie), `.github/workflows/kb3-step16-m0-720-eight-forward.yml`, `tests/test_step16_m0_720_calibration.py`.

## Odbiór
Testy offline wymagają bramek **99→brak T, 100→jeden T, 49 przyszłych→brak review, 50→jeden niezależny review**, SHA i blokad `UPDATE/DELETE`; bez odczytu z sieci podczas PR. Realny run po merge na `main` powinien podać rzeczywiste liczniki dowodów PushEvent oraz rozliczeń. Brak dostępnych zdarzeń GitHub w czasie uruchomienia lub brak faktycznie zakończonych spotkań NIE oznacza fikcyjnego 100/50 ani PASS kroku 16. Do formalnego zakończenia nadal brakuje niezależnego holdoutu i kontroli per-liga, a model nie zostaje Championem.
