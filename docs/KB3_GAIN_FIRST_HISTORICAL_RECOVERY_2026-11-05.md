# KB Score 3.0 — wdrożenie gain-first history backfill i recheck — 05.11.2026

## Zakres faktycznie zrealizowany

- Na polecenie właściciela wdrożono jako kontynuację historycznego projektu `KB3-HISTORY-COMPLETENESS-GAIN-FIRST-PROPOSAL-20261105` nowy algorytm podnoszący priorytet brakujących statystyk, które *mogą* domknąć rzeczywiste zestawy pięciu poprzednich meczów obu drużyn.
- [Pull request #162](https://github.com/karolbarankiewicz1984-ui/kb-score-3/pull/162) **MERGED** do `main` commit `791b75af346f9a3101d1e2a8e57e3c0c81ffae51`.
- Nowy `scripts/kb3_history_gain_first.py` liczy realny chronologiczny last5 dla 8 lig na rzeczywistym `finished_fixture_index`; zakłada cutoff `kickoff−2h` i ukończenie poprzedniego meczu minimum `+3h`. Uwzględnia istniejące oryginalne statystyki, oddziela nieobserwowany poprzedni mecz (nowy fetch) od istniejącej obserwacji ze statystycznymi brakami (recheck). Nie podstawia starszych meczów za brakujące i nie używa wyniku docelowego spotkania jako jego cechy.
- W `scripts/kb3_historical_pitchapi_backfill.py` **maksymalnie 75% każdej 48-meczowej partii** pochodzi z rangowania potencjalnego przyrostu próbek Core5 i Core5+xG5. **Pozostała część** zachowuje dawny selektor, równoważenie lig i istniejące limity `max_matches=48`, `max_calls=150`, 5 osobno sealed batches w przyspieszonej ścieżce. Brak nowego dostawcy i dodatkowego API.
- W `scripts/kb3_history_issue_recheck.py` próby dotąd nierozstrzygniętych żółtych kartek oraz xG są porządkowane według realnego wpływu na historyczne, poprzedzające target spotkania, z preferencją dla NED/POL/TUR. **Wcześniej zbadanych rozbieżności nie powtarza się automatycznie**; konflikty `EVENTS_TEAM_STATS_CONFLICT` i `XG_DISAGREEMENT_PERSISTS` nie są uznawane za poprawne pomiary.
- Dodano sześć osobnych testów w `tests/test_kb3_history_gain_first.py`; historyczny CI nadal uruchamia wszystkie wcześniejsze zabezpieczenia, bez sekretu PitchAPI w PR.

## Niezależny dry-run na faktycznej historycznej SQLite

- [GitHub Actions #42037346794](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/42037346794) **SUCCESS**; 53/53 sprawdzeń offline PASS (12+4+6+8+7+16), dry-run na oryginalnej 53 837 824-bajtowej SQLite z **2001** faktycznymi statystycznymi obserwacjami. Źródłowy SHA256 `0eae525fac24c359b6441160950cd32f907ebbb64a815dafa957f5ef2ff4e765` nie zmienił się.
- Rozpoznano **6069** brakujących, dostępnych w *oryginalnym indeksie* potencjalnych poprzedników; to nie jest jeszcze sprawdzony katalog aktywnych endpointów dostawcy. Wybór `36` (maksimum gain-first w partii 48) wyniósł `TUR 32 / NED 3 / ESP 1`. Potencjalne korzyści **warunkowe** przy pełnych przyszłych odpowiedziach i zgodności źródeł: `35` targetów History5, `19` Core5 i `14` Core5+xG5. **NIE uznawać tych wartości za faktycznie zebrane ani za gwarantowane.** Lista priorytetów z realnej zaktualizowanej listy provider fixtures w live może się różnić.
- Odrębne już istniejące `issue_rechecks`: odnaleziono **163** historyczne strony/games z potencjalnym wpływem naprawy kartek na komplet Core5 i **201** z potencjalnym wpływem naprawy xG. To liczności punktowanych kandydatów, NIE dopisanych obserwacji ani nowych pełnych zestawów.
- Brak zmiany `M0`, przypiętego `Shadow Six`, 23 autentycznych par freeze, 100 FIT+50 przyszłych HOLDOUT, `GATE16/GATE17`, formalnego historycznego PIT i chronologicznego TEST.

## Kontrola wykonania pierwszego live-run

- Po merge uruchomił się **rzeczywisty** [GitHub Actions #42037486832](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/42037486832) (event=`push`, `main`). Stan ostateczny, nowe faktyczne `new_match_stats` i `Core5/xG5` należy zapisać dopiero po zakończeniu i po przeczytaniu **autentycznych** `ACCELERATED_CAPTURE_REPORT.json` oraz `ROLLING_AFTER_RECHECK.json`. Nie utożsamiać dry-run forecast 19/14 z wynikami live.

## Co wymaga osobnych dowodów

1. **Zewnętrzne źródło:** Football-Data udostępnia CSV historyczne z podstawowymi statystykami dla części lig. Test alternatywnego dostawcy na 20–30 meczach pozostaje osobnym `SOURCE_PILOT_PENDING`: bez zweryfikowanego pobrania źródłowych CSV, dokładnego dopasowania drużyn i czasu meczu, zgodności definicji i praw do użycia nie wolno integrować tych danych z natywnym PitchAPI. Brak nowego abonamentu i brak deklaracji, że takie dane już odzyskano.
2. **Rozbieżności xG:** utrzymane `NULL` dla różniących się `shots` i `stats` do czasu rzeczywistej niezależnej diagnozy semantycznej / drugiego źródła; żadnego „uzgadniania” liczb bez dowodu.
3. Kontynuować kolektor, monitorować `ΔCore5`, `ΔCore5+xG5` po kolejnych prawdziwych uruchomieniach, z rozbiciem per liga; jeśli bonus NED/POL/TUR powoduje systematyczny brak postępu, zmienić politykę wyłącznie po realnym porównaniu A/B.

**Status:** kod i CI PR #162 **WYKONANE I WDROŻONE**; live first post-merge uruchomione, jego rzeczywiste liczby wymagają osobnego odbioru; zewnętrzny CSV pilot niezintegrowany.
