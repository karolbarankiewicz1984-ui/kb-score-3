# KB Score 3.0 — realizacja kolejnych zadań 1–3 (01.11.2026)

**Stan dowodów: 2026-11-01 07:05 UTC / 08:05 Europe/Warsaw.** Operacje wykonane na zdalnym prywatnym repozytorium GitHub. Brak ręcznego poboru płatnego PitchAPI, brakuje bieżącego GitHub-hosted CI aktualnych głów poprawek; formalne `GATE16` i `GATE17` **PENDING**, zaakceptowano nadal 15/29 etapów.

## 1. Nowe prognozy M0 po odnowieniu Actions — diagnostyka rzeczywistych danych, nie zmyślanie nowego forecast

- Zweryfikowano metodą GitHub REST aktualne `main`, drzewo z `data/forecasts/m0_720_eight`, listę ostatnich 40 Actions oraz workflow `.github/workflows/kb3-step16-m0-720-eight-forward.yml`.
- Istniejące rzeczywiste post-reset `SUCCESS`: [ośmioligowy M0 rozliczenie run 41260370277](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/41260370277) i [oddzielny M0 3-ligowy rozliczenie run 41261327143](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/41261327143). NIE są nowym `forecast`.
- Do odczytu stanu: [ostatni ośmioligowy receipt](../data/pit_sidecar/m0_720_eight/2026-11-01/settle-011723723032/RECEIPT.json). Niezmienione 73 forecasty z 2026-10-29; 38 settlementów, 35 pending, 62 do minimalnego FIT100; stare `M0_ELO_POISSON_RESEARCH_720TRAIN_V1` i SHA parametrów `55310f0e1dd3842e6d876069ef21b1380901b3a6cc6884cf6ec6ea351a5812d1`. W drzewie `main` nie ma katalogu `data/forecasts/m0_720_eight/2026-11-01`.
- Istniejący automatyczny harmonogram: 06:21 UTC `forecast`, 08:17/22:17 UTC `settle`. Według listy GitHub Actions sprawdzonej o 07:05 UTC 01.11 **brak nowego uruchomienia forecast o 06:21**; możliwe opóźnienie harmonogramu, pominięcie lub ograniczenie Actions — nie przypisano bez dowodów jednej przyczyny. 06:41 UTC native xG też jeszcze bez nowego potwierdzenia. Nie wolno raportować nowego sample przed host-attested dowodem. Dostępny konektor GitHub ma akcje odczytu oraz rerun istniejącego joba, ale **nie** ma endpointu `workflow_dispatch`; nie próbowano ponawiać historycznego settle jako forecast, bo byłby to błędny tryb i koszt API.
- Działający kod `scripts/step16_m0_720_eight_run.py` ma jawne `--mode forecast/settle`, odrzuca ponowne zamrożenie istniejącego dnia. W głównej funkcji `src/kb3_step16_m0_720_eight_forward.py` nowe challengery są generowane tylko przy `mode=forecast` w tym samym cutoff, feature hash, fixture i jednocześnie na staging SQLite. Nie powielono starych 73. **Status P1: AUDYT_WYKONANY, NOWY_FORECAST_NIEPOTWIERDZONY**.

## 2. PR #122 / #123 — weryfikacja CI i uszczelnienie

- [PR #122](https://github.com/karolbarankiewicz1984-ui/kb-score-3/pull/122) HEAD `00b80cbf0e07655d247166fcb72da63eabef68ba`: poprawka testów Poissona i nienaruszalności `data/models` zapisana wcześniej. [Actions #41104025484 attempt 2](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/41104025484) `SUCCESS` historycznego SHA po odzyskaniu limitów; to **nie jest** wynik aktualnego HEAD. `fetch_commit_workflow_runs` dla aktualnego HEAD zwrócił 0 pull-request CI; combined status 0.
- [PR #123](https://github.com/karolbarankiewicz1984-ui/kb-score-3/pull/123): wcześniej `62a5664f092b165b5f398d945018168da4c2c622` usunął duplikację kluczy YAML `cache: 'pip'` i przywrócił odrębny live cache. Niezależny odczyt statyczny repo po commicie potwierdził dwa osobne cache (CI i live) i nienaruszone dwa harmonogramy. Brak dowodu oszczędności minut przed rzeczywistą próbą.
- Na HEAD PR #123 dodano nowe read-only testy oraz izolowany Step17 pair audit (szczegóły niżej) — końcowy commit `0869e9dc5b82dd65994f70a3b886c57064167e33`. Wzmocniono offline workflow, ale **nie uruchomiono aktualnego HEAD GitHub-hosted**, ponieważ konektor nie oferuje dispatch i po zmianach przez konektor nie pojawił się nowy `pull_request` run. Zero merge.
- **Status P2: PREPARED/STATIC_REVIEW_PASS, HEAD_CI_PENDING**. Nie mylić wcześniej wykonanego CI starych SHA z niezależnym testem HEAD obu PR.

## 3. M0 / Elo-only / CatBoost bez xG — rzeczywista wspólna prognoza i uczciwa ocena

- Istniejący M0 posiada równoległy moduł `src/kb3_step17_forward_challengers.py`: `ELO_ONLY` i zamrożony `M1_R_BASE_CATBOOST_720_TRAIN_2026-10-29.cbm` (no-xG), w dokładnie tej samej chwili i dla tych samych NOWYCH prognoz co M0. Brak nowych dodatkowych żądań do PitchAPI. Przedmeczowe prognozy, SHA i wyniki w odseparowanych append-only tabelach, zakaz backfill starych 73.
- Istniejący `src/kb3_step17_challenger_provenance.py` już odczytuje wiarygodne oryginalne artefakty GitHub, wiąże M0 + challenger, a następnie korzysta z `src/kb3_step17_engine_comparison.py` dla Brier sum3, log loss, trafności i tygodniowych porównań paired bootstrap. Ostatni rzeczywisty stan 01.11: **0 nowych par challengerów** i **0 wspólnych, host-attested rozliczeń**, zatem żadnej oceny przewagi nie wolno publikować.
- W [PR #123](https://github.com/karolbarankiewicz1984-ui/kb-score-3/pull/123) przygotowano dodatkowo `scripts/step17_offline_three_engine_audit.py`, `tests/test_step17_offline_three_engine_audit.py` i włączenie w `.github/workflows/kb3-step16-offline-readonly-audit.yml` (commity `0f3383d...`, `333e6f4...`, `0869e9d...`, `9c31432...`, **HEAD `3be004fb542fa8b085668dfbad09bd7455bbf96a`**). Narzędzie:
  1. odczytuje wyłącznie kopię istniejącego SQLite; sprawdza `integrity_check`, model, liczbę źródłowych forecastów, rozliczeń oraz dowodów hosta;
  2. robi hash SHA256 przed/po i wymaga dokładnej nienaruszalności oryginału;
  3. uruchamia istniejący `paired_settled_report` tylko na tymczasowej kopii;
  4. liczy **rzeczywiste trójstronne przecięcie identycznych M0 fixture ID i obu challengerów z własnymi dowodami** (nie minimum samych liczników par), co chroni przed fałszywą próbą;
  5. rozdziela `diagnostic_metrics_available` od formalnego `performance_claim_allowed=false`; nawet przy pierwszej rozliczonej trójce NIE awansuje modelu i utrzymuje `winner_auto_selected=false`, `gate17=PENDING`.
- Dodane testy obejmują nieistniejącą bazę (fail closed), nienaruszalność oryginalnego ledger, zero niepoświadczonych danych oraz sztuczną bazę SQLite z rozdzielonymi dowodami modeli pokazującą, że trójkę można policzyć dopiero po obecności *obu* dowodów. **Testy na HEAD są przygotowane w GitHub, ale nie można przypisać im sukcesu bez realnego CI.** Niezależnie lokalnie uruchomiono syntetyczny test SQL na `:memory:` potwierdzający kolejno 0,0,1,2 wspólne trójki przy dopisywaniu rzeczywistych dwóch dowodów hosta dla tych samych rodziców; nie jest to test pełnego repo ani jego zależności. Zweryfikowano również nazwy trzech kluczy par porównawczych względem rzeczywistego `ENGINES` z comparatora, po poprawce kolejności w `9c31432...`.
- Realne nowe prognozy trzech modeli pozostają zależne od poświadczonego, przedmeczowego `forecast` działającego w `main`. Nie dodano wstecznych prognoz, nie uruchomiono nowego fitu, nie ruszono chronionego TEST ani kalibracji.

## Wymagane bramki przed zamknięciem

1. GitHub-hosted `forecast` po odnowieniu limitów, przed cutoff 90 min, serwerowy artefakt z nowymi M0 i `2×new_forecasts` challengerami, checksum i zgodność identycznych fixture.
2. Rzeczywisty Python 3.11 GitHub Actions test HEAD PR #122 i #123; dopiero wtedy decyzja o merge, nadal oddzielnie od PR #124 Codex.
3. Co najmniej jedna nowa rozliczona i poświadczona wspólna trójka dla diagnostycznego Brier/logloss; wymagane niezależne tygodnie i osobne decyzje GATE16/17 do formalnej akceptacji.

**Zabezpieczenia:** GATE16=PENDING, GATE17=PENDING, 15/29; brak zmian w oryginalnych 73 M0, SHA parametrów, 100+50, produkcji, sekretach, płatnych dostawcach i TEST 2026/27. Zmiany kodowe wyłącznie na izolowanej gałęzi PR #123, żadnego automatycznego scalenia. Raport przeznaczony do trwałego rejestru operacyjnego.
