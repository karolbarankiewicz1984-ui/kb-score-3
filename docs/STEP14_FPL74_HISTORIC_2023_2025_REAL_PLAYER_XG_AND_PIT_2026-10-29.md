**KOREKTA — obowiązujący wynik to 40 historycznie poświadczonych ALTERNATYWNYCH xG5 TRAIN, nie 31.** W trzech starych plikach FPL 2024/25 od GW22 występowało 49 pól przy starym nagłówku 42 pól; skorygowano format z zachowaniem oryginalnych SHA. Pełna [obowiązująca dokumentacja v2](STEP14_FPL74_HISTORIC_REAL_XG_CORRECTED_40_TRAIN_2026-10-29.md). Ten dokument v1 zachowano jako audyt historyczny.

# KB Score 3.0 — etap 14: 74 rewizje FPL 2023/24–2024/25 i prawdziwe archiwalne xG

**29.10.2026.** Ostatnie zatwierdzone wykonanie testowe: [GitHub Actions #40895972167](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40895972167) — **SUCCESS**. Kod wdrożony przez [PR #96](https://github.com/karolbarankiewicz1984-ui/kb-score-3/pull/96).

## Wynik wykonania na rzeczywistych starych danych

| Element | Wynik |
| --- | ---: |
| Historyczne rewizje `fixtures.csv` odczytane z publicznego repo FPL | 38 (2023/24) + 36 (2024/25) = **74** |
| Rewizje dowiedzione jako przodkowie niezależnie datowanych starych publicznych zdarzeń GH Archive | **74/74** |
| Oryginalne TRAIN z publicznym, historycznie przedmeczowym FORM5 obu drużyn | **54/760** (bez przyrostu wobec poprzedniego audytu) |
| TRAIN z historycznym kompletnym **alternatywnym** player-sum xG5/xGA5 | **31** |
| VALIDATION z przedmeczowym FORM5 | **109/380** (bez zmian) |
| VALIDATION z kompletnym alternatywnym xG5 | **107/380** (bez zmian) |
| Cała odizolowana research macierz | **1140×159** (121 liczb i 38 flag, plus osobne 19 pól retro-Elo) |
| W pełni certyfikowane oryginalne natywne PIT M1 TRAIN / VALIDATION | **0/760 + 0/380** |
| Formalny GATE14 | **PENDING**, CatBoost M1 oryginalny **nie wytrenowany** |

### Jak udowodniono publikację 74 źródeł

Zamiast traktować łatwą do manipulowania datę `git committer` jako czas publikacji, dla każdej rewizji sprawdzono jej autentyczne miejsce w **grafie przodków commitów Git**: musi być przodkiem historycznej rewizji `main`, której istnienie poświadczono **niezależnie datowanym, oryginalnym GH Archive PushEvent**. Przyjęty zegar rewizji to konserwatywna data **najwcześniejszego tak poświadczonego potomka**.

Jest to dowód istnienia SHA nie później niż data poświadczonego potomka, **nie** dowód pierwotnej daty opublikowania każdego z 74 commitów. Ta ostrożność wyjaśnia, dlaczego przetworzenie wszystkich 74 rewizji **nie** powiększyło liczby rygorystycznie kwalifikowanych FORM5 ponad 54. W niektórych przypadkach ich daty poświadczenia nie są wystarczająco wczesne dla kolejnych targetów.

Przejrzano 74 dawne zmiany w zakresie sezonów; późniejsze retrospektywne aktualizacje repozytorium nie zastępują dawnych publikacji.

### Skąd odzyskano xG i co dokładnie oznacza 31

Dla oryginalnego SHA starego `fixtures.csv` użyto **tego samego SHA** pliku `data/<season>/gws/merged_gw.csv`, zawierającego statystyki FPL/Opta `expected_goals` zawodników. Dla każdego meczu poprzednika weryfikowano identyfikator `fixture`, stronę `was_home`, `opponent_team`, identyfikator zawodnika i źródłowy identyfikator drużyny. Sumowano xG zawodników z tego samego spotkania i drużyny, przy minimum 11 historycznych wpisach zawodników na każdą stronę, bez podwójnego liczenia graczy. xGA pochodzi od **przeciwnika w tym samym meczu**.

Do pełnego xG5 kwalifikuje się tylko target, dla którego **oba kluby** mają po **pięć ostatnich rzeczywistych wcześniej zakończonych meczów**, a wszystkie dziesięć źródłowych zapisów xG/xGA zostało potwierdzone z właściwej wersji źródła sprzed targetu. Nie użyto wyników docelowych spotkań.

**Wynik 31 to źródłowo poświadczony, alternatywny FPL/Opta `player-xG sum`, a nie oryginalna 121+38 natywna seria xG PitchAPI.** Nie ma automatycznej promocji tego xG ani 19 retrospektywnych cech Elo do pierwotnego modelu.

### Artefakty

- [Lista 74 SHA, indywidualne poświadczenia starych publikacji i niepotwierdzone rewizje](../data/audits/STEP14_ALL_74_FPL_REVISIONS_ANCHORED_GHARCHIVE_2026-10-29.json).
- [Rzeczywiste wyniki TRAIN: źródła, SHA xG, zgodność natywnych ID i liczebności](../data/audits/STEP14_FPL74_TRAIN_ASOF_xG_RESEARCH_SUMMARY_2026-10-29.json).
- [Macierz badawcza 1140×159 po odzyskaniu alternatywnego xG](../data/audits/STEP14_FPL74_TRAIN_1140x159_RESEARCH_2026-10-29.jsonl.gz).
- [Niezależny audyt oryginalnego GATE14/M1 po 74 rewizjach](../data/audits/STEP14_FPL74_ORIGINAL_M1_GATE_2026-10-29.json).
- [Skrypt sprawdzania 74 starych rewizji i grafu commitów](../scripts/step14_fpl74_independent_historic_ancestry.py), [rekonstrukcja TRAIN i xG](../scripts/step14_fpl74_asof_train_xg_recovery.py), [audyt M1](../scripts/step14_fpl74_final_original_M1_gate.py).

## Pozostałe wymagania kroku 14

Dalej trzeba rozpoznać bezpośrednie historyczne GH Archive PushEvent dla możliwie wielu **konkretnych** rewizji spośród 74 (to da wcześniejsze rzeczywiste zegary niż konserwatywny czas ich potwierdzonego potomka), dalej zwiększać TRAIN, porównać semantykę player-sum xG FPL z oryginalnym natywnym PitchAPI w meczach ze wspólnymi danymi i zdobyć autentyczne dowody `first_published_at` natywnych 121+38 pól. Oryginalnego M1 **nie** można wytrenować bez tych dowodów; nie modyfikowano oryginalnego splitu, TEST 2026/27, prognoz M0 ani metody Elo. Nie dodawano płatnego API ani szyfrowania.
