# KB Score 3.0 — operacyjne odblokowanie i kontrola 15.11.2026

**Tryb:** wykonanie operacyjne, bez awansu modelu i bez zmiany M0, archiwalnych etykiet, kalibracji, chronionego ENG TEST ani zasad historycznego PIT. Godziny UTC, chyba że podano inaczej.

## Potwierdzone działania

1. Repozytorium `karolbarankiewicz1984-ui/kb-score-3` zmienione przez właściciela na **publiczne**. Blokada przydziału runnerów GitHub Actions ustąpiła. Upublicznienie wymaga osobnego pełnego audytu sekretów, także całej historii commitów, oraz przeglądu uprawnień `pull_request`; powierzchowny przegląd wyszukiwarki kodu nie wystarcza do poświadczenia bezpieczeństwa.
2. Oryginalny [historical backfill #43698981479, attempt 2](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/43698981479) **SUCCESS** (15.11, 12:13 UTC). Pięć partii: 240 nowych meczów ze statystykami oraz 211 nowych xG zweryfikowanych w raporcie; łącznie 6800 obserwacji statystyk, 6021 zweryfikowanych xG. Trwały commit `a3ef78a5cd70ed966c9ff46ba06e1a3f52036a77`, zapis SHA i zaszyfrowanych danych. Źródło: `data/pit_sidecar/historical_multistat/2026-11-15/run-43698981479-2-summary/ACCELERATED_CAPTURE_REPORT.json`. **Nie** certyfikuje historycznego czasu pierwszej dostępności PitchAPI ani formalnego TRAIN/VALIDATION.
3. Po bezpiecznym ponowieniu [Shadow/Step18 #43670819558](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/43670819558) **SUCCESS** (15.11, 12:28 UTC). Zamrożony porównawczy audyt nadal zgłasza `PENDING_16_17_AND_OWNER_APPROVAL` oraz niewystarczającą liczbę niezależnych tygodni. Brak automatycznego awansu Championa.
4. Po ponowieniu [TEST market freeze/settlement #43670750279](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/43670750279) **SUCCESS** (15.11, 12:29 UTC). `new settlements=0, existing=72, pending=2`; nie przekształca się zaległych dwóch meczów w fikcyjnie rozliczone.
5. Po ponowieniu [osiem lig M0 #43665372568, attempt 2](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/43665372568) testy modelu, oryginalne rozliczenie i kontrole danych działały; `new_settlements=0, total_settlements=147`. **Zadanie końcowe FAIL** wyłącznie w `git push` (`non-fast-forward`): inny proces zmienił main podczas wykonywania. Oryginalny artifact `14160654908` został zachowany. Nie wykonywano retro forecastu ani wymuszonego nadpisania SQLite.
6. [PR #176](https://github.com/karolbarankiewicz1984-ui/kb-score-3/pull/176) **MERGED** commit `ef32a8539e7707c716bd246adade985d8402f9b0`. Poprawka dopuszcza wyłącznie bezkolizyjne ponowienie publikacji **nowych append-only receiptów** po awarii `push`; blokuje rebase SQLite, forecastów, istniejących plików, skasowanych lub modyfikowanych danych. Naprawiono też pełny offline regression: przed testami przywraca `observations.sqlite.gz` dopiero po weryfikacji oryginalnego SHA256, bez dostępu do API. Wszystkie pięć końcowych CI PR na SHA `51536905635c3ab965ed36fd03d7fa5bdca6511d` **SUCCESS**, w tym [pełny audyt #43714907672](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/43714907672).

## Ustalony stan bazowy

- Niezmieniona, oryginalna `data/forward_m0_720_eight/kb3_forward_eight.sqlite` z autentycznego artifact `14160654908`: `integrity_check=ok`, `foreign_key_check=[]`, **149 forecastów**, **147 rozliczeń**, **149 GitHub host-proofs** i **23 Shadow Six**. Ostatnie nowe M0 zamrożono 05.11.2026 08:20 UTC (kickoff do 08.11).
- Oryginalny, niezatwierdzony `m0720_calibrators`: jeden kandydat, `fitted_at_utc=2026-11-08T01:28:23.555622Z`, **100 FIT**, `temperature=0.7`, `production_approved=0`. `m0720_holdout_reviews=0`; **0/50 autentycznych nowych po fit HOLDOUT**. Nie dopasowywać tego samego kandydata drugi raz, nie przenosić dawnych spotkań do nowego holdoutu.
- Formalny, oryginalny [PIT Gate14](https://github.com/karolbarankiewicz1984-ui/kb-score-3/blob/main/data/audits/STEP14_INDEPENDENT_RECHECK_2026-11-14.json): 0/760 pełnych historycznych TRAIN i 0/380 VALIDATION w ścisłym kontrakcie 121+38; certyfikacja dat publikacji xG z dawnych sezonów nieudowodniona. `GATE14=PENDING`, `GATE16=PENDING`, `GATE17=PENDING`. Nie mieszać eksploracyjnego historycznego CatBoost z produkcyjnym M1.

## Dalsza kolejność i warunki odbioru

1. Weryfikować po merge harmonogram `kb3-step16-m0-720-eight-forward.yml` (forecast 06:21/09:21/12:21 UTC, settle 08:17/14:17/22:17 UTC). `forecast_due` i minimalny lead 90 minut mogą legalnie pominąć cykl, kiedy brak kwalifikowanych meczów; **sam sukces workflow na mode=skip nie oznacza nowej prognozy**.
2. Przy pierwszym nowym `new_forecasts>0` udokumentować datę utworzenia, kickoff i serwerowy proof; dopiero spotkania po kalibracji mogą zasilać 50 nowych HOLDOUT. Utrzymać idempotencję i świadomą kontrolę kosztów PitchAPI.
3. Dwa pending settlements wymagają niezależnej oceny zmian kickoff; nie backfillować retro.
4. Osobno sprawdzić nowszy 87-feature V3 forward builder: ostatni wcześniejszy techniczny raport (12.11) miał `target_count=0`, a nie błąd HTTP. Nie dopuszczać ścisłego PIT ani produkcyjnego M1 bez rzeczywistego 87-wymiarowego forward wektora przed odpowiednim cutoff.
5. Audyt bezpieczeństwa publicznego repo: obecna gałąź + historia commitów + artefakty, rotacja każdej potencjalnie ujawnionej wartości, przegląd GitHub Secrets i uprawnień automatyzacji. Nie twierdzić, że sekretów nie ma, bez pełnego dowodu.
6. Generatory PDF, rozbudowa rynków oraz finalny Champion dopiero po zweryfikowanym przepływie nowych danych i właściwych gate'ach.

**Stan decyzji:** operacyjne Actions i kod M0 są uruchamialne, pierwsze badawcze audyty działają; regularny przyrost nowych przedmeczowych prognoz, formalny HOLDOUT i oryginalne PIT nie zostały jeszcze zaakceptowane. Zmiany nie ustanawiają nowej wersji modelu produkcyjnego.


## Dopisany punkt kontrolny V3 — 15.11.2026 12:46 UTC

- Po pierwotnym zapisie niniejszego raportu zakończył się [V3 native two-phase Actions #43714964813](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/43714964813) **SUCCESS** na oryginalnym workflow z kodem badawczym. Nie ma tu powtórnego treningu ani modelu produkcyjnego.
- `source-archive` wykonał 7 zapytań istniejącego PitchAPI i zamroził 6 pierwotnych porcji źródłowych. Oryginalny GitHub artifact **14162580126**: created_at **2026-11-15T12:40:00Z**, serwerowy SHA-256 ZIP `63e43d87947db60be176e8e4d34e3ed5ca4423b7c251904ece99a7a09e0ecfb5`.
- `verified-v3-freeze` potwierdził źródło i pierwotne wartości buildera przed niezależnie wybranym cutoff **2026-11-15T12:45:59.058701Z**. Oryginalny artifact **14162955048** (`KB3_V3_PREMATCH_87_NATIVE_INPUTS.json`) zawiera **9 `VERIFIED_87_INPUTS`** (każdy dokładnie 87 wartości): ESP=3, ITA=3, GER=3. Dotyczą przyszłych kickoffów **20–21.11.2026**; jest to pierwsze potwierdzenie niezerowej grupy takich wektorów w tym audycie.
- Pola audytu: `independently_archived_before_exact_cutoff=true`, `native_sources_verified=6`, `verified_v3_input_vectors=9`, ale `provider_original_first_publication_certified=false`, `formal_v3_training_admitted=0`, `new_catboost_models_trained=0`, `production_approved=false`. Nie używać tych dziewięciu do retro-dopasowania ani do fałszywego zamknięcia oryginalnego `GATE14`.
- Oba artifacts mają **retention-days=90** w workflow. Konieczny osobny plan legalnej, trwałej archiwizacji i deduplikacji źródeł przed wygaśnięciem; samo posiadanie ogólnego logu nie odtwarza historycznych bajtów dostawcy. Nie ujawniać surowych materiałów licencyjnych w publicznym repo bez zgody.


## Kontrola widoczności artefaktów V3 po upublicznieniu

Bezpośredni odczyt istniejącego GitHub artifact **14162580126** potwierdził w ZIP **16 plików JSON bez szyfrowania**: 1 indeks, 9 `inputs/*.json` i 6 `sources/{ESP,ITA,GER}_{2025,2026}.json`, zawierających struktury źródłowych meczów i poprzedników PitchAPI. W podstawowym skanowaniu nazw pól nie znaleziono `api_key`, `authorization`, `secret`, `token`, `bearer`, `password` ani `private_key`, ale **nie jest to certyfikat braku ujawnionych sekretów w treści lub historii repozytorium**. Publiczny artifact powinien zostać sprawdzony pod kątem uprawnień do dalszej dystrybucji danych źródłowych i zastąpiony bezpiecznym, prywatnym lub szyfrowanym archiwum, zachowując niezależny hosting czasu przed cutoff. Nie zmieniać statusu PIT, nie ujawniać kluczy, nie usuwać historycznych dowodów bez planu zachowania SHA. Operacyjna decyzja o nowym mechanizmie składowania wymaga osobnego audytu uprawnień i licencji.
