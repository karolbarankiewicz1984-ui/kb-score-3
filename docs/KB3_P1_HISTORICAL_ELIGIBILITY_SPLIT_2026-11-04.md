# KB Score 3.0 — P1-01: audyt historycznego PIT i odrębny podział badawczy (04.11.2026)

**Etap:** liczebność rzeczywiście kwalifikujących się archiwalnych meczów dla wspólnego kontraktu as-of v2 oraz bezpieczny wariant badań retrospektywnych. To *kolejny krok po* [kontrakcie TRAIN/forward v2](KB3_P1_SHARED_ASOF_V2_2026-11-04.md) z PR #151, a nie dopuszczenie istniejącego CatBoost do treningu.

## Materiał rzeczywisty i ograniczenie dowodowe

Źródło: `data/research/historical_multistat/observations.sqlite` (zapisane obserwacje, indeks skończonych meczów i obliczone okna) oraz oddzielny `issue_rechecks.sqlite` do późniejszych potwierdzonych nakładek źródłowych. Skrypt `scripts/kb3_p1_historical_eligibility_split.py` pracuje wyłącznie READ-ONLY i oblicza rzeczywiste liczby. Kod oryginalnego kolektora wymusza `observations.provider_first_published_at_utc IS NULL` oraz `finished_fixture_index.original_provider_first_published_utc IS NULL`; `rolling_feature_cache` jest jednoznacznie oznaczony `HISTORICAL_RECONSTRUCTED_NOT_ORIGINAL_PIT`, `training_approved=false`. Pobrane po dawnym meczu statystyki **nie są snapshotem przed jego rozpoczęciem**. Sam SHA obecnego API lub późniejszy source_observed_at nie jest dowodem archiwalnego prematch freeze.

Z powodu braku niezależnego dawnego prematch host/provider proof **formalnie dopuszczonych przypadków historycznych v2 do nowego CatBoost jest ZERO**, nawet gdy materiał daje znaczną pulę badań retrospektywnych. Nie oznacza to, że historyczne wyniki są fałszywe albo że dzisiejsze zamrożone prognozy M0 (74 FIT z ostatniego receipt) zostały odrzucone; są osobnymi populacjami.

## Metodyka dwóch niezależnych populacji

1. **CERTIFIED_ASOF_V2** — wyłącznie niezależnie poświadczone źródła oraz prematch snapshot sprzed target kickoff minus 90 minut, potwierdzona tożsamość meczu, wartości cech zarejestrowane przed cutoff, brak późniejszej korekty, kontrola z nowym builderem v2. Bieżąca historyczna SQLite nie zawiera wystarczających oryginalnych dowodów. Skrypt tworzy **pusty formalny TRAIN i VALIDATION** oraz jawny blokujący powód. Nie wolno fikcyjnie podnosić kwalifikacji przez +48h ani flagę source SHA.
2. **RECONSTRUCTED_RESEARCH** — istniejące realne ID zakończonych meczów i statystyki źródłowe, ale retrospektywne. Wyłącznie w ośmiu ligach, sezony 2023/24, 2024/25, 2025/26 (bez bieżącego 2026/27, bez UCL i bez chronionego ENG). Dla każdego historycznego celu przyjmujemy **HIPOTETYCZNY** cutoff = kickoff minus 2 godziny, zaś potencjalny poprzednik musi zakończyć „+3h od rozpoczęcia” przed cutoff. Z ostatnich **rzeczywiście chronologicznych** pięciu meczów obu drużyn sprawdzamy osobno obecność historii, core-stats i natywne xG. Nie zastępujemy brakującego xG=0 i nie wybieramy starszego meczu w zamian za brakujący w ostatniej piątce. Nie utożsamiać takiego retro testu z datą oryginalnej publikacji ani realnym wektorem wyliczonym builderem v2.
3. **Podział chronologiczny** tylko dla research history5, bez wymogu xG. Około 70% pierwszych spotkań idzie do oddzielnego selektora RESEARCH_TRAIN, pozostałe dopiero po siedmiodniowym embargo do RESEARCH_VALIDATION. Wszystkie mecze z dokładnie tym samym kickoff są po jednej stronie. Nie ma powtórek fixture IDs między zbiorami i nie odczytuje się etykiety docelowego spotkania do wyboru. Osobne sumy core5/xG5 i rozkład lig pozwalają ocenić przyszłe możliwości eksperymentu.
4. **Brak treningu:** przygotowane są selektory (identyfikatory oraz metadane, nie etykiety ani prawdopodobieństwa), nie jest to jeszcze 85-kolumnowy TRAIN i nie stanowi pretekstu do użycia dawnych wag M1-R. Oryginalna historyczna baza, M0 i FIT/HOLDOUT nie są modyfikowane.

## Odbiór automatyczny

Odizolowany, zależny od PR #151 projekt w **stacked draft PR**. Workflow `.github/workflows/kb3-p1-historical-eligibility-v2-offline.yml` sprawdza realny SQLite na Pythonie 3.11 i 3.12, testy chronologii/embargo, mapowanie source records i brak nieautoryzowanego PIT. W GitHub Artifacts zapisuje na 14 dni:
- `HISTORICAL_V2_ELIGIBILITY_READINESS.json` — liczba certyfikowanych próbek i zestawienie historycznych możliwości badawczych, per liga/sezon;
- `RECONSTRUCTED_RESEARCH_TRAIN_SELECTORS.json` i `RECONSTRUCTED_RESEARCH_VALIDATION_SELECTORS.json` — rzeczywiste rozłączne ID kandydatów research, oznaczone **train_approved=false**;
- `FORMAL_V2_TRAIN_VALIDATION_NO_ELIGIBLE_ROWS.json` — jawne puste listy formalnych próbek v2 (brak wymaganego dowodu).

**Warunek przejścia do nowego treningu:** odrębne dowody historycznego prematch as-of dla wersji v2 albo nowe prospektywne próbki z faktycznym i host-poświadczonym cutoff; następnie niezależny audyt pełnego wektora, nowy identyfikator modelu i chronologiczny TRAIN/VALIDATION bez przecieków. P1-01 i GATE16/GATE17 pozostają PENDING dopóki te dowody nie zostaną zweryfikowane. Nie zmieniać 100 FIT + 50 przyszłych HOLDOUT dla M0.

**Stan wpisu:** implementacja i próba CI — szczegóły oraz faktyczne liczniki muszą zostać uzupełnione po odbiorze prawdziwego workflow; nie zakładać wyników przed wykonaniem.
