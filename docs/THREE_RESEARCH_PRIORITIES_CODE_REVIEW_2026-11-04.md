# KB Score 3.0 — realizacja badawcza trzech priorytetów (04.11.2026)

**Status:** CODE STAGED ON DRAFT PR / CI PENDING / NO MODEL OR DATA MUTATION.
To rozwinięcie [planów](RESEARCH_PRIORITIES_1_3_2026-11-04.md), a nie zakończenie P1-01, P1-02, GATE16 lub GATE17.

## Tor 1 — realna kontrola kodu i nowy kontrakt badawczy

- src/kb3_research_train_forward_contract.py: wersjonowany schemat porównania tych samych target fixtures i predecessor IDs przy historycznym 48h od kickoff poprzednika względem target kickoff oraz prospektywnym 3h od kickoff poprzednika względem faktycznego capture cutoff. Osobny rachunek dni od ostatniego meczu z obu zegarów. Historyczne RECONSTRUCTED nie jest dowodem ORIGINAL_PREMATCH_ATTESTED, nawet gdy istnieje deklarowana data; narzędzie jawnie nie certyfikuje zegarów ani nie pozwala na trening.
- scripts/kb3_research_parity_audit.py: przy każdym uruchomieniu czyta **rzeczywisty kod** src/kb3_features.py i scripts/step14_m1r_recompute_1140_relaxed_48h.py, wylicza SHA i sprawdza konkretne znaczniki semantyki. SOURCE_POLICY_DRIFT to FAIL, nie pozorny PASS. Opcjonalny plik JSON rzeczywiście wspólnych fixture daje delty predecessor IDs, ale bez takiego pliku status NO_REAL_ID_INPUT_SUPPLIED. Nie wolno traktować samych syntetycznych unit testów jako naprawy P1-01.
- **Następna bramka:** osobno zbudować rzeczywisty input z chronologicznych i niezależnie poświadczonych źródeł, potwierdzić ten sam fixture/cutoff, następnie wdrożyć nowe wersjonowane obliczenie cech i testy parytetu. Nie nadpisywać dotychczasowego M1-R.

## Tor 2 — realne kontrole kompletności xG / formy

- scripts/kb3_research_xg_coverage_readonly.py: bez połączenia API czyta **rzeczywiste** bieżące ROLLING_AFTER_RECHECK.json i ACCELERATED_CAPTURE_REPORT.json run 41882339782. Niezależnie uzgadnia sumy po ligach, statusy native xG, brakujące okna 5/10/15, kompletność core5 i znane przyczyny konfliktów; brak starego PIT wymusza status training_allowed=false.
- Punktem odniesienia jest 1525 obserwowanych meczów, 1363 native xG, 162 konflikty, 654 core5, 271 xG5, 39 xG10, 6 xG15. Skrypt nie naprawia 162 konfliktów bez oryginalnych statystyk ani nie uruchamia selektora z draft PR #145. Wynik per liga wskaże, gdzie brakujące poprzedniki ograniczają całe okna.

## Tor 3 — diagnostyka prospektywnego porównania silników

- scripts/kb3_research_three_engine_readiness.py: odczytuje **najnowszy istniejący** rzeczywisty M0 settlement receipt. Waliduje M0_ELO_POISSON_RESEARCH_720TRAIN_V1, brak dostępu do ENG TEST, liczby FIT/frozen oraz status dowodów. Zlicza rzeczywiste sparowane mecze w trzech porównaniach M0/Elo-only/CatBoost no-xG; nie miesza ich z 942 retrospektywnymi modelami #144.
- Formalne minimum istniejącego scorer: >=100 faktycznych par na model i >=8 tygodni dla bootstrap, po formalnym GATE16. Niezależna decyzja właściciela zawsze wymagana. Raport nie dopasowuje nowego modelu, nie wybiera Championa.

## Bezpieczeństwo i odbiór

- PR w wersji DRAFT, tylko trzy nowe narzędzia badawcze, kontrakt i testy; osobny workflow PR-only, dwa Pythony 3.11/3.12, bez sekretów i poboru API; odczyt tylko istniejących źródeł. Dane SQLite, PDF, stare archiwa, parametry M0, CBM, protected ENG TEST nietknięte.
- Dopiero zakończone CI SUCCESS i odczyt artefaktów pozwalają oznaczyć offline audit PASS; same stworzone pliki oznaczają tylko IMPLEMENTED_STAGING. Rozbieżność TRAIN/forward i brak 100+50 nadal są blokadami. Trzy obszary pozostają PARTIAL do niezależnego odbioru.
