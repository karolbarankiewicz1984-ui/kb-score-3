# KB Score 3.0 — uruchomienie Shadow 6 wyłącznie na przyszłych prognozach (05.11.2026)

**Dyspozycja właściciela:** „Zrób kolejny krok wg tego co proponujesz”, tj. kontrolowany odbiór, merge zależnych PR i uruchomienie Shadow na nowych spotkaniach bez zmiany M0. PR #151–#155 scalono kolejno metodą merge, zachowując historię commits. PR #155 po review i regresji 31/31 ma dodatkową ochronę: przewidywalna niedostępność 6 cech może pominąć jedynie shadow, a M0 i dwa pozostałe challengers pozostają. Nie ukrywa błędów hash/clock/integrity.

## Jak włączono badania

- NOWA osobna konfiguracja **`config/kb3_shadow_six_forward_activation.json`** jest jawnie wersjonowana i ma `enabled=true`, `research_only=true`, `formal_model_approval=false`, `official_fit_increment=0`, `allow_retroactive_predictions=false`, `allow_champion_promotion=false`. To zatwierdzenie do zbierania **nowych** obserwacji, nie awans modelu.
- Funkcja `scripts/kb3_p1_shadow_activation_policy.py` weryfikuje politykę i przypięty jeden CBM SHA256 `58c5a7fc35afe942893a25b96233689d1f7814ec8a93ed689a7b46f553dbbbc5`. Włącza wyłącznie gdy `mode=forecast`, GitHub event = `schedule` lub `workflow_dispatch`, `GITHUB_REF=refs/heads/main` oraz repo dokładnie `karolbarankiewicz1984-ui/kb-score-3`. `push`, `pull_request`, `settle`, `skip` i niegłówne gałęzie dają OFF.
- Workflow `.github/workflows/kb3-step16-m0-720-eight-forward.yml` ma etap `shadow_activation` przed pobieraniem danych sportowych. Jeżeli flag = true, odtwarza konkretny model oraz manifest z trwałego, prywatnego `assets/research/kb3_shadow_six_v1/`, sprawdza oba SHA i dopiero wtedy ten sam oryginalny kolektor PitchAPI tworzy nową prognozę M0 oraz osobny CBM Shadow z **tej samej** migawki danych. Nie wykonuje dodatkowych zapytań do API.
- Każda nowa prognoza CBM trafia do **osobnej append-only tabeli** z niezmiennym identyfikatorem M0, SHA modelu, SHA cech i oryginalnym cutoff. Przewidywane braki 6 cech nie blokują M0, są jawnie oznaczane. Nie ma backfillu starych meczów, zmiany starych M0 forecastów, podmianki prawdopodobieństw, automatycznej kalibracji CatBoost ani awansu Championa.
- **Autentyczny GitHub host-proof nadal wymaga wykonania prawdziwego przyszłego `forecast`, pojawienia się archiwum źródłowych bajtów SQLite przed kickoff−90m, późniejszego `settle`, weryfikacji oryginalnego host-created_at i score settlement.** Sam kod i przełącznik nie generują historycznych dowodów. Liczniki realnych shadow 1X2 / sprawdzonych par zaczynają się od zera do rzeczywistego odbioru.

## Szybki rollback (bez przebudowy lub utraty M0)

Zmienić **wyłącznie** `config/kb3_shadow_six_forward_activation.json`, `enabled` na `false`, i scalić do `main`. Nowe wywołania `forecast` wrócą do trybu M0 + Step17 bez sześcioczynnikowego CBM. Stare istniejące, poświadczone prognozy Shadow **nie są kasowane ani przepisywane**. Nie trzeba wyłączać bazowego harmonogramu M0.

## Odbiór przed scaleniem

Na osobnej gałęzi review testy syntetyczne oraz oryginalna regresja M0 bez nowych provider API. Odrębny workflow `kb3-p1-shadow-six-forward-activation-review.yml` na Python 3.11 + 3.12 sprawdza osiem scenariuszy w tym ON tylko schedule/dispatch/main, OFF settle/push/PR/branch, ścieżkę rollback, poprawne SHA pin i niedopuszczenie promocji. PR pozostanie niescalony w przypadku awarii kontroli. Po rzeczywistym CI uzupełnić tu ID i wynik, nie twierdzić, że już są prawdziwe CBM forecasts przed pierwszym live run.

**Formalny status:** P1-01 częściowy, GATE16/GATE17 pending, M0 100 FIT + 50 nowych HOLDOUT bez zmian, CatBoost wciąż *research-only*. Porównanie 1/X/2 dopiero na prawdziwych, takich samych, poświadczonych hostem i rozliczonych meczach.
