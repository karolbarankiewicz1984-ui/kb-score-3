# KB Score 3.0 — Krok 12: podział TRAIN / VALIDATION / TEST

**Rozpoczęto:** 26.10.2026 • **Stan:** W REALIZACJI / GATE12 PENDING • **Koszt nowych usług:** 0 zł.

**Zakres:** techniczna konstrukcja odtwarzalnego, chronologicznego i niemutowalnego podziału. **Nie uruchamiamy treningu, nie generujemy typów bukmacherskich, nie twierdzimy, że historyczne dane są prawdziwym PIT.** Krok 11 odebrany według pierwotnej bramki; jego `training_allowed=false` pozostaje w mocy.

## Zamrożona propozycja okien v0.1 (UTC, lewy kraniec włączony, prawy wyłączony)

| Rola | Zakres wydarzeń | Dozwolone użycie po dodatkowej certyfikacji |
|---|---|---|
| TRAIN | 01.07.2023–30.06.2025 | Estymacja ELO/Poissona i innych parametrów |
| VALIDATION | 01.07.2025–30.06.2026 | Strojenie i kalibracja, bez korzystania z TEST |
| TEST | 01.07.2026–30.06.2027 | Zamknięty holdout; bez strojenia na jego wynikach |

Podział działa po rzeczywistym `kickoff_utc`, a **nie** tylko po nazwie sezonu. Tożsamość `fixture_id` nie może wystąpić więcej niż raz. Ciągłość tożsamości drużyn między latami nie jest przeciekiem: tożsamość jest znana przed meczem, natomiast ich **późniejsze oceny, wyniki oraz cechy już są przeciekiem**.

## Walk-forward v0.1

Kolejne walidacyjne okna: 07–09.2025, 10–12.2025, 01–03.2026 i 04–06.2026. W każdym oknie treningowe obserwacje muszą spełnić obie granice: `kickoff < fold_start` **oraz** `label_observed_at < fold_start`. Wcześniejsze obserwacje VALIDATION mogą wejść do następnego, poszerzonego TRAIN dopiero po udostępnieniu ich prawdziwych wyników. **Nigdy** nie wolno włączyć TEST do strojenia.

## Kwarantanna informacji retrospektywnych

Odczyty meczów PL 2023/24–2025/26 pobrane 26.10.2026 są prawdziwą historią sportową, ale nie stanowią dowodu historycznej dostępności wszystkich cech przed kickoff. Zapisujemy je jako `RETROSPECTIVE` i **nie** przydzielamy ich do dopuszczonego treningu ani uczciwego historycznego backtestu. Obserwacje `PROSPECTIVE_OBSERVED_AT` muszą mieć źródłowe znaczniki każdej cechy <= `feature_cutoff_utc < kickoff_utc`, a także zgodę z audytu Step11. Brak xG nie staje się zerem; osobny mechanizm cech z kroku 11 nadal odpowiada za flagi braków.

Kontrola 90 minut: wynik H/D/A musi być obserwowany nie wcześniej niż kickoff i najpóźniej do czasu eksportu. Wynik TRAIN obserwowany po początku VALIDATION nie nadaje się do treningu tej walidacji, analogicznie VALIDATION po początku TEST nie nadaje się do decyzji poprzedzającej TEST. Wyniki trzymamy poza jawnie publikowanymi w manifestach listami, by nie przypadkowo wykorzystać holdoutu.

## Kod, dowód i odbiór

- `src/kb3_split.py`: walidacja UTC, wersja danych, kody powodów kwarantanny, chronologiczny przydział, walk-forward, SHA-256 i zapis manifestu **bez możliwości nadpisania różną zawartością**.
- `tests/test_step12_split.py`: negatywne i pozytywne testy syntetyczne. Test nie jest dowodem na istnienie prawdziwych poprawnych historycznych PIT.
- `.github/workflows/kb3-step12-split.yml`: testy offline, bez sekretów, wywołań API, automatycznego treningu i płatnych zadań.
- Wywołanie na gotowym rzeczywistym *zunifikowanym indeksie metadanych*, nie na surowym pliku z tokenami: `python -m src.kb3_split --input input_metadata.json --output private/STEP12_SPLIT_v1.json`. Wymagane pola wejścia: `dataset_version`, `exported_at_utc`, `records[]`; rekord: `fixture_id`, `kickoff_utc`, `label_90m` (lub null), `label_observed_at_utc` (lub null), `evidence_class`. Dla dopuszczalnego PIT także `feature_cutoff_utc` i `feature_availability` z czasem i zgodą dla każdej cechy.

**Do odbioru GATE12:** (1) wskazać rzeczywisty, zamrożony, pełny indeks fixture ID wraz z fingerprintami źródeł; (2) zapisać manifest z liczebnościami i SHA oraz sprawdzić jego niezależne odtworzenie; (3) pokazać zielone testy CI oraz oddzielne potwierdzenie braku przecieku; (4) uzyskać akceptację metodologii przed treningiem. Jeśli brak rzeczywistego PIT, wynik to uczciwe `GATE12 PENDING`, a nie fikcyjne zaliczenie.

**Własne starsze modele KB2.1, API Market i MultiModel:** nietknięte. **Nowe koszty:** 0 zł.
