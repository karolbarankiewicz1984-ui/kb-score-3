# KB Score 3.0 — KROK 10 — wyniki pierwszego audytu jakości i chronologii

**Data:** 26.10.2026. **Stan bramki:** **W REALIZACJI / GATE10 PENDING**. **Zaliczonych kroków projektu:** 9/29. Ten dokument potwierdza udane testy na dotychczas zaimportowanym, **pojedynczym** sezonie, nie pełne pokrycie źródeł ani zgodę na trening ML.

## Metoda

- W repo napisano [automatyczny audyt bazy](../scripts/step10_quality_audit.py), [16 testów pozytywnych/negatywnych](../tests/test_step10_quality_audit.py) i [workflow](../.github/workflows/kb3-step10-quality-gate.yml).
- [GitHub Actions #40278994874 — SUCCESS](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40278994874) ponownie pobrał jeden kompletny sezon z API-Football i przetestował zapis oraz jego QA w SQLite (kopia lokalna nie była jedynym materiałem źródłowym).
- **35/35** testów: 16 nowych GATE10, 10 regresyjnych GATE09 i 9 regresyjnych GATE08. Dodatkowo cztery celowo uszkodzone warianty rzeczywistej bazy musiały zakończyć się \`FAIL\` i blokadą treningu.
- [Manifest jakości](../data/audits/STEP10_QUALITY_2026-10-26.json) · [manifest testów negatywnych](../data/audits/STEP10_NEGATIVE_TESTS_2026-10-26.json).

## Faktyczny wynik kontrolnego sezonu

| Kontrola | Wynik |
|---|---|
| Liga / sezon | Premier League / 2024–2025 |
| Rekordy meczów | 380/380 |
| Wydarzenia zakończone FT | 380 |
| Kluby | 20 |
| Kanoniczne mapowania API-Football | 380 |
| Daty UTC | 16.08.2024–25.05.2025 |
| Mecze dom / wyjazd | 19/19 na zespół, bez naruszeń |
| Spójność wyników 90 min i dat | PASS, 0 błędów krytycznych |
| SQLite integrity_check | ok |
| SQLite foreign_key_check | 0 naruszeń |
| Obserwacje statystyk / zdarzenia | 0 / 0 — NIEZAIMPORTOWANE |
| Snapshoty kursów | 0 — NIEZAIMPORTOWANE |
| Potwierdzone źródła prematch | 0 — BRAK |
| Dane retrospektywne | 1 snapshot źródła |

**Wynik historycznej integralności:** \`PASS_WITH_COVERAGE_WARNINGS\`. Poprawność struktury nie jest równoznaczna z pokryciem potrzebnych rynków i cech.

### Negatywne próby — 4/4 prawidłowo zatrzymane

1. Data meczu poza sezonem → \`KICKOFF_OUTSIDE_SEASON\`.
2. Brak bramki w zakończonym spotkaniu → \`MISSING_OR_INVALID_REGULATION_GOALS_goals_home_90\`.
3. Źródło pozornie \`VERIFIED_PREMATCH\`, bez autentycznego czasu publikacji → \`PREMATCH_SOURCE_WITHOUT_PUBLICATION_PROOF\`.
4. Usunięte mapowanie dostawcy → \`PROVIDER_MAPPING_INCONSISTENT\`.

Dodatkowe testy jednostkowe weryfikują blokadę informacji opublikowanych lub zaobserwowanych po czasie odcięcia oraz używania wyniku konkretnego meczu jako jego własnej cechy.

## Ryzyka i decyzja o szkoleniu modelu

**TRENING ZABLOKOWANY (`training_allowed=false`).** Dane pobrane teraz o meczach z 2024–2025 stanowią prawidłowe historyczne wyniki/etykiety. Sam fakt dzisiejszego pobrania statystyk nie potwierdza jednak, że były dostępne przed startem tych meczów. Do budowania cech z *wcześniejszych* meczów potrzeba jawnej polityki chronologicznej i źródeł danych dostępnych do danego cutoffu. Nie wolno używać wyniku badanego meczu jako jego cechy.

**Brak xG, statystyk, kursów i zdarzeń w tej konkretnej tabeli nie oznacza wartości 0.** Braki muszą pozostać jawne, zostać pozyskane z udokumentowanym czasem lub prowadzić do modelu bez tych cech.

## Dlaczego GATE10 jest nadal otwarty

Pierwszy sezon i mechanizm walidacji przeszły test, ale docelowy zakres audytu każdej importowanej ligi/sezonu, szczegółowa analiza kompletności źródeł i rzeczywiste reguły cech point-in-time nie są jeszcze zamknięte. Zanim uznamy całą bramkę za zaliczoną, trzeba ustalić zakres dopuszczonych lig oraz zaakceptować/wyspecyfikować progi jakości brakujących pól. Nie awansowano do GATE11; nikt nie uruchomił treningu ani codziennych raportów KB3.

**Nowe zakupy: 0 zł.** Starsze KB2.1, API Market i MultiModel nie były modyfikowane.
