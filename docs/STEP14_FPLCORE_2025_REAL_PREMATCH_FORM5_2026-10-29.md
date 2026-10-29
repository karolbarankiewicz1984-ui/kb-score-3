# KB Score 3.0 / Krok 14 — FPL-Core-Insights 2025/26: rzeczywiste historyczne FORM5, źródło alternatywne xG

**Data wprowadzenia:** 29.10.2026. **Wdrożenie:** izolowany strumień BADAWCZY, bez zmiany oryginalnego M1, 121+38, zamrożonych prognoz i TEST Premier League 2026/27.

## Dlaczego nowe źródło jest użyteczne

Publiczne `olbauday/FPL-Core-Insights` zawiera pliki `data/2025-2026/By Gameweek/GW*/matches.csv` zapisane w trakcie sezonu 2025/26. Nie korzystamy z wersji pobranych po sezonie w lipcu 2026 — tam dokonywano integracji i korekt historycznych statystyk.

Cztery przypięte commity mają **niezależne od autora commita serwerowe zdarzenia GitHub Actions** na publicznej gałęzi `main`. Dowodzi to, że dokładny SHA historycznej zawartości repo był już na `main` **najpóźniej** w danym momencie (nie dowodzi pierwszej publikacji pojedynczego upstream xG):

| Github commit | Github Actions run | GitHub server UTC |
|---|---|---|
| `35932486961bb9a7eb8fbb710ad33ec21a28b1da` | 17822709032 | 2025-09-18 08:24:28 |
| `173bd03f01a9808dbbcf9c42e8ad1112b63429ac` | 19175468717 | 2025-11-07 17:03:33 |
| `59a4cd678579a38b5937bd07afe5635ed3be9e29` | 20642294092 | 2026-01-01 17:04:13 |
| `326b639b21979961dc2a6e1b06db388f8b7431e6` | 22965280628 | 2026-03-11 17:18:18 |

Uznanie daty wymaga zawsze autentycznego odczytu serwerowego `actions/runs?head_sha=...` ze zgodnym `run_id`, `head_sha`, `head_branch=main`, `created_at`, `conclusion=success`, a następnie pobrania dokładnych plików pod tym SHA. Serwerowy dowód nie polega na łatwej do zmiany dacie `commit.committer.date`.

## Audyt rzeczywisty na GitHub Actions

[CI realny — 4+5 testów i audyt](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40860535610) **SUCCESS**, 4/4 serwerowe świadectwa wersji, **18 różnych publicznych przyszłych spotkań** z odtworzonymi FORM5 obu drużyn, w tych samych 18 przypadkach również publiczny wariant xG5/xGA5 z dokładnie pięciu poprzedników obu drużyn. To **18 kandydatów badawczych, nie 18 oficjalnych native-PitchAPI-kwalifikowanych M1 rekordów**. Publiczne wyniki docelowych meczów nie były odczytywane.

W części wersji z 1.01.2026 znaleziono wiersze `finished=True` z kickoff w przyszłości (np. błędnie przypisany do stycznia mecz z sierpnia): **cały plik GW z taką wadą jest odrzucany**, a jego numer i SHA trafiają do raportu. Nie naprawiamy tam dat na podstawie wiedzy z przyszłości. Nigdy nie mieszamy EPL z FA Cup/EFL/Europą. Mecz dopuszczany jako poprzednik tylko, gdy wynik był w opublikowanym przed meczem SHA, mecz odbył się co najmniej trzy godziny przed niezależnym świadectwem, istnieje dokładny home/away i kickoff w niezależnej publicznej referencji bez wyników. Jeśli któregokolwiek z ostatnich pięciu poprzedników brakuje, obie wartości źródłowe FORM5 nie są deklarowane jako kompletne.

## Co faktycznie zostaje wdrożone

- [Skrypt](../scripts/step14_fpl_core_2025_independent_asof.py) — odczyt publicznych historycznych SHA, serwerowe świadectwa, daty, kontrola kompletności, FORM5/P(średnie goli), alternatywne xG i SHA poszczególnych historycznych plików.
- [Testy](../tests/test_step14_fpl_core_2025_independent_asof.py) — blokada fałszywych dat, nieznanych drużyn, przyszłych rozliczeń i niekompletnego FORM5.
- [Workflow](../.github/workflows/kb3-step14-2025-fplcore-historic-asof.yml) — rzeczywiste wywołania historycznych źródeł na PR i `main`, gotowy też do ręcznego uruchomienia; wynik zostaje utrwalony na prywatnym `main` w `data/audits/STEP14_2025_FPLCORE_INDEPENDENT_ASOF_RECOVERY_2026-10-29.json`. Brak nowych płatnych API i szyfrowania.

Dane trafiają do **odizolowanego badawczego audytu historycznego**, nie do tabeli produkcyjnych oryginalnych prognoz, M0 czy TRAIN/VALIDATION oryginalnego M1.

## Granice poprawności i co blokuje GATE14

1. Źródło FPL-Core-Insights (w tym xG) jest **inną semantyką niż natywne PitchAPI team-xG**; jego przechowywanie nie jest dowodem, że 48 oryginalnych pól xG PitchAPI istniało i miało te same wartości. Nawet poprawnie datowany plik nie dowodzi kiedy up-stream obliczył pierwotną wartość.
2. Użyto odrębnej *publicznej* bezwynikowej referencji 2025/26 do dokładnego dopasowania home/away/kickoff; nie mamy jeszcze audytowanego native fixture_id → publiczny wpis dla każdego z 18, więc **0 nowo zatwierdzonych oryginalnych 159-polowych native-PIT**.
3. Odtworzony zestaw obejmuje tylko FORM5 i alternatywne xG5/xGA5; nie obejmuje wszystkich 73 non-xG i 48 xG, brak m.in. kompletnego Elo i FORM10/15 oraz brak oryginalnych receipts per feature.
4. **Oficjalny krok14 pozostaje 13/29 i GATE14=PENDING**. Oryginalny CatBoost M1 nadal nie może być uczony na tych danych. Ewentualne badawcze modele alternatywne muszą mieć własną wersję i niezależny eksperyment; żadnej automatycznej zamiany oryginalnego modelu.

### Oczekiwany następny postęp

Rozszerzyć liczbę historycznych punktów publikacji na więcej kolejek sezonu 2025/26, sprawdzić 380 oryginalnych native par z własnego historycznego audytu identyfikatorów i porównać definicję publicznego xG z PitchAPI; dopiero potem dopuszczać *konkretne cechy w oddzielnym kontrakcie*, nie retrospektywnie przerabiać GATE14.
