# KB3 v3 — rzeczywisty audyt dwóch archiwów, 2026-11-09

Przeprowadzono rzeczywiste pobranie i lokalny odczyt ZIP GitHub Actions, bez płatnego API i bez zmian M0.

- Historyczny artifact `13635728620` (run `42528150426`), ZIP SHA256 `cbd2002b39a9700f17bb5d0ce2a90f6e93d4d65cd4776c31ba91a5056a633aee`; SQLite `research/historical_multistat/observations.sqlite`: **4401** obserwacji.
- Forward M0 artifact `13643613735` (run `42547104765`), ZIP SHA256 `668e06146599dd8bb25256776ba15704f1b94d7288169a5240bc07c77adc6482`; SQLite `forward_m0_720_eight/kb3_forward_eight.sqlite`: **149** zamrożonych prognoz. Zakres cutoff 2026-10-29T19:47:20.508937Z do 2026-11-05T08:20:18.046808Z.
- Kontrola rzeczywistych wierszy: dla **74/149** prognoz istnieje co najmniej jedna historyczna obserwacja z tej samej ligi z `source_observed_at_utc <= target captured_at_utc` i `predecessor kickoff + 3h <= target captured_at_utc`. Łącznie **10858** par obserwacja–prognoza spełnia te **wstępne**, bardzo szerokie kryteria. Nie sprawdzano tu jeszcze tożsamości drużyny, pełnego okna last5, niezależnej host-publication każdej obserwacji ani pochodzenia natywnego response.
- Przykład: ESP target `m_3apOTP`, cutoff 2026-11-03T14:29:39.361057Z, poprzednik `m_2P8d0o` obserwowany 2026-11-03T13:58:40.439144Z. Jest to jedynie kandydat do kontroli; **nie** dopuszczona cecha.
- **Istotna blokada:** archiwum historyczne z run `42528150426` utworzono dopiero 2026-11-08T22:08:22Z, po wszystkich analizowanych cutoff. Sam obecny ZIP nie stanowi wcześniejszego niezależnego dowodu dla tych 149 prognoz. Wymagane są starsze host-archived runy z oryginalnymi bajtami przed odpowiednimi cutoff.
- Brak certyfikacji pierwszej publikacji dostawcy i pełnego lineage TRAIN/FORWARD. **0** nowych formalnych v3 TRAIN; `NOT_TRAINED`; bez dopisywania wstecznych prognoz, bez zmiany M0/Champion/TEST.

**Następny krok:** odnaleźć starsze oryginalne artefakty GitHub Actions z 3–5 listopada (oraz wcześniejsze), sprawdzić host-created time, ZIP SHA, native member SHA i dopiero wtedy budować target-specific predecessor team last5. Nie używać daty z obecnego ZIP jako substytutu starszego niezależnego świadectwa.
