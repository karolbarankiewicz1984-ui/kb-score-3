# KB Score 3.0 — 26.10.2026: uproszczenie do jednego źródła sportowego

## Decyzja techniczna

**Preferowane główne źródło dla nowych danych meczowych: PitchAPI.** Aktualny stan `SHADOW_ONLY_NOT_PRODUCTION`; **GATE11 PENDING (10/29)**. Nie wykonano migracji starych baz, nie wyłączono ich przywracania, nie włączono ML ani prognoz. Zasada do pilota: **identyfikator jednego dostawcy** opisuje datę, parę drużyn, wynik końcowy i strzały xG. Kursy bukmacherskie pozostają oddzielnym obszarem danych rynkowych, bez wpływu na tożsamość spotkania.

**Powód:** co najmniej 5 z 10 ostatnich przypadków PitchAPI xG musiało pozostać w kwarantannie wyłącznie przez łączenie z nazwami/identyfikatorami z API-Football. To ryzyko znika w nowych obserwacjach opartych o natywny `PitchAPI.match_id`. Pięć starych kwarantann **nie zostaje na siłę zatwierdzonych** ani wymazanych — są dowodem dawnej architektury, ale nie będą potrzebne w nowym przepływie. Wcześniejsze archiwa 760 i PIT zachowano tylko do odczytu.

## Zakończone prawdziwe testy dostawcy

[Actions — 3 sezony, terminarz oraz xG](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40312167476), zakończone `SUCCESS`:

| Kontrola | Wynik |
|---|---:|
| Premier League 2023/24 | 380/380, wszystkie finished |
| Premier League 2024/25 | 380/380, wszystkie finished |
| Premier League 2026/27 | 380/380, w tym 80 finished + 300 not_started |
| Unikatowe ID spotkań w każdym sezonie | 380/380 |
| Próbki xG z natywnym ID PitchAPI | 5/5 kompletne |
| API-Football | 0 wywołań |
| PitchAPI | 9 wywołań |
| Wydatek na nowy abonament | 0 |

Dodatkowy rzeczywisty audyt [Actions — UEFA + faule/kartki](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40312704445) także `SUCCESS`:

- Liga Europy 2026/27: **144** rozpoznane spotkania, z czego **54** finished i **90** przyszłych.
- Liga Konferencji 2026/27: **108** rozpoznanych spotkań, z czego **36** finished i **72** przyszłe.
- W jednej rzeczywistej odpowiedzi statystyk z Premier League sprawdzono **41 kluczy**, wśród nich `fouls`, `yellow_cards` i `red_cards`.
- **5 zapytań PitchAPI**, **0 API-Football**.

To dowodzi wykonalności podstawowego rozwiązania dla tych rozgrywek. **Nie dowodzi** kompletności xG ani fauli dla *wszystkich* spotkań Ligi Europy i Ligi Konferencji. Katalog PitchAPI w czasie testu miał **77 lig**, a dostępne statystyki i historia zależą od pokrycia; nie należy ekstrapolować PL na całą ofertę.

## Kod i zabezpieczenia

- `src/kb3_pitch_native.py`: walidator meczów, drużyn, wyników i statystyk xG, korzystający wyłącznie z natywnych identyfikatorów PitchAPI. `match_id` z odpowiedzi strzałowej **musi** być identyczny z `match_id` terminarza; różny ID blokuje zapis. Brakujące xG reprezentowane przez `NULL`, nie zero.
- `src/kb3_pitch_native_features.py`: eksperymentalny `shadow_native` do obliczania ELO, formy 5/10/15 i historycznego xG z tej samej pary identyfikatorów, bez łączenia z API-Football. Przyszły mecz docelowy jest odrzucany z historii, wynik wcześniejszego meczu wchodzi dopiero po udokumentowanym odczycie i minimalnym opóźnieniu, xG dopiero po **swoim** odczycie. Raport ma flagę `requires_future_verified_receipt_ledger=true` i nigdy nie twierdzi, że surowe dane ze *shadow* zapisano trwale.
- `scripts/step11_pitch_single_provider_shadow.py`: rzeczywisty test 3 sezonów PL + pięciu xG, tylko 9 wywołań jednego dostawcy, raportuje sumy i hashe, nie publikuje rekordów/klucza.
- `scripts/step11_pitch_native_uefa_stats.py`: dodatkowa kontrola UEFA, 5 wywołań.
- `config/STEP11_PROVIDER_POLICY.json`: kandydat na podstawowe źródło, procedura akceptacji i zakaz automatycznej migracji starych baz.
- **160/160 testów offline PASS** [GitHub Actions #40313071652](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40313071652): 121 testów Step11 i 39 regresyjnych Step08–10, testy starego dwudostawcowego trybu nadal bez zmian.

## Co jeszcze trzeba wykonać przed faktyczną migracją

1. Zbudować **szyfrowany append-only dziennik PitchAPI**: zapisywać rzeczywiste timestampy pobrań terminarzy, wyników i strzałów xG; nie wnioskować `published_at` z dat meczu.
2. Sprawdzić na próbie zdarzeń zmianę `not_started → finished`, zachowanie tego samego ID po przełożeniu meczu i korektę wyniku, z ochroną przed lookahead.
3. Rozszerzyć próby obecności statystyk i xG w LE/UECL i głównych ligach, szczególnie dla rynków fauli i kartek. Warunki licencyjne i retencja muszą być zgodne z wykorzystaniem.
4. Zdecydować, czy brak kursów w tym sportowym API wymaga osobnego dostawcy kursów. **To nie będzie drugi dostawca wyniku/terminarza, tylko osobne źródło cen rynkowych.**
5. Dopiero po zatwierdzeniu jakości i backupu jawnie przełączyć produkcyjne nowe pobrania na PitchAPI; poprzednie archiwa API-Football zostawić w trybie `legacy`, bez niejawnego mieszania drużyn.

**Brak certyfikowanego historycznego PIT dla 2023–2025, brak treningu, GATE11 pozostaje PENDING, formalnie 10/29.** Dostawca publicznie reklamuje brak opłat, ale ta cecha oferty może ulec zmianie. Stan potwierdzony dla wykonanych testów, nie dla wszystkich 77 lig. **Nie zmieniano** KB Score 2.1, API Market, MultiModel.
