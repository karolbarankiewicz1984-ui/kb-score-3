# CODEX-04 — automatyczny freeze, settlement i kalibracja M0-720

**Status: PARTIAL. GATE16 PENDING.** Audyt i poprawki operacyjne przygotowane
do osobnego PR. Nie wykonano poboru live, nowej rzeczywistej prognozy ani
dopasowania kalibratora na danych użytkownika. Nie jest to formalny odbiór
kroku 16. Wymagane pozostaje 100 FIT, następnie 50 nowych prognoz po fit,
rozliczenie niezależnego HOLDOUT oraz formalna decyzja właściciela.

Źródło: main `ad59f8cc3bceb26fea97c937be825d3ee6cde3e6`.
[Rzeczywisty raport](audits/M0_720_OPERATIONS_2026-11-04.json),
[odczytane uruchomienia Actions](audits/M0_720_ACTIONS_OBSERVED_2026-11-04.json).
SQLite SHA256 `af1bd3bebc962490b3ad8765be587152428cb323ad2e65115655caefdf689556`.

## Rzeczywiste liczby i metryki

| Pozycja | Wynik |
| --- | ---: |
| Oryginalne zamrożone prognozy | 91 |
| Prognozy z zapisanym upstream host proof | 91 |
| Rozliczenia i kwalifikujące próbki do FIT | 74 |
| Nierozliczone mecze z przyszłym kickoffem | 17 |
| Potwierdzony zaległy settlement po terminie meczu | 0 |
| Kalibratory / przeglądy HOLDOUT | 0 / 0 |
| Brakuje do pierwszego FIT100 | 26 |
| Niezależne nowe próbki HOLDOUT po fit / wymagane | 0 / 50 |

Nie uznano 17 przyszłych meczów za zaległe ani za próbki FIT/HOLDOUT. Wszystkie
74 kwalifikujące rozliczenia mają spójne oryginalne identyfikatory, hash,
parametry, zegary i zapisany host proof. Odtworzono straty z zamrożonych
prawdopodobieństw i istniejących etykiet: Brier sum3 **0.5618179311**, log loss
**0.9470508062**, accuracy **59.4595%**, ECE5 **0.1509747390**. Brier jest sumą
trzech błędów kwadratowych, nie średnią po trzech klasach.

Host proof sprawdzono ponownie lokalnie; nie pobierano ponownie oryginalnych
bajtów ZIP trzech historycznych artifactów. Ich niezależna autentykacja jest
zaufaniem do wcześniejszego audytu źródłowego, nie nowym certyfikatem tego PR.
Nie odszyfrowano historycznych listingów. Parametry M0 nadal mają SHA
`55310f0e1dd3842e6d876069ef21b1380901b3a6cc6884cf6ec6ea351a5812d1`.

## Co potwierdzono, co było już gotowe

[Draft PR #131](https://github.com/karolbarankiewicz1984-ui/kb-score-3/pull/131)
ma head `ddedb1489251253ade57859d1997a2a615f7a088`: częściowy opis blokady
dziennej oraz prosty backlog inspector bez testów i rzeczywistego odczytu bazy.
Aktualny main ma już lepszy read-only audyt kwalifikacji i metryk; wykorzystano
go zamiast kopiować dawny patch. Istnieją również: deduplikacja SQLite po
natywnym meczu, niezmienne payloady, dopasowanie drużyn, próg +3h, server-time
proof i bramka 100+50. Zachowano te rozwiązania.

Potwierdzone problemy:

1. Trzy sloty forecast istnieją w YAML, ale guard, CLI i jeden dzienny katalog
   blokowały kolejne próby po pierwszym freeze, także gdy powstało 0 nowych
   prognoz. Nowe uruchomienia mają odrębne, niezmienne katalogi; stare dzienne
   pliki pozostają nietknięte.
2. Pierwsze dziesięć przyszłych meczów mogło zawierać już zapisane ID; były
   liczone do quota przed późniejszym dedup w SQLite. Teraz wykluczamy znane
   ID przed historią i limitem. Limit pozostaje **10 nowych / ligę / próbę**,
   nie 10 plus dodatkowy nieograniczony zbiór.
3. Przerwa settlement 8h nie pasowała do slotów 08:17→14:17 (6h). Przerwa 5h
   pozwala wykonać istniejące trzy sloty i toleruje jitter. Nie dodano cronów.
4. Zapis SQLite następował przed dziennym JSON. Awaria publikacji mogła
   pozostawić nowe wiersze bez kompletnego archiwum. Teraz wszystkie pliki
   powstają przed końcowym os.replace bazy; niepowodzenie usuwa wyłącznie nowy,
   nieopublikowany mirror/receipt, zachowując zaszyfrowane źródło i FAILURE.
5. Błędy API nie miały trwałego licznika próby. ATTEMPT/FAILURE są osobnymi
   metadanymi, nie prognozą i nie dowodem kwalifikacji. Timeout nie tworzy
   udanego freeze ani blokady do końca dnia; kolejna próba może być wykonana.
6. SDK 0.1.6 domyślnie ponawiał requesty poza licznikiem. Ten CLI ustawia
   max_retries=0; run odrzuca klienta z ukrytymi retry. Wszystkie 17 odpowiedzi
   pozostają wymagane dla forecast, 9 dla settlement. Nie ma budżetu na retry
   wewnątrz pełnego poboru: ponowienie to nowa, ograniczona próba.
7. Settlement nie sprawdzał pola id samego wyniku niezależnie od klucza mapy.
   Dodano ten warunek i odmowę duplikatów listingów. Równoważny zapis UTC
   (+00:00 zamiast Z) jest akceptowany; rzeczywista zmiana kickoff lub stron
   pozostaje odrzuceniem do przeglądu. Zera wyniku są prawidłowe, brak nie jest zerem.
8. Dodano kontrolę rzeczywistego zegara podczas budowania i bezpośrednio przed
   publikacją, aby opóźnienie obliczeń nie zapisało spóźnionej prognozy.

## Harmonogram i rzeczywiste Actions

Forecast: **06:21, 09:21, 12:21 UTC** (w listopadzie Warszawa 07:21/10:21/13:21).
Settlement: **08:17, 14:17, 22:17 UTC** (09:17/15:17/23:17). Latem lokalne
godziny przesuwają się o godzinę; kod zawsze wymaga UTC.

Odczytano 150 najnowszych rekordów workflowów repo, w tym 12 uruchomień main
tego workflowu. Wszystkie 12 miało SUCCESS; to ograniczony wycinek historii,
nie dowód braku dawnych awarii. Logi potwierdzają m.in. dwa pominięcia
SETTLEMENT_ALREADY_RECENT i źródłowy forecast 03.11 o 14:29 UTC. Ten run
utworzono o 14:28 — ponad dwie godziny po ostatnim nominalnym slocie 12:21.
Nie można rozstrzygnąć, której z trzech planowanych godzin odpowiadał; nie
przypisujemy mu fikcyjnego czasu 06:21. GitHub schedule jest best effort.

Po zmianie: do **3 prób forecast na dzień UTC**, odstęp po sukcesie **2h**,
po błędzie co najmniej **5 min**. Niepoprawny lokalny marker wymaga kontroli,
nie uruchamia kolejnych requestów na podstawie domysłów. Manualny forecast
nie omija limitu. Dla trzech nominalnych slotów maksymalnie 3×17 + 3×9 = 78
wywołań SDK; ręczny settlement pozostaje jawnie osobnym żądaniem. To może
zużyć więcej istniejącego limitu niż poprzedni skuteczny jeden forecast/dzień;
nie jest to zakup planu API. Push kodu odtąd zawsze pomija provider calls.

## Pominięte mecze — granice dostępnego dowodu

Osobny zapisany snapshot XG z 03.11 o 14:37 zawiera 21 przyszłych celów:
17 jest już zamrożonych w M0, cztery niemieckie pozostają niezamarznięte.
Wszystkie cztery mają kickoff 07.11 o 14:30, około 21 sekund **po końcu**
96-godzinnego horyzontu M0 z 03.11 14:29:39. Nie były więc kwalifikujące
w tamtym freeze. Nie uznajemy ich za utracone próbki ani nie rozszerzamy horyzontu.

Pełny historyczny mianownik selekcji pozostaje **nieustalony**: dawne kompletne
listingi są zaszyfrowane i nie odszyfrowano ich w tym audycie. Nie wolno
zastąpić ich późniejszą rekonstrukcją i ogłosić policzonych pominięć. Nowe
receipt'y będą zawierały rozłączne liczniki wszystkich bieżących wierszy
i przyczyny: status, horyzont, lead, znany ID, krótka historia gospodarza/gościa,
quota i opóźnienie publikacji. Settlement analogicznie rozdziela brak wyniku,
maturity, status, zmieniony kickoff/strony, błędny wynik i faktyczny zapis.

## FIT i HOLDOUT

Nie zmieniono progów ani kalibracji M0 w produkcji. Nowy kandydat badawczy
może powstać dopiero z 100 kwalifikujących rozliczeń. Zapisuje dokładne 100 ID
i hash listy; fitted_at oznacza zakończenie dopasowania, nie wcześniejszy cutoff
źródła. Przegląd HOLDOUT zapisuje osobne 50 ID. Prognozy powstałe przed fit
lub dokładnie w jego chwili nie wchodzą do HOLDOUT, nawet jeśli zostaną
rozliczone później. Nie ma automatycznego awansu modelu lub GATE16 PASS.

## Ograniczenia i następne kroki

- Poprawki pokrywają potwierdzone blokady kodu; ich rzeczywisty przyrost próbek
  wymaga późniejszego kontrolowanego live. Nie przeliczono historycznych wyników
  na nowe prognozy. Nie można odzyskać po czasie okazji, której cutoff już minął.
- Awaria przed ostatnim atomowym zapisem pozostawia bazę bez zmian. Twarde
  przerwanie procesu/awaria całego checkoutu lub późniejszy nieudany git push
  nadal wymagają odzyskania z artifactu; nigdy odtworzenia prognozy po kickoffie.
- Nakładanie odrębnych ręcznych procesów poza workflow concurrency nie jest
  nowym wspieranym trybem. Zmiana kickoff wymaga osobnego audytowalnego
  rozstrzygnięcia, bez nadpisywania oryginalnej prognozy.
- Po przeglądzie PR obserwować nowe reason counters, opóźnienia Actions,
  statusy prób i rzeczywisty koszt. Potwierdzić brak duplikatów i zachowanie
  host proof przed kickoff−90min. Przyrostu nie wyliczać z testów syntetycznych.
- Dopiero po FIT100 zebrać 50 nowych po fit, ocenić jakość i uzyskać formalny
  odbiór. W chwili audytu nadal brakuje 26 FIT i wszystkich 50 HOLDOUT.

Oryginalne źródła, wcześniejsze prognozy, manifesty i parametry pozostają bez
zmian w PR. Kontrole SQLite wykonano read-only oraz na kopiach tymczasowych.

## Weryfikacja

Pełna regresja tej gałęzi: **1204/1204 PASS**, 0 failures/errors/skips,
niezależnie Python **3.11.17 i 3.12.14**, w tym **24 nowe testy**. Wcześniejsze
zestawy różnych PR nakładają się — nie dodajemy ich do tej liczby. Runner
blokuje sieć, fit na rzeczywistych danych i zapisy do data/models/config;
wyjątki dotyczą jedynie nazwanych istniejących demo syntetycznych.

Sprawdzono retry, dwa freeze jednego dnia, quota po dedup, stare payloady,
lead i horizon na granicy, UTC/DST, wyniki 0:0, natywne ID/strony, ponowne
rozliczenie, brak wyniku, opóźnienie obliczeń i rollback na kopii rzeczywistej
bazy. Test 99→100→49→50 oraz rozłączne ID FIT/HOLDOUT przechodzi; dodatkowo
prognozy sprzed fit i z dokładnie jego chwili nie stają się HOLDOUT po późnym
settlement. Syntetyczne testy nie są dowodem rzeczywistego przyrostu próbek.

Niezależny odczyt rzeczywistej bazy i przeliczenie raportu na jego dokładnym
czasie audytu: PASS. Brak zmian plików źródłowych, modeli i konfiguracji.
Odbiór live po przeglądzie PR pozostaje wymagany; nie uruchomiono dispatch.

```bash
python scripts/test_m0720_offline.py
python -m scripts.audit_m0720_operations --verify-report docs/audits/M0_720_OPERATIONS_2026-11-04.json
```
