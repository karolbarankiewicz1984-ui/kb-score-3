# KB Score 3.0 — Rozpoznanie jednej rozbieżności terminu w 1140 meczach

**27.10.2026, autentyczny wynik lokalny właściciela:**

- 1140/1140 autentycznych fixture_ids PitchAPI, 760 TRAIN i 380 VALIDATION.
- 1139 par gospodarzy i gości **oraz czasu UTC** identyczne z zamrożonym publicznym OpenFootball.
- Dokładnie **1** w `SAME_PUBLIC_TEAM_PAIR_DIFFERENT_UTC_KICKOFF`: **pary klubów zgadzają się**, ale **dokładny termin UTC się różni**.
- Nie wiadomo na podstawie agregatu, którego meczu, jakiej daty i o ile minut dotyczy niezgodność. **Nie wolno utożsamiać jej automatycznie z wcześniejszym osobnym przypadkiem Bournemouth–Newcastle**; on dotyczył niezależnego lipcowego, starszego snapshotu.
- W niezależnej próbce 60 historycznych archiwalnych wersji: 3 potwierdzone zgodności z serwerowym czasem publicznego PushEvent; 30 jedynie ze starą datą commita (bez niezależnego czasu publikacji); 5 bez tej samej pary drużyn w historycznej wersji; 21 bez archiwalnego prematch commita; 1 osobno udokumentowana zmiana terminarza. **Te statusy mówią o ówczesnym źródle, NIE o bieżącej dokładności identyfikacji 1140 rekordów.**

## Bezpieczne ustalenie jedynego rozbieżnego meczu

Do projektu dodano **nowy właścicielski lokalny program** [`scripts/step14_explain_one_kickoff_local.py`](../scripts/step14_explain_one_kickoff_local.py). Uruchamiany na Windows z **tym samym oryginalnym ZIP + prywatnym PEM**, co wcześniej pomyślny audyt. Program ponownie weryfikuje oryginalny ZIP/chain i oryginalny bezwynikowy indeks SAFE (nie korzysta z TEST), lokalnie odszyfrowuje prywatne źródło i wymaga ścisłej struktury **1139 EXACT + 1 SAME_PAIR_DIFFERENT_KICKOFF**. Wypisuje na ekranie wyłącznie **sezon, rolę TRAIN/VALIDATION, publiczne nazwy gospodarza i gościa, oryginalny czas PitchAPI UTC, drugi czas OpenFootball UTC i dokładną różnicę minut**. **Nie wypisuje `fixture_id`, żadnego natywnego `team_id`, wyników, kursów, RSA i nie zapisuje nowego pliku.** Pozostawia oryginalne dokumenty i modele niezmienione.

Z aktualnego katalogu projektu:

```powershell
py -3 -m scripts.step14_explain_one_kickoff_local --archive-zip "$HOME\Downloads\KB3_PITCH_PL_2023_2026_NATIVE_20261026.zip" --private-key "$HOME\Desktop\KB3_760_PAKIET_ODZYSKIWANIA_POUFNE\KB3_760_KLUCZ_ODZYSKIWANIA.pem"
```

Przed uruchomieniem trzeba pobrać **aktualną wersję repozytorium po scaleniu** [PR #63](https://github.com/karolbarankiewicz1984-ui/kb-score-3/pull/63) i wejść PowerShellem do folderu z `scripts` oraz `src`. Jeżeli rzeczywista zawartość różni się od 1139+1 albo SHA zamrożonego źródła, narzędzie **odmawia** zamiast zgadywać.

[GitHub Actions #40592656646](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40592656646) PASS 6/6 **wyłącznie na syntetycznych przykładach** oraz walidacja składni lokalnego skryptu. GitHub Actions **nie ma i nie użył prywatnego RSA**, więc prawdziwa para nazw i obie godziny nadal są do wyświetlenia jedynie na komputerze właściciela. Po otrzymaniu wyniku z tego programu można zbadać niezależne oficjalne źródła zmiany daty oraz ustalić, czy konflikt pochodzi z DST, rescheduling czy innej redakcji danych. Nie wolno automatycznie przepisywać pierwotnego PitchAPI ani OpenFootball.

## Bramka PIT modelu niezmieniona

**GATE14 PENDING, 13/29, PIT TRAIN 0/760, VALIDATION 0/380**. Poprawna identyfikacja meczu nie poświadcza 121 pól danych liczbowych i 38 znaczników braków przed historycznym kickoffem. Brak ingerencji w CatBoost M1, M0, zamrożone 20 prognoz, TEST 2026/27 i brak nowych płatnych wywołań PitchAPI.
