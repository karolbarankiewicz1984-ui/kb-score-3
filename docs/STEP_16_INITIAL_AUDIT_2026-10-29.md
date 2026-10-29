# KB Score 3.0 — krok 16: rzeczywisty audyt wejścia do kalibracji

**29.10.2026 | stan: W REALIZACJI, GATE16 PENDING, 15/29.**

Przeprowadzono niezależny audyt dwóch już istniejących raportów realnego M0 dla trzech lig ESP, ITA, GER, bez nowych pobrań PitchAPI.

## Wynik

- Zamrożone prognozy w poprzednim preflight: 12, ale niezależna pierwsza publikacja serwerowa nie jest w pełni poświadczona. Nie jest to komplet 100 rozliczeń.
- **Naprawdę rozliczone i dopuszczone do kalibracji mecze: 0 z wymaganych 100**. Nadal potrzebnych 100; po dopasowaniu wymaganych będzie 50 nowych spotkań w niezależnym holdoucie.
- W repo istnieje już mechanizm SQLite M0 rozliczający prawdziwe wyniki. Nie zakładamy, że stworzenie mechanizmu = posiadanie wymaganej próbki.
- Nie wybrano żadnego T, nie przeliczono oceny po kalibracji i nic nie zostało automatycznie wdrożone.
- Nowe narzędzie liczy osobno reliability bins dla 1/X/2; nie uczy temperatury i odrzuca przypadki fałszowanych liczników, mieszanych źródeł i dostępu do chronionego TEST.

## Dowody

- [CI #40925527646 — SUCCESS, 24 testy i sprawdzenie 0/100](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40925527646).
- [Narzędzie audytu](../src/kb3_step16_calibration_readiness.py), [testy](../tests/test_step16_calibration_readiness.py).
- [Niezmienny rekord startowy](../data/audits/STEP16_INITIAL_READINESS_2026-10-29.json).
- Pełny wynik audytu do odczytu jako GitHub Actions artifact ID 12920900579.

## Następny krok

Pozyskiwać kolejne **rzeczywiste przedmeczowe freeze** wraz z SHA źródeł, wynikami 90 minut i datami. Nie kalibrować na historycznych 374 meczach z kroku 15. Po pierwszych 20–30 dopiero diagnostyka, a T dopasowywać wyłącznie po 100, ocenę w kolejnym, powstałym po fit holdoucie 50. TEST Premier League 2026/27 nieotwarty.

**GATE16 PENDING — brak podstaw do formalnego zamknięcia, brak nowych zakupów.**
