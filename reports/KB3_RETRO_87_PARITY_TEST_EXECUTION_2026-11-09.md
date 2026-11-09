# KB3 87-cechowy parity test — wykonanie i wynik (2026-11-09)

## Zakres wykonany

1. Sprawdzono oryginalne źródła `src/kb3_features.py` (`_compose_features`), `src/kb3_p1_shared_asof_features_v2.py` (`build_shared_features`) i lokalny faktycznie uruchamiany `train_retro_87.py`.
2. Sprawdzono istniejący syntetyczny test `test_true_same_asof_train_forward_same_features_hash_lineage`: porównuje dokładnie wektory, missing flags, lineage, clocks, SHA na tych samych wejściach. Zakończony sukcesem workflow GitHub Actions run `42573117892` z 09.11 06:27 UTC. **To parity oryginalnego TRAIN vs FORWARD**, a nie retro-87 vs builder.
3. Uruchomiono dodatkowy lokalny, deterministyczny test kontrprzykładu kolejności aktualizacji Elo: porządek po `kickoff+3h` w eksperymencie kontra `kickoff` w oryginalnym builderze. Dla stałego 3h lag zachowują identyczny porządek. Test PASS, ale nie porównuje całych wektorów.

## Wynik i ograniczenia

- `ORIGINAL_TRAIN_FORWARD_SYNTHETIC_PARITY=PASS`.
- `RETRO_ELO_MATURITY_ORDER_CHECK=PASS`.
- `RETRO_87_TO_ORIGINAL_87_VECTOR_PARITY=NOT_VERIFIED`.
- `OFFICIAL_V3_MODEL_TRAINED=FALSE`; `OFFICIAL_V3_SHADOW=NOT_STARTED`.

Nie ma uczciwego powodu, aby podawać 87/87 PASS: retrospektywny skrypt nie importuje oryginalnego buildera, a historyczna baza nie zawiera wiarygodnych indywidualnych receiptów pozwalających go uruchomić na identycznym źródle. Testy obecnego buildera sprawdzają jego wewnętrzną zgodność TRAIN/FORWARD, **nie** zgodność odrębnego modelu. Aby formalnie zamknąć parity, trzeba zbudować deterministyczny fixture adapter dla tego samego historycznego materiału, jawnie oznaczyć receipt jako symulowane tylko do testu semantyki i porównać numerycznie wszystkie 87 wartości, brakujące pola i identyfikatory. Następnie osobno wymagana rzeczywista archiwizacja native pre-cutoff dla Shadow.

Bez zmian produkcji, bez API.
