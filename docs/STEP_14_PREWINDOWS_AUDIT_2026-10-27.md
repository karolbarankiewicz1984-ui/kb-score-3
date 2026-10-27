# KB Score 3.0 — prace kroku 14 bez Windows i klucza RSA (27.10.2026)

**Zakres:** rzeczywisty audyt publicznych zapisów i podpisanego SAFE TRAIN+VALIDATION bez żadnych nowych płatnych zapytań PitchAPI. TEST, zamrożone 20 prognoz, M0 i formalny plan 29 etapów **bez zmian**. Certyfikacja pierwotnego historycznego `PIT` pełnych cech nadal blokuje rzeczywisty M1.

## 1. Niezależny realny audyt ryzyka `same kickoff` dla 1140 rekordów

W [GitHub Actions #40576598573](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40576598573) pobrano tylko zamrożone `STEP12_SAFE_MODEL_VIEW_2026-10-26` (760 TRAIN + 380 VALIDATION) oraz zamrożony **bezwynikowy** publiczny OpenFootball (`fa924730da71e3ba24e89a3095f7d4d92de5e71dd252b893bd86cc2e4db53678`). Nie odczytywano surowych wyników, żadnego TEST, bukmachera, RSA ani dwóch natywnych `team_id`. Publiczną datę i czas London BST/GMT przeliczono na UTC, porównując dla każdego z 1140 oryginalnych kickoffów wyłącznie **liczbę** publicznych meczów o tej samej godzinie i w tym samym sezonie.

| Liczba zgodnych po dacie/godzinie kandydatów w OpenFootball | REAL rekordy SAFE 760+380 | Uzasadnienie |
| --- | ---: | --- |
| **Co najmniej dwa** publiczne mecze o tej samej godzinie i sezonie | **647** | Bardzo duże ryzyko błędnego przypisania `fixture_id` do **cudzej pary drużyn** |
| **Dokładnie jeden** publiczny mecz o tej godzinie i sezonie | **492** | Wciąż NIE potwierdza natywnej tożsamości, co udowodniła wcześniejsza pomyłka lipcowej wersji Sunderland–Aston Villa |
| **Zero** publicznych meczów o tej godzinie i sezonie | **1** | Wymaga weryfikacji różnicy czasu, zmiany terminu lub źródła, NIE wolno automatycznie „poprawiać” danych |
| **Suma** | **1140** | Kontrola sum, podziału 760/380 i 0 TEST PASS |

[Zamrożone agregaty](../data/audits/STEP14_REAL_1140_KICKOFF_AMBIGUITY_2026-10-27.json), [kod](../src/kb3_step14_calendar_collision_audit.py), [testy](../tests/test_step14_calendar_collision_audit.py).

**Interpretacja:** 647/1140 NIE oznacza, że 647 rzeczywistych identyfikacji PitchAPI jest błędnych. Tyle rekordów miałoby **niejednoznacznych kandydatów przy niedopuszczalnej metodzie `join` tylko po godzinie**. Po wykonaniu pełnej lokalnej weryfikacji z RSA poprawne dopasowanie będzie wymagało **obu drużyn, sezonu i kickoff**, a ewentualna rozbieżność pozostanie jawnym powodem do wyjaśnienia.

## 2. Znaleziona i naprawiona luka w integralności 1140-wierszowej referencji

Weryfikator przed poprawką sprawdzał wewnętrzny SHA256 publicznego skoroszytu, ale przy hipotetycznej celowej zmianie `home_name/away_name/kickoff` napastnik mógłby też przeliczyć nowy własny SHA i podsunąć fałszywą „zgodną” referencję. Od teraz akceptowana jest **WYŁĄCZNIE pierwotna, niezależnie zamrożona dokładna suma referencji** `fa924730da71e3ba24e89a3095f7d4d92de5e71dd252b893bd86cc2e4db53678`, a także wszystkie trzy oryginalne sumy surowego źródła dla 2023/24, 2024/25 i 2025/26. Dodatkowo kontrolowane są pola `TEST not downloaded`, `no prematch feature release`, bez score/xG/odds. Re-signed tamper test ma zwrócić odmowę. Oryginalne źródło nie zostało zmienione.

[Kod uszczelnienia](../src/kb3_step14_full_identity_pit_audit.py); [8 niezależnych testów projekcji i ataków](../tests/test_step14_public_1140_fixtures.py).

## 3. Przygotowana kontrola późniejszego raportu 1140 RSA, ale bez klucza

Powstał osobny [bezkluczowy analizator `kb3_step14_full_owner_report_review.py`](../src/kb3_step14_full_owner_report_review.py), który po wykonaniu lokalnego odczytu przez właściciela zbada jedynie **same agregaty** przyszłego raportu: 1140, 760/380, 380/380/380, 20/20/20 klubów, brak niezgodnych natywnych identyfikatorów i rol, zgodność sum 1140 publicznych statusów i 60 starych próbek, wrześniową poprawkę, źródłowe PINNED SHA i zachowanie `GATE14 PENDING`. Jeżeli test licznika albo niespodziewanie pokazana prywatna wartość `t_...` / `m_...` nie spełnia reguł, raport zostanie odrzucony. **9 testów pozytywnych/negatywnych** PASS.

Analizator nie odszyfrowuje materiału, nie potwierdza samodzielnie autentyczności wyniku podpisem kryptograficznym i **nie może** podnieść zgody na trening. Przygotowuje tylko kontrolę spójności, dzięki czemu po powrocie do komputera użytkownik wykona jedno wymagane wcześniejsze polecenie, a nie serię improwizowanych nowych prób.

## 4. Niezależny oficjalny GATE14 uruchamiany także na głównej gałęzi

[Workflow `kb3-step14-real-pit-audit.yml`](../.github/workflows/kb3-step14-real-pit-audit.yml) dotąd działał tylko na dawnej gałęzi audytowej. Teraz działa również na **main** i po zmianach kodu walidującego modele lub oryginalnych manifestów Step12 (także manualnie przez `workflow_dispatch`). Przed dotknięciem CatBoost kontroluje w podpisanych rzeczywistych źródłach **760 TRAIN bez przedmeczowego cutoff i 380 VALIDATION bez cutoff**, 0 danych TEST, a po niepowodzeniu **odmawia treningu realnego M1**. [9/9 testów GATE PIT PASS](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40575868016) oznacza **poprawną ochronę i blokadę**, nie akceptację danych.

## Status i następny potrzebny dowód

Oryginalny przebieg właścicielski 4/4 weryfikacji natywnych `team_id` jest faktem z wcześniejszego dnia; **pełne 1140 natywnych par nie zostało odszyfrowane w tym etapie, gdyż prywatny klucz nie jest dostępny w zdalnych narzędziach**. Wszystkie realne audyty w tej zmianie dotyczą wyłącznie jawnych podpisanych manifestów i publicznych terminarzy. Pierwsze publiczne historyczne częściowe FT od 2.10.2024 dla Evertonu i Newcastle nadal są ważnym osobnym dowodem, ale nie uwalniają wszystkich 159 historycznych cech.

**Formalnie: 13/29; krok 14 W REALIZACJI; GATE14 PENDING; certyfikowany TRAIN=0/760, VALIDATION=0/380.** Bez zmian w M0, TEST, 20 wcześniejszych prognozach i bez dodatkowych płatnych zapytań.
