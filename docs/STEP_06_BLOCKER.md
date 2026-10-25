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

## Porównanie ze starym repozytorium — diagnostyka klucza, nie dane treningowe

**Kontrola odczytów 25.10.2026: stare repo `kb-score-model` nadal pobiera dane PitchAPI prawidłowo.** Jest to mocna wskazówka, że źródło działa, a usterka dotyczy autoryzacji używanej z nowego `kb-score-3`, lecz nie jest to dowód konkretnej przyczyny.

| Dowód w STARYM projekcie (tylko odczyt) | Zweryfikowane dane | Uwagi |
|---|---|---|
| [Prematch PitchAPI, run 40217313687](https://github.com/karolbarankiewicz1984-ui/kb-score-model/actions/runs/40217313687) | Workflow SUCCESS; etap pobrania z SDK również SUCCESS | [Snapshot 26.10](https://github.com/karolbarankiewicz1984-ui/kb-score-model/blob/main/data/pitchapi/prematch/2026-10-26.json): 38 przyszłych meczów zebranych, 37 z wystarczającą przeszłą historią obu drużyn |
| [Historyczny xG, run 40164885481](https://github.com/karolbarankiewicz1984-ui/kb-score-model/actions/runs/40164885481) | Workflow SUCCESS; 75 meczów zebranych, 67 z kompletnym xG | [Dane 24.10](https://github.com/karolbarankiewicz1984-ui/kb-score-model/blob/main/data/pitchapi/daily/2026-10-24.json). To dane **postmatch**, nie wolno podawać ich jako prematch do tego samego meczu |
| [Porównanie źródeł 24.10](https://github.com/karolbarankiewicz1984-ui/kb-score-model/blob/main/reports/pitchapi/2026-10-24.json) | 21 dopasowanych spotkań do API-Football, 0 rozbieżności wyniku dla dopasowanych | Próbka jednego dnia, nie dowodzi pokrycia pięciu lig × sześciu sezonów |

**Praktyczny wniosek:** przed zakupami i przebudową skryptów należy porównać aktywność klucza w panelu PitchAPI i **przywrócić poprawną wartość `PITCHAPI_API_KEY` w nowym repozytorium**. Nie kopiować surowej wartości przez rozmowę. Jeśli tylko dotychczasowy sekret starego repo działa, a jego wartości nie zachowano, regeneracja może unieważnić klucz w starym repo; najpierw ustalić, czy PitchAPI pozwala dodać drugi klucz, a w razie wymuszonej rotacji zaktualizować obie integracje. Nie wykonywać kolejnych automatycznych prób HTTP 401 bez działań na koncie.

**Stan odbioru niezmieniony:** GATE 06 = BLOKADA / NIEZALICZONY; ogółem 5/29. Historyczne pliki zostały **wyłącznie odczytane**; nie użyto ich do trenowania KB Score 3.0 ani nie zmieniano starego repo.

---

## ZAMKNIĘCIE BLOKADY — 25.10.2026 (NOWSZY WPIS, zachowano historię błędów)

Po wymianie klucza `PITCHAPI_API_KEY` właściciel poprosił o ponowienie. Uruchomiono **attempt 2** [run #40220569321](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40220569321). Część zbierania i walidacji danych przeszła SUCCESS: PitchAPI ponownie działa, katalog 24/30 sezonów, 48/48 kompletnych próbek xG, 14 ścisłych par API-Football, 7/7 testów offline; zero błędów dostawców. Pełny workflow ma status failure **z powodu konfliktu Git push podczas publikacji**, nie z powodu nieprawidłowego klucza. Oryginalny raport JSON+MD został trwale zarchiwizowany na [Google Drive](https://drive.google.com/file/d/1y3z4EdkkNJHb0oiuyFLU5elFVTiJoa_k/view).

**Aktualne rozstrzygnięcie:** blokada autoryzacji ZAMKNIĘTA; **GATE 06 ZALICZONO — 6/29 kroków**. [Nowy protokół odbioru](STEP_06_ACCEPTANCE.md). Wszystkie wcześniejsze próby FAIL pozostają w historii. Następny krok 07 — nie rozpoczęto.
