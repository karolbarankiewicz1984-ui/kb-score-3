# KB Score 3.0 — KROK 06: diagnostyka PitchAPI (BLOKADA)

**Data:** 2026-10-25. **GATE 06: BLOKADA / NIEZALICZONY.** Postęp projektu: **5/29**.

## Dlaczego audyt nie jest zakończony?

Dostęp PitchAPI nie przeszedł autoryzacji przy pobieraniu `GET /v1/leagues`. Nie ma podstaw, by raportować historyczne xG, dostępność sezonów ani dopasowane mecze jako sprawdzone.

| Próba | Dowód | Testy lokalne | Wynik usług |
|---|---|---|---|
| Odczyt HTTPS z nagłówkiem `X-API-KEY` | [Run #40220277718](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40220277718) | PASS | Katalog: **HTTP 401**, 0 meczów, 0 xG |
| Oficjalna biblioteka Python PitchAPI | [Run #40220451559](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40220451559) | PASS | Katalog: **SDK_AuthError**, 0 meczów, 0 xG |

Szczegół błędu pierwszej próby pochodzi z archiwum artefaktu ID `12609056822`: `provider_errors.pitchapi: /v1/leagues HTTP_401`. Nie odczytywano wartości klucza. Wcześniej, w [KROKU 03](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40203074557), ten sam typ połączenia z nowego repozytorium działał i zwrócił HTTP 200. Przyczyna zmiany nie jest jeszcze znana (np. rotacja/wygaśnięcie klucza lub problem po stronie usługi). Nie zakładać konkretnej przyczyny bez dowodu.

Oficjalna dokumentacja https://pitchapi.dev/ podaje: **401 UNAUTHORIZED = brak lub nieprawidłowy klucz w nagłówku `X-API-KEY`**. Jest to inny stan niż HTTP 429 (ograniczenie częstości) i niż problem Cloudflare 403. Dostawca opisuje plan bez opłat, ale aktualnego pokrycia z konta nie można potwierdzić bez działającej autoryzacji.


## Dodatkowy test rozróżniający błąd SDK i HTTP

- [Run #40220569321](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40220569321), 25.10.2026: **7/7 testów offline PASS; PitchAPI katalog FAIL**. Oficjalny SDK: `SDK_AuthError`, niezależna próba HTTPS: `HTTP_401_CLOUDFLARE`, bez wykrytego kodu blokady CF 1010.
- Oba odczyty używały prywatnego sekretu `PITCHAPI_API_KEY` z NOWEGO repozytorium; żaden klucz nie został ujawniony w logu. Nagłówek serwera Cloudflare jest informacją o obsłudze żądania, a nie samodzielnym dowodem blokady WAF.
- PitchAPI dokumentuje HTTP 401 jako brak lub nieważność klucza. Dalszych automatycznych prób **nie uruchamiać przed weryfikacją/aktualizacją sekretu**. Dodatkowy audyt nie pobrał żadnego meczu ani xG.

## Bezpieczne działania właściciela

1. Otworzyć panel kluczy na oficjalnej stronie [PitchAPI](https://pitchapi.dev/) i sprawdzić aktywność klucza; w razie potrzeby wygenerować/odświeżyć klucz, bez zakupu abonamentu.
2. W nowym prywatnym repozytorium GitHub otworzyć [Actions secrets](https://github.com/karolbarankiewicz1984-ui/kb-score-3/settings/secrets/actions) i **zaktualizować istniejący** `PITCHAPI_API_KEY` na aktywną wartość. Nie wklejać klucza do rozmowy, Issue, commitu, pliku repo ani logu.
3. W [Actions](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions) ponowić ręcznie workflow **KB3 Step 06 - PitchAPI historical xG coverage** (`workflow_dispatch`) na gałęzi `main`. Odpowiedzi z katalogu i strzałów powinny zostać udokumentowane w raporcie.
4. Udostępnić wyłącznie URL wyniku testu (bez sekretów). Następnie przeprowadzić GATE 06, odczyt próbek i kontrolę jakości porównań z API-Football.

## Kryteria zaliczenia, wciąż do wykonania

- [ ] Katalog `/v1/leagues` działa z nowego repozytorium.
- [ ] Weryfikacja sezonów dla 5 lig na rzeczywistych odpowiedziach konta.
- [ ] Reprezentatywne przykłady meczów i **rzeczywiste wartości xG pojedynczych strzałów**.
- [ ] Bezpieczne, nieprzeszacowane parowanie przykładowych spotkań z API-Football i wskazanie niejednoznaczności.
- [ ] Jawne `BRAK` zamiast 0 i ograniczenia dostępności historycznej.
- [ ] Zarchiwizowany raport, identyfikatory próbek, wynik testów PASS oraz protokół odbioru w Google Docs.

**Nie kupowano nowych usług i nie trenowano modelu.** Krok 07 nie jest jeszcze rozpoczęty. Źródło prawdy: [Plan główny KB Score 3.0](https://docs.google.com/document/d/10wjHL3r3OAuxtezwcIeWztxS8lwjhYon5GM3BLhI0xE/edit).
