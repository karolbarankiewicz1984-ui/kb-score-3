# KB Score 3.0 — Krok 14: niezależny czas publicznego PushEvent z GH Archive (27.10.2026)

**Wynik: 2/4 wybranych SHA mają niezależne zdarzenie publicznego wypchnięcia do gałęzi `master`**, potwierdzone archiwum publicznych zdarzeń GitHub, a nie tylko datą `commit.committer.date`. Dwie pozostałe godzinowe próbki były **niedostępne (HTTPError)**; ich brak w raporcie nie dowodzi braku historycznego pusha. **Nadal brak dowodu oryginalnych `home_team_id/away_team_id` PitchAPI z szyfrowanego archiwum i PIT wszystkich cech modelu.**

Podstawa i metoda: [GH Archive](https://www.gharchive.org/) gromadzi historyczne publiczne zdarzenia `PushEvent` w plikach hourly `YYYY-MM-DD-H.json.gz`. Przeczytano strumieniowo dokładnie cztery wybrane godziny dla SHA poprzednio ustalonych w [audytach 25 realnych starych blobów](STEP_14_HISTORICAL_BLOB_IDENTITY_2026-10-27.md). Każdy dowód wymaga `repo.name=openfootball/football.json`, `type=PushEvent`, `payload.ref=refs/heads/master`, exact `payload.head` albo `payload.commits[*].sha` oraz GitHub-server `created_at < kickoff`. Źródłowy SHA Git prowadzi do konkretnego pliku sezonowego, którego treść i własny SHA256 zostały wcześniej sprawdzone w historycznym audycie. Są to zatem dwa dowody realnego *zdarzenia udostępnienia commita publicznie*; nie tylko edytowalnego pola autora.

| Publiczny commit | GH Archive server UTC | GH Archive public event ID | Ref | Status |
| --- | --- | --- | --- | --- |
| `5f777dc6e2cd02cdafd1520e81b7e338284fb7a7` | **2024-10-02 13:52:44 UTC** | `42475053178` | `refs/heads/master` | PUSH CORROBORATED |
| `fdca227e6fc8284865254f009e987ce7a70935a0` | **2025-07-30 16:20:53 UTC** | `52743265113` | `refs/heads/master` | PUSH CORROBORATED |
| `d0a780d5a22b34375f320a51e52e723814d59aff` | niepotwierdzony | — | — | Hourly archive HTTPError |
| `831bb41621b99b7081f9942ff294fb3c91165448` | niepotwierdzony | — | — | Hourly archive HTTPError |

Źródłowe godziny GH Archive:
- https://data.gharchive.org/2024-10-02-13.json.gz
- https://data.gharchive.org/2025-07-30-16.json.gz

Dwa sprawdzone SHA występują w sześciu rekordach naszego pilotażu 60 spotkań: **4 przypadki mają jedno dokładne dopasowanie rozkładu godzinowego do meczu OpenFootball, 2 nie znajdują meczu o tym kickoff w danym starym pliku**. Cztery prowizoryczne powiązania są następujące:

| PitchAPI native `fixture_id` z oryginalnego SAFE Step12 | Kickoff UTC | Kandydat nazw pary z old blob | SHA z niezależnym PushEvent |
| --- | --- | --- | --- |
| `m_3AMymS` | 2024-10-05 16:30 | Everton FC – Newcastle United FC | `5f777dc6e2cd…` |
| `m_4AseJ9` | 2025-08-18 19:00 | Leeds United – Everton FC | `fdca227e6fc8…` |
| `m_0lzfjT` | 2025-08-31 15:30 | Liverpool FC – Arsenal FC | `fdca227e6fc8…` |
| `m_0JJdwI` | 2025-09-21 13:00 | Sunderland AFC – Aston Villa | `fdca227e6fc8…` |

W szczególności daty committera **nie służą już jako jedyna podstawa zegara** w tych czterech kandydaturach. Dane z kopii GitHub/archiwum publicznego potwierdzają publiczną obecność SHA wcześniej niż dane mecze. Jednak **dopasowanie pary po kickoff nadal nie jest zweryfikowanym połączeniem natywnych obu IDs drużyn PitchAPI** i ma status `PROVISIONAL_KICKOFF_ONLY`. Poprzednia mapa 3 meczów z października 2026 nie jest dowodem na sezony 2023–2026.

Utrwalony [raport z dokładnymi event ID, nazwami gałęzi i server time](../data/audits/STEP14_GHARCHIVE_SERVER_PUSHCLOCK_2026-10-27.json), [kod niezależnego testu](../src/kb3_step14_gharchive_clock.py), [testy jednostkowe](../tests/test_step14_gharchive_clock.py), [GitHub Actions #40493703798](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40493703798) **4/4 PASS**.

## Dalsza wymagana bariera

Pełna certyfikacja konkretnego oryginalnego `fixture_id` wymaga autentycznej natywnej pary identyfikatorów drużyn i źródłowego łańcucha PitchAPI z pierwotnego zaszyfrowanego archiwum — odczyt przez właściciela klucza prywatnego na zaufanym komputerze, bez przekazywania klucza do chatu lub GitHub. Potrzebny jest też osobny PIT *wszystkich użytych cech* (historical Elo/forma/xG as-of) przed cutoff, a nie tylko wiedza, że sama data/mecz były widoczne w OpenFootball. Etykiety, kursy i wyniki docelowych spotkań nie mogą pomagać w doborze identyfikatorów ani cech.

**Oficjalnie 0/760 TRAIN dopuszczonych. Krok 14 W REALIZACJI, GATE14 PENDING, ukończone 13/29.** M0, zamrożone prognozy i nietykalny TEST bez zmian. Nie użyto płatnego sportowego API.
