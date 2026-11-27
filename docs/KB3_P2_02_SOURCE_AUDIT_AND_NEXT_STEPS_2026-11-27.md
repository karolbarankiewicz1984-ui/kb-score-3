# KB3 P2-02 — walidator i audyt źródeł

Audyt #190 odtworzono z plików dostępnych na `main` w commicie [0add75df](https://github.com/karolbarankiewicz1984-ui/kb-score-3/commit/0add75dfbddee2773b1ecef99689645e62973ef2). [Raport JSON](../data/audits/KB3_P2_02_SOURCE_CONTRACT_AUDIT_2026-11-27.json) zawiera wyniki per liga i skróty kontrolne. Dane obejmują osiem lig BEL, ESP, FRA, GER, ITA, NED, POL i TUR.

## Wyniki audytu 27.11.2026

| Źródło | Wynik techniczny | Ograniczenie dowodu |
| --- | --- | --- |
| Archiwum PitchAPI `historical_multistat` | 166 pakietów zgodnych rozmiarem i SHA-256 z manifestami. Powiązane raporty zgodne z SHA szyfrogramów i końcami łańcuchów. | 21 030 obserwacji zadeklarowanych w manifestach. Potwierdzenie treści i łańcuchów wymaga odszyfrowania. |
| Archiwum PitchAPI `historical_issue_rechecks` | 44 pakiety z tą samą weryfikacją, dodatkowo zgodne liczniki obserwacji w manifestach i raportach. | 3 118 obserwacji zadeklarowanych. Potwierdzenie treści wymaga odszyfrowania. |
| Historyczne weryfikacje kartek `issue_rechecks.sqlite` | `integrity_check=ok`, SHA-256 przed i po odczycie identyczny. 1 434 wiersze z ośmiu lig. | 1 347 statusów `EVENT_YELLOW_CONFIRMED` według dotychczasowego klasyfikatora, 86 konfliktów zdarzenia–statystyki, jeden pusty lub brakujący feed. 0 wartości pierwszej publikacji. |

Nie było dostępnego prywatnego klucza odbiorcy. Ścieżka odtwarzania lokalnego korzysta z istniejącego mechanizmu weryfikacji szyfrogramu, odbiorcy, danych po odszyfrowaniu i łańcucha obserwacji. Przechowuje odszyfrowane dane w pamięci procesu i zapisuje zagregowaną diagnostykę. Liczniki z manifestów obejmują różne zasoby i mogą zawierać powtórzenia. Liczby z SQLite opisują wyniki starszego ekstraktora zdarzeń, który liczył wpisy `yellowcard` i sprawdzał zgodność z dostępną statystyką po stronie drużyny.

## Odbiór na poziomie targetu

| Target | Pole kandydackie lub źródło do sprawdzenia | Wynik i brakujący dowód |
| --- | --- | --- |
| `fouls_called` | `periods[].groups[].items[key=fouls]` z `matches.stats` | `UNKNOWN`. Definicja odgwizdanego faulu, jawny okres 90 min i zgodność stron. |
| `corners_taken` | `periods[].groups[].items[key=corners]` z `matches.stats` | `UNKNOWN`. Wykonany rożny, zakres 90 min i zgodność stron. |
| `total_shots` | `periods[].groups[].items[key=total_shots]` z `matches.stats` | `UNKNOWN`. Zakres 90 min oraz definicja strzału, w tym zasady bloków i obramowania bramki. |
| `shots_on_target` | `periods[].groups[].items[key=ShotsOnTarget]` z `matches.stats` | `UNKNOWN`. Zakres 90 min, definicja celności i właściwa jednostka po stronie drużyny. |
| `yellow_cards` | `yellow_cards` w statystykach i `events[].event_type=yellowcard` w starszym rechecku | `UNKNOWN`. Pełny timeline, okres, aktywny zawodnik i jednoznaczne ujęcie drugiej żółtej. |
| `straight_red_cards` | `red_cards` w statystykach i `events[].event_type` w timeline | `UNKNOWN`. Bezpośrednia czerwona rozróżniona od skutku drugiej żółtej. |
| `second_yellow_dismissals` | Kandydat do ustalenia w timeline | `UNKNOWN`. Tożsamość zawodnika i dowód kolejności oraz pojedynczego zapisu wykluczenia. |
| `card_units` | Wyliczenie z jednoznacznie sklasyfikowanych zdarzeń | `UNKNOWN`. Pełne kwalifikowalne zdarzenia, jawna reguła przerwy i jednostka 1/2/3. |

Każda wartość `home`, `away` i `total` w audycie pozostaje `null` z kodem przyczyny. Do odbioru potrzeba jeszcze wersji schematu źródła, powiązania z oryginalnym meczem i stronami oraz niezależnego dowodu hosta dla sprawdzonych bajtów. Natywne ID PitchAPI nie identyfikują automatycznie oferty operatora. Dopasowanie do reguł operatora, w tym strzałów, wymaga jego własnej wersjonowanej definicji. Historyczny `observed_at_utc` w repo opisuje obserwację archiwizującego. Pierwsza publikacja dostawcy pozostaje nieznana.

## Uruchomienie

```bash
python -m unittest discover -s tests -p 'test_kb3_p2_source_*.py' -v
python -m scripts.kb3_p2_source_audit --out /tmp/kb3-p2-02-source.json
```

Na komputerze właściciela można podać `--owner-key /lokalna/sciezka/do/klucza.pem` i nową ścieżkę `--out`. Odtworzenie wykorzystuje `cryptography`. Metadane PR CI obejmują audyt szyfrogramów i istniejącej SQLite bez prywatnego klucza. [Workflow](../.github/workflows/kb3-p2-source-contract.yml)

Walidator [`kb3_p2_source_contract.py`](../src/kb3_p2_source_contract.py) przyjmuje natywne statystyki i oczekiwaną tożsamość z osobno sprawdzonego katalogu. Wymaga reguły przejrzanej per target i rewizja, dokładnego oznaczenia okresu, formatu wartości oraz powiązania SHA-256 kanonicznego JSON SDK z niezależnym poświadczeniem hosta. Ścieżka kartkowa ma wejście z adaptera o udowodnionej kompletności, z informacją o okresie, zawodniku, drużynie, rodzaju zdarzenia i statusie uczestnictwa. Aktualne archiwa nie dostarczają zatwierdzonej reguły ani adaptera. Faule, kartki, rożne i strzały korzystają ze wspólnego kontraktu bez uruchamiania ścieżek produkcyjnych.

## Dalsze etapy P2-03 i P2-04

1. **Odbiór per target.** Zweryfikować lokalny odczyt oryginałów i niezależny dowód hosta. Powiązać wersję schematu z definicją okresu, wartości obu stron oraz mapowaniem meczu, ligi i dwóch drużyn. Dla kartek sprawdzić kompletność i typy zdarzeń na przykładach z drugą żółtą, bezpośrednią czerwoną, przerwą i wykluczonymi uczestnikami. Jeżeli dowodu brakuje, pozostawić `UNKNOWN` lub `QUARANTINE`.
2. **P2-03.** Po odbiorze danego targetu zdefiniować i wersjonować badawczą prognozę z kluczem mecz/okres/target/strona. Porównać Poissona i model ujemno-dwumianowy na identycznych meczach w chronologicznych podziałach. Ocenić nadmierną dyspersję i dobrać specyfikację w obrębie części treningowej. Zapisać wersję, SHA kodu i hash wejść/prognozy, a następnie zweryfikować niezależne `created_at` dla tych samych bajtów przed `kickoff - 90 min`. Retrospektywne dane bez dowodu publikacji mogą służyć analizie jakości źródła.
3. **P2-04.** Zamrozić osobny schemat rozliczeń z `market_id`, linią, stroną, `OVER/UNDER`, okresem i wersją zasad. Jawnie obsłużyć `PUSH/VOID`, odnotować brak i opóźnienie, przypinać wyniki 90 min do dokładnej tożsamości źródłowej. Ocenić Brier i log loss per rynek, liga i wersja na niezależnym, chronologicznym holdoucie. Porównywać identyczne mecze i tygodnie oraz grupować niepewność po meczach i tygodniach. ROI wymaga osobno poświadczonych rzeczywistych kursów.
