# Krok 14: rzeczywiście opublikowane wcześniejsze wyniki przed wybranymi meczami (27.10.2026)

Niezależne **GH Archive PushEvent** z serwerowym czasem udostępnienia i SHA publicznego `openfootball/football.json` pozwoliły sprawdzić autentyczną dostępność **części wyników wcześniejszych spotkań** jeszcze przed trzema historycznymi meczami. To jest ważniejszy dowód niż samotne `commit.committer.date`, ale nie może być mylony z poświadczeniem kompletnego PIT 121 cech modelu z historycznego PitchAPI.

## Wykonanie realne

[GitHub Actions #40546191857](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40546191857) **PASS, 7/7 testów** i realne pobranie **konkretnych starych blobów** przypiętych do ich oryginalnego SHA256 z audytu `STEP14_HISTORICAL_BLOB_60`. Repo `openfootball/football.json` było wtedy publicznie dostępne dzięki niezależnym zdarzeniom archiwum GH Archive.

| Historycznie publiczne źródło | Data publicznego PushEvent UTC | Wynik FT dostępny dla wcześniejszych meczów w starym pliku | Możliwość odtworzenia części formy |
| --- | --- | ---: | --- |
| `5f777dc6e2cd…`, Premier League 2024/25 | **2024-10-02 13:52:44** | **60** wcześniejszych meczów | Dla Everton–Newcastle zaplanowanego na 05.10: **po 6 zakończonych wyników obu drużyn**, czyli dostępne wejścia do wyliczenia formy z poprzednich 5 spotkań |
| `fdca227e6fc8…`, Premier League 2025/26 | **2025-07-30 16:20:53** | **0** (sezon jeszcze się nie rozpoczął) | Nie zapewnia żadnych wyników z nowego sezonu dla Leeds–Everton (18.08) ani Liverpool–Arsenal (31.08) |

Dwa użyte wówczas SHA plików to `6687e626fd7361ae771308920b289392229c36f6bdffee0b56b7e9235815e3de` (sezon 2024/25) oraz `ba32190faf6aad0558d9e919344db6be6abe6e4ce733168b7efc40427771962b` (2025/26). Dla meczu `m_0JJdwI` oryginalny lipcowy blob wskazuje inną parę Sunderland–Aston Villa; po udokumentowanym późniejszym przełożeniu Bournemouth–Newcastle nie wolno przypisywać lipcowego wyniku/scheduled match do tego ID.

Algorytm sprawdził, że w dawnych blobach **nie ma wyniku spotkania docelowego**, a wszystkie policzone 60 wyników pochodziło ze spotkań z datą **wcześniejszą niż moment opublikowanego PushEvent**. Raport [`STEP14_EARLY_PUBLIC_PREMATCH_FT_2026-10-27.json`](../data/audits/STEP14_EARLY_PUBLIC_PREMATCH_FT_2026-10-27.json) zapisuje tylko liczniki poprzedników oraz czasy i SHA, nie eksportuje wyników bramek docelowych ani wyników TEST.

## Ważne rozgraniczenie

**Tak:** dowiedliśmy faktycznej dostępności na publicznym GitHub **w dniu 02.10.2024 przed kickoff 05.10** wyników FT pewnych wcześniejszych spotkań, z których można zrekonstruować część prostych statystyk formy oraz historycznych goli Evertonu i Newcastle.

**Nie:** nie wiemy z tego źródła, kiedy PitchAPI oryginalnie opublikował pełne historyczne statystyki; nie ma w tym dawnym pliku pełnego historycznego xG, kompletnej certyfikacji Elo z właściwym parametrem i wcześniejszymi sezonami ani kompletnej kontroli wszystkich 159 dowodów Step11. Nie wolno więc na tej podstawie używać całego przykładu jako `PIT_CERTIFIED_TRAIN` ani dopuszczać formalnego M1.

**Status formalny:** zero pełnych certyfikowanych przykładów historycznego TRAIN 760 / VALIDATION 380, GATE14 PENDING, 13/29, TEST, M0 i 20 zamrożonych prognoz nietknięte. Dane publiczne z potwierdzoną datą mogą w przyszłości tworzyć **odrębne, indywidualne dowody dla konkretnych poprzednich wyników** zamiast obniżać wymóg dowodu dostępności całego modelu.
