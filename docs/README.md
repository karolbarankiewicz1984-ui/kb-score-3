# Dokumentacja KB Score 3.0

**Źródło prawdy — plan główny i aktualny dziennik odbiorów:** [Google Docs: KB Score 3.0 — Plan główny v1.1](https://docs.google.com/document/d/10wjHL3r3OAuxtezwcIeWztxS8lwjhYon5GM3BLhI0xE/edit).

## Cztery dokumenty robocze

- [PLAN.md](PLAN.md) — kompletna mapa **29 etapów**, zależności, bramki PASS, dowody i statusy.
- [DANE.md](DANE.md) — źródła, pola danych, czas pochodzenia, baza i testy jakości.
- [MODEL.md](MODEL.md) — niezależna metodologia ELO/Poisson/CatBoost, no-lookahead, kalibracja, Champion–Challenger.
- [ZMIANY.md](ZMIANY.md) — rejestr decyzji i protokołów odbioru.

[STEP_03_SECURITY_CHECKLIST.md](STEP_03_SECURITY_CHECKLIST.md) — dokumentacja sprawdzonego testu API-Football/PitchAPI i budżetu.

[STEP_04_ACCEPTANCE.md](STEP_04_ACCEPTANCE.md) — protokół PASS: 4 dokumenty, 29/29 bramek, poprawne linki, postęp 4/29.

[STEP_05_ACCEPTANCE.md](STEP_05_ACCEPTANCE.md) — protokół PASS: rzeczywisty audyt API-Football, 30/30 kombinacji, porównanie niezależnych testów. [Raport pokrycia](audits/API_FOOTBALL_STEP05_2026-10-25.md).


[STEP_06_ACCEPTANCE.md](STEP_06_ACCEPTANCE.md) — **krok 06 PASS**, 60/60 kompletnych próbek xG i 30/30 kombinacji lig i sezonów po dopasowaniu nazwy LaLiga.

[STEP_06_BLOCKER.md](STEP_06_BLOCKER.md) — historyczna blokada HTTP 401, rozwiązana po aktualizacji klucza; nie usuwamy wpisów FAIL.

**Uwaga:** GitHub jest kopią operacyjną. W razie rozbieżności statusu decyduje najnowszy [dziennik na Dysku Google](https://docs.google.com/document/d/10wjHL3r3OAuxtezwcIeWztxS8lwjhYon5GM3BLhI0xE/edit). Nigdy nie deklarujemy ZALICZONO bez odczytanego testu i linku do dowodu. Żaden nowy silnik prognoz nie został jeszcze napisany.

[STEP_07_ACCEPTANCE.md](STEP_07_ACCEPTANCE.md) — **krok 07 PASS**, 38 jednoznacznych przypisań, 22 niezatwierdzone do kontroli, wyniki 17 testów i [trwała mapa](../data/audits/STEP07_MATCH_CROSSWALK_2026-10-25.json). Stan **7/29**.
