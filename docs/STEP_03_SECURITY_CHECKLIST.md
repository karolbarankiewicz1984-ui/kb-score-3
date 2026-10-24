# Krok 03 — Secrets, limity i budżet

Status: W REALIZACJI / GATE 03: PENDING. Nie uruchomiono testu w GitHub Actions. Brak nowych zakupów.

## Co jest już gotowe
- Prywatne repozytorium `kb-score-3` ze strukturą (krok 02 PASS).
- Workflow tylko ręczny: `.github/workflows/kb3-step03-secrets-smoke.yml`.
- Zakres: **dwa odczyty GET** — API-Football `/status` i PitchAPI `/v1/leagues`.
- Uprawnienia workflow tylko `contents: read`, limit 4 minut, bez harmonogramu i zapisu danych, bez wypisywania sekretów.

## Działania właściciela konta (nie wklejać żadnych kluczy w ChatGPT)
1. Otwórz https://github.com/karolbarankiewicz1984-ui/kb-score-3/settings/secrets/actions
2. Kliknij **New repository secret**; nazwa `API_FOOTBALL_KEY`; wklej wartość klucza ze swojego panelu API-Football i zapisz.
3. Powtórz z nazwą `PITCHAPI_API_KEY`; wklej klucz z konta PitchAPI.
4. Otwórz https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions i wybierz **KB3 Step 03 - API access smoke test** → **Run workflow** → **main**.
5. Po zakończeniu wejdź w uruchomienie, otwórz **Summary**. Oczekiwane: API-Football PASS HTTP_200_JSON oraz PitchAPI PASS HTTP_200_JSON. Przekaż wyłącznie LINK DO URUCHOMIENIA, nigdy klucz.
6. Otwórz https://github.com/settings/billing → Budgets and alerts i zweryfikuj: bieżące użycie i pozostałą pulę Actions, budżet dodatkowych wydatków dla Actions i alerty. Jeżeli `Stop usage when budget limit is reached` jest dostępne i zależy Ci na sztywnym limicie, zaznacz je. W razie zmian kosztów poproś o osobne zatwierdzenie.
7. Sprawdź limit w panelu API-Football https://dashboard.api-football.com/profile?access (stan liczników się zmienia). Nie udostępniaj zrzutu zawierającego niezamaskowany klucz.

## Kontrola GATE 03
- [ ] Istnieją oba sekrety w *tym* repozytorium; nie zakładamy ich odziedziczenia z KB 2.1.
- [ ] Ręczny test GitHub Actions zakończył się **success**; oba wiersze PASS.
- [ ] Wynik smoke testu zawiera tylko status i rodzaj błędu, a nie klucze i dane konta.
- [ ] Skan plików repo i logów przebiegu nie ujawnia sekretów.
- [ ] Aktualny budżet/limity/alerty zostały potwierdzone przez właściciela.
- [ ] W dzienniku głównego planu wpisano wynik, datę i link do dowodu.

Błąd HTTP 403 lub 1010 z PitchAPI może wskazywać blokadę WAF; nie traktuj go automatycznie jako nieprawidłowego klucza. W takim przypadku wpisz FAIL i przeprowadź diagnostykę, bez ujawniania sekretów.

## Źródło prawdy i kolejny krok
Pełny plan: https://docs.google.com/document/d/10wjHL3r3OAuxtezwcIeWztxS8lwjhYon5GM3BLhI0xE/edit

Krok 04 (pełna dokumentacja metodologii) jest nadal NIE ROZPOCZĘTY.
