# KB Score 3.0 — Krok 14: korekta crosswalk po rzeczywistej zmianie terminarza (2025-09-03)

**Wynik rozpoznania 27 października 2026:** odszyfrowanie oryginalnego, SHA-pinned archiwum PitchAPI *powiodło się lokalnie u właściciela klucza*. Weryfikator w pierwotnej wersji zwrócił `TOTAL 4, MATCHED 3, TRAIN 1, VALIDATION 2`. Właściciel **bez udostępniania surowych t_... ani klucza** zweryfikował publicznie na swoim terminalu 3 przypadki ze zgodną parą nazw, datą i sezonem. Dla `m_0JJdwI` realne, uwierzytelnione archiwum PitchAPI zawiera:
- `pitch_home_name = AFC Bournemouth`,
- `pitch_away_name = Newcastle United`,
- `kickoff_utc = 2025-09-21T13:00:00Z` i sezon `2025-26`,
natomiast przypięty SHA **2025-07-30** OpenFootball wskazywał w tym terminie `Sunderland AFC – Aston Villa`. **To dwa zupełnie inne mecze, nie alias nazwy**; oryginalna wartość 3/4 była słuszną odmową mechanizmu fail-closed.

## Ustalone źródło pomyłki

Premier League w oficjalnej [informacji o korektach terminarza z 3.09.2025](https://www.premierleague.com/en/news/4406114) wymienia niedzielę **21.09.2025, 14:00 BST — AFC Bournemouth v Newcastle**. Klub [Newcastle United w osobnym komunikacie z 3.09.2025](https://www.newcastleunited.com/en/news/new-date-and-kick-off-time-for-magpies-bournemouth-trip) potwierdza przesunięcie *z soboty 20.09.2025 godz. 15:00 BST na niedzielę 21.09.2025 godz. 14:00 BST*, ze względu na terminarz Ligi Mistrzów. 14:00 BST = **13:00 UTC**.

Tego samego dnia i o tej samej godzinie miał się odbyć również **Sunderland–Aston Villa** (zob. [oficjalny terminarz Premier League 2025/26](https://www.premierleague.com/en/news/4324539)). Stara migawka OpenFootball, publicznie wypchnięta na GitHub **30.07.2025, 16:20:53 UTC** (GH Archive event `52743265113`), **nie mogła jeszcze odzwierciedlać późniejszej zmiany z 3 września 2025**. Nawet jej wstępnie „jedyny” terminowy kandydat mógł więc być cudzym meczem, bo drugi mecz został przełożony na ten sam termin.

**Wniosek metodologiczny:** nie stosować `fixture_id` ↔ zewnętrzne gospodarze/goście tylko na podstawie identycznego `kickoff` w starszym snapshot. Sprawdzać *historyczne zmiany terminu* oraz **natywne oba team_id + nazwy ze źródła PitchAPI**. Nie wolno także przepisywać poprawionych nazw **w miejsce starego OpenFootball bloba**: jego SHA, źródłowe dane Sunderland–Villa i czas rzeczywistego publicznego Git PushEvent pozostają bez zmian.

## Co poprawiono w kodzie

[Weryfikator lokalny](../src/kb3_step14_native_team_crosswalk.py) posiada dokładnie jeden jawny wyjątek **OFFICIAL_FIXTURE_AMENDMENT dla `m_0JJdwI`**. Zachowuje starego kandydata `Sunderland AFC – Aston Villa` w niezależnym audycie, ale do weryfikacji właściwej natywnej pary PitchAPI używa oficjalnie skorygowanych nazw `AFC Bournemouth – Newcastle United`. Sprawdza dokładnie 2025-09-21T13:00:00Z, oryginalny SHA starego harmonogramu, bazowy SAFEVIEW i serwerowy Git Archive PushEvent, rolę VALIDATION i autentyczny PINNED archiwum PitchAPI; **bez rozluźnienia kontroli dla innych fixture IDs**.

Prywatny raport lokalny po ponownym wykonaniu udokumentuje rozdzielnie:
- `public_candidate_home_name/away_name`: pierwotne Sunderland–Aston Villa ze starego bloba,
- `official_revised_fixture_home_name/away_name`: Bournemouth–Newcastle po korekcie z 3.09.2025,
- `archival_july_schedule_team_pair_match=false`,
- `used_official_september_reschedule_evidence=true`,
- `external_fixture_identity_crosswalk_confirmed`: zależy od rzeczywistego niezależnego ponownego odczytu obu natywnych team IDs/nazw,
- `official_article_editorial_date_is_independent_PIT_receipt=false`,
- `historical_prematch_PIT_certified=false`, `production_catboost_training_allowed=false`, `gate14_pass=false`.

**UWAGA:** dopóki właściciel nie wykona ponownie programu lokalnie po aktualizacji kodu, rzeczywisty raport pozostaje `MATCHED 3/4`. CI na mockach nie jest rzeczywistym odtworzeniem prywatnego archiwum. Dowodem poprawności algorytmu jest [GitHub Actions #40538194007, 12/12 PASS](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40538194007), w tym negatywny test: sztuczne PitchAPI z błędną starą parą Sunderland–Villa NIE uzyskuje statusu `external_fixture_identity_crosswalk_confirmed`. Trzeba natomiast na komputerze właściciela z tą samą oryginalną kopią i kluczem ponownie zbudować **nowy osobny** prywatny raport (nowa nazwa; runner zabrania nadpisywania istniejącego pliku).

Zmiana terminarza poprawia **identyfikację meczu**, ale **nie** potwierdza historycznej dostępności wszystkich statystyk Elo/xG/formy przed cutoff; oficjalny M1 train wciąż **0/760**, GATE14 PENDING, stan planu 13/29, TEST nietknięty, źródło PitchAPI główne, brak nowych kosztów API.

## Uzupełnienie po rzeczywistym ponownym odczycie u właściciela (27.10.2026)

**Poprzednia UWAGA o konieczności ponowienia testu jest już historyczna.** Właściciel odczytał ponownie to samo autentyczne źródło przy użyciu poprawionego kodu (PR #54) i właściwego lokalnego prywatnego RSA PEM. Terminal bez drukowania par `t_...` podał **`TOTAL 4, MATCHED 4, TRAIN 1, VALIDATION 3, GATE14 PENDING`**. Osobny prywatny raport zapisany tylko na komputerze właściciela pod nazwą `KB3_STEP14_NATIVE_TEAM_IDS_PRIVATE_V2.json`; starego 3/4 nie usunięto. Potwierdzono więc także `m_0JJdwI` jako Bournemouth–Newcastle po późniejszym oficjalnym przełożeniu, przy zachowaniu starej lipcowej kopii Sunderland–Aston Villa jako oddzielnego dowodu. Nie publikowano klucza ani identyfikatorów `t_...`.

Zakres tego potwierdzenia to **identyfikacja czterech meczów, nie PIT danych treningowych**. GATE14 nadal PENDING, 13/29 etapów, oryginalne TRAIN 0/760 z poświadczonym kompletem przedmeczowych cech.
