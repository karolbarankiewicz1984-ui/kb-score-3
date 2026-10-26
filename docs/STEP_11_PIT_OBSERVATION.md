# KB Score 3.0 — Krok 11: pierwszy trwały zapis rzeczywistej obserwacji PIT

**Data:** 26.10.2026. **Stan:** częściowy test `PASS`, **GATE11 nadal PENDING (10/29)**. Nie trenowano ani nie generowano typów.

## Czego dokonano

- Zbudowano **osobny** od historycznej bazy 760 meczów dziennik obserwacji `src/kb3_pit_ledger.py`, który przechowuje 380 kanonicznych rekordów oraz całą treść oryginalnej odpowiedzi API-Football, hash SHA-256 każdego rekordu i łańcuch hashy sesji. Triggery SQLite blokują UPDATE i DELETE. Weryfikator wykrywa późniejsze uszkodzenie rekordu lub odpowiedzi. Ostateczny hash został zakotwiczony w [trwałym zbiorczym manifeście](../data/audits/STEP11_PIT_LIVE_CAPTURE_2026-10-26.json).
- [GitHub Actions #40296430026](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40296430026) **SUCCESS**: po 9/9 testach w trybie offline wykonano jedno prawdziwe pobranie `fixtures?league=39&season=2026`. Odnotowano okno rzeczywistego wykonania **09:01:48.745533–09:01:49.018457 UTC 26.10.2026** na zegarze środowiska GitHub Actions.
- Uzyskano **380/380** spotkań Premier League 2026/27: **80** zakończonych, **300** z datą rozpoczęcia jeszcze w przyszłości. Zapisano pełną treść odpowiedzi, ale surowe rekordy nie zostały opublikowane w GitHub ani w jawnym artefakcie.
- Dziennik zaszyfrowano publicznym kluczem dotychczasowego odbiorcy (RSA-3072/OAEP-SHA256 + losowy AES-256-GCM) i zapisano jako [prywatny plik ZIP na Google Drive](https://drive.google.com/file/d/1wvFMLiSQHUP06-r95iNwp9nyBfYbsBoP/view?usp=drivesdk), **55 922 bajty**. ZIP zawiera jedynie zaszyfrowaną SQLite, manifest i niefikcyjny zbiorczy receipt. Klucz prywatny nie został przesłany do Drive ani GitHub.
- Kopię **pobrano ponownie z Google Drive** i niezależnie odszyfrowano tym samym kluczem odzyskiwania, który posłużył do archiwum 760 z poprzedniej części kroku 11. Zgodny SHA-256 ZIP `04b7e3927186a4ef1412ae48954716619b57a2e5eac697f692458edfb9cd4845`, zgodny SHA szyfrogramu, `PRAGMA integrity_check=ok`, `foreign_key_check=0`, 380/380 poprawnych hashy rekordów i łańcuch sesji. Zaszyfrowany plik istnieje niezależnie od wygasających artefaktów GitHub Actions.
- Po zakończeniu audytu dołączono test sytuacji, w której **nowszy snapshot zmienia wynik na odroczony** — w takiej sytuacji starszy wynik FT nie może wrócić jako prawidłowy. Testy obejmują także odrzucanie backdatingu, syntetycznej historii, błędnych przedziałów czasu, zmian treści, naruszenia niezmienności i szyfrogramu.
- [Końcowy test offline #40296978637](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40296978637) **SUCCESS**: **43/43 testy Step11**, **39/39 regresji (GATE08–10)**, łącznie **82/82**. W tym uruchomieniu zadanie dostawcy jest świadomie wyłączone, ponieważ nowa sesja sieciowa wymaga ręcznego uruchomienia workflow, by nie marnować limitów API.

## Interpretacja historycznej dostępności — kluczowa

`captured_at_utc` to **rzeczywisty czas zakończenia odczytu** według zegara hosta. Nie oznacza czasu **pierwotnego opublikowania** rekordu przez dostawcę; `source_published_at_utc = NULL` / `UNAVAILABLE`.

- **A — NETWORK_OBSERVED:** treść pojedynczej odpowiedzi zaobserwowana i zabezpieczona 26.10.2026 09:01:49 UTC. Można badać ją jako wejście do **późniejszego** cutoff z kontrolą czasu i statusu zakończenia. Sam ten fakt nie pozwala ogłosić certyfikowanego historycznego backtestu ani treningu.
- **B — RETROSPECTIVE:** poprzednie archiwum 760 meczów sezonów 2023/24–2024/25; zapis z roku 2026 nie nadaje mu wstecznego PIT. Tylko ostrożne replay, ze znanymi ograniczeniami.
- **C — UNKNOWN / QUARANTINED:** nieudowodniona pierwotna publikacja, niezgodna lub niezatwierdzona para PitchAPI, brak xG, rewizja wyników lub źródło bez przechwyconej treści. Nie promować do A.

`select_result_asof` zwraca rezultat **wyłącznie** ze zdarzenia `NETWORK_OBSERVED` zakończonego przed forecast cutoff, z wcześniejszego zakończonego meczu i prawidłowym wynikiem FT w **najświeższej** zaobserwowanej wersji. Nowsza poprawka może unieważnić wcześniejszy wynik. Żaden odczyt nie ustawia `training_allowed=true` ani nie dodaje prognozy.

## Warunki następnej fazy kroku 11

1. Dopasować kanoniczne ID z przyszłej historii i udowodnić spójność wielu obserwacji tego samego źródła w kolejnych dniach, także po odroczeniu lub korekcie wyniku.
2. Oddzielnie przechwytywać i archiwizować prawdziwe xG po zakończeniu spotkań z zatwierdzonymi identyfikatorami, z datą pobrania, brakami NULL i ścisłym cutoff; nie wnioskować dat publikacji z dat meczów.
3. Opracować audyt czy i kiedy w ogóle można promować spójny `feature_snapshot` na `VERIFIED_PREMATCH` (kontrola źródła, treści, czasu, kompletności, cutoff i tożsamości), bez nazywania dzisiejszych danych certyfikowanym historycznym backtestem.
4. Do czasu niezależnego odbioru utrzymać `GATE11=PENDING`, `training_allowed=false`; nie ruszać starszych KB2.1/API Market/MultiModel.

**Przechowywanie:** użyto istniejącego abonamentu API, bez dodatkowego zakupu. Udostępnianie surowych danych musi pozostać zgodne z licencją dostawcy. Nowe pobrania API są ręcznym `workflow_dispatch`, a nie automatycznym harmonogramem.
