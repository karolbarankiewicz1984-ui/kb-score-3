# KB Score 3.0 — start wykonania priorytetów 1–3 (23.11.2026)

**Polecenie właściciela:** „Zacznij od kroków 1-3. Wpisz wszystko w rejestr”. Zakres: (1) kontrola automatyzacji, błędów e-mail i nierozliczonych prognoz, (2) krok 16 — weryfikacja kalibracji, (3) krok 17 — parowane porównanie M0 / Elo-only / CatBoost. **Stan: rzeczywisty audyt i uruchomione dalsze kontrole; brak samowolnej zmiany modelu, danych FIT/HOLDOUT i źródeł.**

## 1. Diagnostyka i stan automatyzacji — START / CZĘŚCIOWY PASS

### Sprawdzone awarie i przyczyny
- Gmail, 21–23 XI: powiadomienia o porażkach workflow M0, V3-R, historycznego backfillu i osobnego market-freeze; samo stare powiadomienie nie świadczy, że kod na `main` nadal ma ten sam problem.
- [M0 #44923015118](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/44923015118), 21 XI: `anti-leakage-and-data-safety=success`, `real-eighth-league-fitted-M0-shadow=failure`; log `M0_720_CAPTURE_FAILED Research720Error {}` podczas `settle`. Starszy przebieg nie wystarcza do uznania aktualnego M0 za niesprawny, bo późniejszy [autentyczny receipt 23 XI](../data/pit_sidecar/m0_720_eight/2026-11-23/settle-024730964942/RECEIPT.json) potwierdza 20 nowych rozliczeń.
- [V3-R #45037075596](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/45037075596), 22 XI: `CANDIDATE_LEAGUE_UNAVAILABLE_TUR`. **Istniejąca poprawka**, nie nowo tworzona: [PR #186](https://github.com/karolbarankiewicz1984-ui/kb-score-3/pull/186) umożliwia odseparowanemu badawczemu Shadow pominięcie wyłącznie naprawdę nieobecnego kraju TUR w oficjalnym katalogu; inne błędy pozostają fail-closed. [V3-R #45071343565](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/45071343565) później zakończony SUCCESS: 45 nowych M0-matched rzeczywistych shadow forecastów, 119 łącznie w niezależnym archiwum. Nie udawać, że poprzedni FAIL jest nadal nierozwiązany.
- [Historical backfill #45067925011](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/45067925011) FAIL w tym samym okresie; późniejszy [#45071343451](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/45071343451) PASS dla offline i live, rzeczywisty przyrost +24 meczów, +22 natywnych xG, przy braku kraju TUR. Zgodnie z polityką FORWARD-FIRST historyczny backfill pozostaje P2, cotygodniowy; obecne błędy starej gałęzi nie są powodem ponownego intensywnego pobierania.
- [Market freeze #45109170879](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/45109170879), 23 XI: `ModuleNotFoundError: cryptography` w fazie atestacji GitHub-hosted ZIP. **Istniejąca poprawka**: [commit 4b8d9d8](https://github.com/karolbarankiewicz1984-ui/kb-score-3/commit/4b8d9d8fa2c483c2f1fc5ec0b5ce87266b811434) instaluje bibliotekę i wykonuje smoke-test przed pobraniem ZIP. [Rzeczywisty run #45117523199](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/45117523199) zakończył oba joby SUCCESS: 45 nowych potwierdzonych hostem rynków i 25 nowych rozliczeń badawczych. To **osobny** ledger market, nie to samo co 208 głównych rozliczeń M0.

### Otwarte
- [Receipt M0 z 23 XI, 02:47 UTC](../data/pit_sidecar/m0_720_eight/2026-11-23/settle-024730964942/RECEIPT.json): `git_server_push_verified_forecasts=268`, `settled_total=208`, `new_settlements=20`, `not_yet_settled=60`, `missing_catalog_leagues=["TUR"]`, `league_count=7`, `partial_source_coverage_research_only=true`. **Odczytano rzeczywiste 80 decyzji settlement z tej samej migawki**, nie tylko sumę 60:
  - `RESULT_MATURITY_3H_NOT_REACHED=49`: termin lub wymagany odstęp od kickoff jeszcze nie kwalifikuje prognozy do rozliczenia (TUR 1, POL 7, ITA 7, ESP 7, NED 7, GER 7, BEL 6, FRA 7). Nie są to 49 potwierdzone awarie.
  - `PROVIDER_RESULT_MISSING=8`: **wszystkie TUR**, przy brakującym kraju TUR w dostępnym katalogu; nie wolno zgadywać wyniku ani zastępować ligi.
  - `KICKOFF_CHANGED_REVIEW_REQUIRED=3`: **FRA 2, POL 1**. Wymaga oddzielnej kontroli zmian czasu kickoff, autentycznego ID i prawidłowego cut-off bez cofania wcześniejszej prognozy.
  - `SETTLED_NEW=20`: NED 3, POL 2, ITA 4, FRA 3, GER 2, BEL 3, ESP 3; te 20 są rzeczywiście rozliczone i nie wchodzą w 60 oczekujących.
- P0 do następnych odczytów: ponownie klasyfikować 49 po upływie 3h zgodnie z logiką i faktycznym stanem meczu; osobno rozliczyć 8 TUR dopiero gdy provider zwróci autentyczne wyniki; wyjaśnić 3 rozbieżności kickoff bez nadpisywania immutable snapshotów. Sprawdzić najnowsze po audycie scheduled runs. Nie traktować dawnego FAIL jako dowodu przyszłej niesprawności.

**Wynik kroku 1:** dwa rozpoznane incydenty są już naprawione i mają późniejszy rzeczywisty LIVE PASS, M0 ma faktyczny przyrost rozliczeń; klasyfikacja 60 i następne cykle wymagają dalszej kontroli. Brak nowych płatnych API w tym audycie.

## 2. Krok 16 — analiza kalibracji FIT100 / HOLDOUT50 (PASS badawczy, formalny GATE PENDING)

- [Raport źródłowy 23 XI](KB3_HOLDOUT50_MODEL_DECISION_AUDIT_2026-11-23.md) oraz [Actions #45137310981](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/45137310981) potwierdzają self-test i niezależny audyt rzeczywistego immutable SQLite/HOLDOUT.
- Wersja modelu `M0_ELO_POISSON_RESEARCH_720TRAIN_V1`, próba do kalibracji FIT100, niezależny pierwszy późniejszy HOLDOUT50. `T=0.7` było wcześniej ustalone i zamrożone, a NIE dopasowane ponownie do HOLDOUT.
- Na 50 HOLDOUT: trafność top1 **29/50=58%** (bez zmian po temperature scaling); Brier sum3 `0.56695415 → 0.55081560`, log loss `0.95540357 → 0.93163311`, top1 ECE10 `0.17106788 → 0.04529290`. To poprawa na małej próbce, **nie gwarancja przewagi na kolejnych meczach ani przy kursach**.
- [Receipt M0](../data/pit_sidecar/m0_720_eight/2026-11-23/settle-024730964942/RECEIPT.json) ma `holdout_review_exists=true` i `missing_post_fit_holdout=0`, ale także `50_future_after_fit_verified=false` i `gate16=PENDING`. **Sprawdzono implementację:** `50_future_after_fit_verified=False` jest **sztywną, konserwatywną wartością w wyniku funkcji `settle_sqlite`** w [kodzie](../src/kb3_step16_m0_720_eight_forward.py); sama nie rozstrzyga, czy osobny, późniejszy HOLDOUT50 istnieje. Aktualny dokument bramki wymaga rozdzielenia „PASS niezależnego badawczego audytu” od „formalny PASS i wdrożenie”. Nie przestawiono flagi ani statusu ręcznie.
- Dalsze badania: kolejne niezależne mecze/tygodnie po tym HOLDOUT, ocena stabilności z przedziałami niepewności, dokument bramki i separacji chronionego ENG TEST. Wybór produkcyjnej kalibracji wymaga osobnej decyzji. Nie trenować/dostrajać na 50 HOLDOUT.

**Wynik kroku 2:** techniczny audyt rozłącznej próby = PASS; formalna decyzja GATE16 i zastosowanie produkcyjne = PENDING. FIT/HOLDOUT, parametry M0, T=0.7 i Champion nietknięte.

## 3. Krok 17 — uczciwe porównanie na wspólnych spotkaniach (START / RESEARCH)

Z [niezależnego audytu 23 XI](KB3_HOLDOUT50_MODEL_DECISION_AUDIT_2026-11-23.md): **135 tych samych host-attested meczów, tylko dwa niezależne bloki tygodniowe**, identyczny przedmeczowy 1X2.

| Silnik | Top1 accuracy | Brier sum3 (mniej lepiej) | Log loss (mniej lepiej) |
| --- | ---: | ---: | ---: |
| M0 Elo + Poisson | 56.30% | 0.579740 | 0.975656 |
| Elo-only | 55.56% | 0.571945 | 0.962666 |
| CatBoost bez xG | 58.52% | 0.576960 | 0.974073 |

Wniosek: CatBoost bez xG ma wyższą **opisową** trafność top1, ale Elo-only w tej próbie lepiej wypada według obu metryk jakości prawdopodobieństw. Brak przewagi zgodnej we wszystkich metrykach i zbyt mało niezależnych tygodni do formalnego wyboru. Oddzielny Shadow Six na 84 wspólnych spotkaniach ma gorszy Brier/log loss od M0; V3-R to kolejna **odrębna** wersja, nie wolno sklejać jej z Shadow Six i zbiorami historycznymi. CatBoost with-xG wymaga własnych rzeczywistych, poprawnych par z odpowiednią wersją M0, bez retro-backfillu prognoz.

- Już istnieje tygodniowy [workflow read-only](../.github/workflows/kb3-holdout50-weekly-research.yml) (poniedziałek 07:25 UTC, plus manual), bez wywołań provider API i bez modyfikowania bazy; [real PASS #45137310981](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/45137310981).
- Do GATE17 wymagane: następne odrębne bloki tygodniowe, per-fixture różnice Brier/log loss z poprawną niepewnością uwzględniającą zależności czasowe, stabilność per liga, kompletność odpowiednich cech, brak błędów chronologii. Żadnego automatycznego wybrania Championa, GATE17=PENDING.

## Ochrona i kolejny checkpoint

Nie otwarto chronionego Premier League TEST 2026/27, nie zmieniono oryginalnych prognoz, model weights, kodu do prognoz, FIT/HOLDOUT, statusu GATE16/17 ani repozytorium MultiModel. Nie wykonano w tej operacji płatnych odczytów PitchAPI, żadnego treningu ani fałszywego `PIT PASS`. Zadania 1–3 uruchomione jako audyt i priorytety działania, **nie** oznaczone jako ukończone wdrożenie. Weryfikacja audytu: Gmail GitHub notices, GitHub Actions jobs/logi, istniejące zachowane receipts/rejestr i niezależny read-only HOLDOUT50 CI.

**Kolejny checkpoint:** klasyfikacja 60 pending po kickoff, najnowsze schedule results, przejrzenie semantyki flagi `50_future_after_fit_verified`, przyrost identycznych forward par i tygodni. Po uzyskaniu nowych wyników dodać odrębny append-only wpis, nie nadpisywać historycznych PASS/FAIL.

## Kontynuacja 23.11 — diagnostyka przesunięć i poprawa bramki GATE17

**Nowe wykonane zmiany w kodzie na `main`, bez ręcznego nadpisywania źródeł:**

1. [`src/kb3_step16_m0_720_eight_forward.py`](../src/kb3_step16_m0_720_eight_forward.py), commit [8b876543](https://github.com/karolbarankiewicz1984-ui/kb-score-3/commit/8b876543204081327616538a9d56d6d86a8f9f88): wyłącznie dla `KICKOFF_CHANGED_REVIEW_REQUIRED` przyszła `settlement_decisions` zawiera oryginalny zamrożony i nowy źródłowy kickoff UTC, delta minut, czas capture, zgodność ID obu drużyn, warunek wcześniejszego 90-minutowego freeze, `manual_review_required=true` i `automatic_settlement_permitted=false`. **Nie dodano możliwości automatycznego rozliczenia.** Historyczne receipts pozostają niezmienione, dlatego wcześniejsze 23.11 nie zawierają nowej godziny.
2. [`tests/test_m0720_operations.py`](../tests/test_m0720_operations.py): nowe syntetyczne regresje wcześniejszego/późniejszego kickoff, brak settlement i nienaruszone immutable forecast SQL, commit [4f1978b9](https://github.com/karolbarankiewicz1984-ui/kb-score-3/commit/4f1978b93c34f020c7eaf7dfd5c9e1f192a6142b).
3. [`scripts/kb3_review_postfit_readonly.py`](../scripts/kb3_review_postfit_readonly.py), końcowy commit [c6849eb8](https://github.com/karolbarankiewicz1984-ui/kb-score-3/commit/c6849eb83d8d904ed85a0b21171efd36c14943dd): w tygodniowym CI kontrola `pending_settlement_review` zestawia wszystkie niezamknięte rekordy z ostatnimi decyzjami oraz z rzeczywistym `forecasts` SQLite otwartym `mode=ro`, sprawdza SHA, oryginalny cutoff, liczniki i identyfikatory; rozdziela `RESULT_MATURITY_3H_NOT_REACHED`, `PROVIDER_RESULT_MISSING` i `KICKOFF_CHANGED_REVIEW_REQUIRED`. Nie wypełnia nieznanej nowej godziny z pamięci. Gdy nowy live `RECEIPT` zawiera oba czasy, sprawdza także zgodność delty minut i zakaz auto-settlement. `--self-test` ma przykłady negatywne dla sfałszowanej godziny.
4. **GATE17 — znaleziony metodologiczny rozjazd i poprawka:** [formalny `src/kb3_step17_engine_comparison.py`](../src/kb3_step17_engine_comparison.py) używa `MIN_BLOCKS=8` i rzeczywistego ISO-week cluster bootstrap, ale pomocniczy skrypt gotowości poprzednio używał tylko `weeks>=4`. Od teraz `confidence_intervals_ready` jest TRUE jedynie przy co najmniej **8 tygodniach**, trzech identycznych porównaniach, każdej realnej parowanej `ci95=[lo,hi]` dla Brier/log loss/top1, `status=PAIRED_ISO_WEEK_BOOTSTRAP` i prawidłowych liczbach. Dodatkowe `missing_independent_week_blocks_for_ci` podaje niedobór. Syntetyczne selftesty odrzucają 4 tygodnie oraz 8 tygodni bez `ci95`. **Na danych 23.11: 2/8 tygodni, brak 6, GATE17 PENDING.**
5. **Przejście do kolejnego checkpointu**: po pierwszym nowym skutecznym run M0 / read-only CI sprawdzić 3 przypadki `FRA: m_1ronn6, m_264TKg; POL: m_4dpQ5H` (stary vs nowy kickoff, ID home/away, pierwotny freeze, autentyczny wynik 90-minutowy), rozliczyć dopiero po jawnej walidacji, bez wstecznej modyfikacji danych. W raportach 23.11 przypadki mają **tylko status drift**, a nie zweryfikowany nowy kickoff. Kontynuować też 8 TUR przy dostępności wyniku.
6. **CI odbiór:** zapis zmian GitHub potwierdzony, **bieżący rzeczywisty SUCCESS nowej wersji CI jeszcze niezweryfikowany**. Nie wpisywać PASS self-testów tylko z faktu dodania kodu/testów. Bez nowszych autentycznych danych liczności historyczne pozostają 268 frozen / 208 settled / 60 pending (na timestamp ostatniego poświadczonego receipt), a nie aktualna prognoza stale rosnącej bazy.

Formalny GATE16 wciąż PENDING mimo udanego niezależnego audytu HOLDOUT50. GATE17 PENDING mimo startu porównań. Żadnego auto-awansu, nie dotknięto chronionego ENG TEST ani historycznej oryginalnej certyfikacji PIT.
