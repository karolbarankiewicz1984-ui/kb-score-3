# KB Score 3.0 — KROK 13 / W REALIZACJI: Baseline ELO + Poisson

**Rozpoczęcie:** 2026-10-26. **Status:** M0 matematyka i testy referencyjne PASS, **GATE13 PENDING** (brak wiarygodnego historycznego testu i metryk). **Postęp projektu:** nadal **12/29 odebranych**; kroku 13 nie uznajemy za ukończony. Nowe koszty zewnętrzne: 0 zł.

## Zakres i definicja M0

- **ELO drużyn:** standardowa oczekiwana punktacja Elo `1/(1+10^((R_away-R_home-65)/400))`, start 1500, K=20; wynik W/D/L aktualizuje obie drużyny o przeciwnych znakach, bez kursów bukmacherskich. **Elo expected points NIE jest prawdopodobieństwem zwycięstwa.**
- **Poisson:** niezależne bramki 90 minut, proste niezfitowane `mu_home=1.45`, `mu_away=1.15`. Prematch Elo różnica modyfikuje stawki `lambda_home=1.45*exp(0.35*(R_home-R_away)/400)`, `lambda_away=1.15*exp(-0.35*(R_home-R_away)/400)`. Przy przewadze gospodarzy zawartej już w średnich bramkowych **nie dodajemy drugi raz +65 Elo do Poissona**; parametr +65 jest tylko dla aktualizacji oceny Elo. Parametry to ilustracja/test — NIE dane wytrenowane na KB3.
- Z jednej macierzy Poissona obliczane są **P(1), P(X), P(2)**, over 1,5 / 2,5 / 3,5, BTTS TAK, pięć najwyżej prawdopodobnych dokładnych wyników. Usuwanie ogona Poissona jest kontrolowane z tolerancją, P(1X2) sumuje się do 1.
- **Bez ingerencji w inne modele:** bez KB2.1, API Market i MultiModel, kursów/odds, tokenów API, danych z przyszłości, dopasowywania parametrów, losowych prognoz historycznych.

## Referencja matematyczna — wymyślone drużyny i niezatwierdzone parametry

| Przykład sztuczny | Elo gospodarzy | Elo gości | P(1) | P(X) | P(2) | Średnie gole H/A |
|---|---:|---:|---:|---:|---:|---|
| Syntetyczna A/B | 1500 | 1500 | 43.98% | 26.04% | 29.98% | 1.450 / 1.150 |
| Syntetyczna C/D | 1600 | 1500 | 49.62% | 25.11% | 25.27% | 1.583 / 1.054 |
| Syntetyczna E/F | 1400 | 1600 | 33.23% | 26.38% | 40.39% | 1.217 / 1.370 |

**Uwaga:** nie są to typy bukmacherskie, prawdopodobieństwa dla realnych drużyn ani dowód trafności. Sztuczne przykłady sprawdzają wyłącznie matematyczną spójność wzorów.

[Zamrożony raport referencyjny, tylko syntetyczny](../data/audits/STEP13_M0_REFERENCE_2026-10-26.json), SHA256 `38e08689a8d7ca81b96c9b4a8fa4ed8c6e75d5eef617f3f421bb839711c989ff`.

## Formuły miar błędu (syntetyczna kontrola, nie historyczna skuteczność)

- **Multi-class log loss:** średnia `-ln(P prawdziwej klasy)`.
- **Multi-class Brier (sum3):** średnia sumy trzech kwadratów `(p_k - y_k)^2`, zakres 0..2, bez dzielenia przez trzy.
- **Kalibracja:** kontrolna top-class ECE na 5 z góry zadanych koszykach; mała próba syntetyczna nie daje wiarygodnej miary kalibracji.
- Raport zawiera matematyczny test tych funkcji na **3 zmyślonych etykietach**. Wartości log loss, Brier i ECE z raportu NIE SĄ wynikami HISTORYCZNYMI; realne Brier/log loss i kalibracja są nadal niedostępne.

## Bramki jakości i co pozostało do zaliczenia

| Kryterium z PLAN.md | Stan |
|---|---|
| Poisson 1X2 sumuje się do 100% | **PASS** — offline testy 1X2 dla różnic ELO |
| Brak kursów jako wejść modelu | **PASS** — jawne wejścia Elo/parametry, testy odrzucenia nieznanych pól |
| Wzorcowe przykłady | **PASS** — trzy jawnie syntetyczne, deterministyczne przykłady |
| Test HISTORYCZNY na wcześniejszych danych | **BLOCKED** — z kroku12 wiemy 0/1520 dopuszczonych próbek PIT |
| Prawdziwe wieloklasowe Brier, log loss, kalibracja historyczna | **PENDING** — niczego nie fabrykowano |
| Odbiór właściciela pierwszych wyników referencyjnych | **PENDING** |

**Dane:** Step12 niezmienny metodologiczny PASS; w realnej bazie 1220 wstecznych rekordów historycznych i 300 terminarzowych, bez pełnego certyfikatu prematch. Nie wolno wstecznie fałszować historycznego `observed_at` ani traktować odczytu pobranego w październiku 2026 jako źródła przedmeczowego z 2023.

**Następny fragment kroku 13:** opracować zasady rzeczywistego odtworzenia statystyk meczowych/rezultatów (retrospective replay) ze ścisłym oznaczeniem różnicy `reconstructed event-time` kontra `verified provider observed-at`, przepuścić je przez niezależne bramki jakości; dopiero potem ustalać parametry na TRAIN, wybierać EXPANDING vs ROLLING na VALIDATION i mierzyć metryki bez podglądania TEST.

## Dowody

- [Silnik bazowy M0](../src/kb3_step13_baseline.py).
- [Formuły miar referencyjnych](../src/kb3_step13_reference_metrics.py).
- [Wersjonowany generator raportu](../src/kb3_step13_reference_report.py).
- [Testy ELO/Poisson](../tests/test_step13_baseline.py) i [metryk](../tests/test_step13_reference_metrics.py).
- [CI Step13 (offline)](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40375744613).

**GATE13: PENDING. training_allowed=false.** Zamrożony raport syntetyczny nie zastępuje prawdziwego testu historycznego.

## 26.10.2026 — Drugi fragment kroku 13: bezpieczny walk-forward ELO (v0.2)

Dodano rzeczywiście wykonujący obliczenia ELO w czasie [silnik kwartalnego replay](../src/kb3_step13_fold_replay.py) — na **wyłącznie sztucznych danych**. W każdej strategii TRAIN zamraża stan na granicy folda i wylicza z tych ratingów niezależne prognozy VALIDATION. Wyniki ze sprawdzanego kwartału trafiają do oceny **po** zapisaniu wszystkich prognoz, nie do uczenia. Wprowadzono 48-godzinne konserwatywne embargo po kickoff oraz warunek rzeczywistego receipt wcześniejszego od cutoff; to jest syntetyczny test bezpieczeństwa, **nie dowód historycznych godzin publikacji w PitchAPI**. Brak choć jednego wyniku blokuje syntetyczne metryki całego folda. TEST i kursy są blokowane.

Zamrożono [realny audyt gotowości samych terminarzy na 1520 ID](../data/audits/STEP13_REAL_FOLD_READINESS_2026-10-26.json), SHA `814b58950a387ec206673203c51a494b1b82a3a199ab1f9b28f77dac4e84e29b`. Walidacja 60/126/123/71, TRAIN-kandydaci EXPANDING 760/820/946/1069 oraz ROLLING 760/753/750/776, ale **każdy fold: 0 certyfikowanych danych do prawdziwego treningu.** Nie czytano żadnych historycznych etykiet ani nie liczono prawdziwych wyników i metryk modelu. Testy [CI PASS](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40377868431) weryfikują w szczególności, że zmiana etykiety meczowej walidacji nie może zmienić zamrożonej prognozy. [Pełny kontrakt rozróżnienia PIT i retrospektywnego replay](STEP_13_REPLAY_CONTRACT.md).

**GATE13 PENDING; postęp 12/29; training_allowed=false.**

## 26.10.2026 — Uzupełniający test wyników dostępnych w trakcie folda (kontrola prequential)

W odróżnieniu od istniejącego `kb3_step13_fold_replay.py`, który na potrzeby **głównego porównania** zamraża ELO na początku każdego kwartału, przygotowano odrębny **syntetyczny wariant badawczy prequential** `src/kb3_step13_replay.py`. Tu każdą prognozę oblicza się na aktualny kickoff, a wyniki poprzednich spotkań można uwzględnić **dopiero po znanym czasie ich otrzymania**. Dzięki temu testujemy kontrolę lookahead również *wewnątrz kwartału*, bez zmiany oficjalnego protokołu porównawczego z kroku12.

14 testów syntetycznych kontroluje: 2 metody okna historii, opóźnione wyniki, identyczne kickoff, zmianę późniejszych etykiet (nie zmienia wcześniejszych P), wykluczenie TEST, kursów, duplikatów i realnych identyfikatorów, odrzucanie wyników poznanych po datach analizy, SHA freeze. [Implementacja](../src/kb3_step13_replay.py), [testy](../tests/test_step13_replay.py), [niezmienny raport wyłącznie demonstracyjny](../data/audits/STEP13_M0_SYNTHETIC_REPLAY_2026-10-26.json), SHA `68849afe0389e994b51e7ee2f55927fe9e875ca69d3e0d9433a3a8f232ec6d2e`, [CI PASS](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40387731556). W przykładzie występują tylko **2 sztuczne wyniki walidacyjne** i 2/1 sztucznych kandydatów do historii; metryki są jedynie testem kodu i nie wskazują skuteczniejszej metody dla rzeczywistej Premier League.

**Rozróżnienie wariantów:** podstawowy zamrożony kwartalny fold = protokół główny. Prequential = niezależny wariant techniczny, potencjalny eksperyment do osobnej przyszłej oceny, a **nie jego zamiennik**. Nie wybieramy go na podstawie syntetycznych wyników. Nadal `GATE13 PENDING`, `training_allowed=false`, **12/29**.

## 26.10.2026 — Trzeci fragment kroku 13: dobór parametrów Poissona na TRAIN (v0.3)

**Wdrożono kod rzeczywistej optymalizacji matematycznej, ale wykonano go dotąd WYŁĄCZNIE na sztucznym TRAIN.** [Moduł](../src/kb3_step13_poisson_train.py) wybiera parametry intensywności bramek gospodarzy i gości z analitycznego maksimum wiarygodności rozkładu Poissona; parametr wrażliwości bramek na różnicę Elo przeszukuje na stałej z góry zadanej siatce 0.0–0.6 ze skokiem 0.1. Minimalizuje całkowity **Poisson negative log-likelihood na TRAIN**, nie na VALIDATION/TEST. Nie optymalizuje jeszcze K=20 ani przewagi domowej ELO=65; te pozostają niezweryfikowanymi ustawieniami początkowymi.

**Źródło treningu:** wyłącznie rekordy syntetyczne z jawnym `source_type=SYNTHETIC_REFERENCE_ONLY`, ID `SYN-MATCH-*`, wynikami 90 minut, godziną kickoff, godziną wcześniejszego odcięcia cech, godziną rzeczywiście deklarowanego otrzymania wyniku i `partition=TRAIN`. Program zatrzymuje się, gdy wynik otrzymano po zamrożeniu folda, cutoff cech wypada po kickoff, etykieta jest błędna, pojawia się VALIDATION/TEST, kurs bukmacherski, dodatkowa kolumna, niezgodny lub zduplikowany identyfikator. Ze względu na sztuczne źródło testy **nie certyfikują niezależnie autentyczności momentu odczytu ELO**.

**Wykonany referencyjny przykład:** 12 wyłącznie ZMYŚLONYCH wyników TRAIN, optymalizator otrzymał `mu_home=2.0`, `mu_away=0.5`, `elo_goal_elasticity=0.0`; to parametry przykładowej, sztucznej próbki, NIE parametry KB Score 3.0 i NIE prognoza sportowa. Wartość treningowego NLL 27.462977349072986 jest wyłącznie matematycznym sprawdzianem optymalizatora, NIE historycznym log loss na 1X2. Twardy status `SYNTHETIC_FITTED_REFERENCE_ONLY_NOT_FOR_BETTING`. [Niepodmienialny raport referencyjny](../data/audits/STEP13_SYNTHETIC_POISSON_FIT_V03_2026-10-26.json), SHA256 `55c28c220c140c00be0b3272c87053e2be13a580d3c58740e8fd506c9e9d3523`.

**Testy i bramki:** [15 testów parametrów i anty-leakage](../tests/test_step13_poisson_train.py); [CI PASS](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40395088065). Generator sprawdza dodatkowo podpisaną wersję raportu rzeczywistej luki PIT ze Step12: nadal 1520 realnych ID, **0 rzeczywistych meczów dopuszczonych do fit**, historyczny Brier, log loss i kalibracja nadal NIEOBLICZONE. Nie wygenerowano rekomendacji, nie pobierano API, nie wykorzystano TEST.

**Warianty, które odblokują dalszą pracę:**
1. Formalnie zatwierdzone źródło historycznie dostępnych cech i wyników z wiarygodnym niezależnym `observed_at` — umożliwia pełny backtest PIT.
2. Osobno uzgodniony badawczy, wyraźnie opisany replay z wyników archiwalnych dostępnych obecnie, oparty wyłącznie na historycznej kolejności zdarzeń — może służyć do badań wstępnych, lecz **nie** daje dowodu historycznej wiedzy przed meczem i nie może automatycznie zaliczyć GATE13.

**GATE13 PENDING**: nadal brak rzeczywistych historycznych metryk. **Stan projektu 12/29; produkcyjne training_allowed=false**.

## 26.10.2026 — Kontynuacja ISTNIEJĄCEGO kroku 13: realny backtest badawczy offline (bez nowych etapów planu)

**Decyzja właściciela:** wykorzystać istniejące archiwum PitchAPI w odrębnym eksperymencie `RECONSTRUCTED_EVENT_TIME_RESEARCH_NOT_VERIFIED_PIT`, równolegle zachowując budowę przyszłych prawdziwych przedmeczowych obserwacji. Nie dodajemy osobnej pozycji do harmonogramu 29 kroków i nie zmieniamy zadań 14–29.

### Co jest wdrożone teraz
- [Algorytm badań historycznych](../src/kb3_step13_retrospective.py): cztery istniejące kwartalne walidacje 2025/26, EXPANDING i ROLLING 24 miesiące, Elo aktualizowane z poprzednich wyników tylko po **symulowanym konserwatywnym embargo 48 godzin**. Ten hipotetyczny czas jest wyłącznie założeniem badawczym; **nie jest** oryginalnym `source_observed_at`. MLE bazowych stawek bramkowych i z góry ustalona siatka elasticities wybierane na okresie TRAIN; na początku każdego kwartału oceny i parametry zostają zamrożone. Wynik meczów VAL może zostać użyty dopiero w przyszłym foldzie. Wynik i identyfikator TEST całkowicie zablokowane. Dla obu metod wspólne mecze i osobne porównywalne metryki multiclass logloss, Brier sum3 i 5-koszykowa kalibracja top-class. Wartość ECE prezentowana jako **średnia ważona ECE foldów**, nie globalnie przeliczona na połączonych prognozach.
- [Zaufany lokalny czytnik i uruchamiacz](../scripts/step13_pitch_retrospective_local.py): przyjmuje oryginalną zaszyfrowaną kopię Google Drive `KB3_PITCH_PL_2023_2026_NATIVE_20261026.zip`. Weryfikuje niezmienne SHA-256 ZIP `301bae69251d19a0192e12c2c033636b3f2822a15dcea2c4beaca28f4b45de2e`, szyfrogramu `e5e14a2320e65f945a2709c4cd8dfb49ed38d45ccca3502b3e5ba7c21f84d343`, łańcucha `33c750f2db89a0df5faeba9348652a451f33548959839ff7bb0ca49210c2b367` oraz prawdziwy moment źródłowej obserwacji `2026-10-26T13:17:47.692940Z`, niezależny `restore(...include_receipts=True)`, wszystkie 1140 autentyczne ID/ko z przypiętym, safe-only widokiem kroku 12. Wymaga kompletnych **760 TRAIN + 380 VALIDATION** i nie odczytuje żadnego TEST. Raport zawiera tylko zbiorcze liczby, parametry i metryki, nigdy nazw, wyników ani prywatnych kluczy.
- [Testy algorytmu](../tests/test_step13_retrospective.py) i [testy obsługi archiwum](../tests/test_step13_local_archive.py) obejmują anty-lookahead, równe ID porównania, odmowę TEST, kursów, złego źródła/ZIP, ponawialność i przypadki graniczne. GitHub Actions może uruchamiać **wyłącznie te testy na danych syntetycznych**, nigdy odszyfrować prawdziwego ZIP.

### Jak uruchomić lokalnie (z zachowaniem klucza prywatnego tylko u właściciela)

1. Na komputerze właściciela z Pythonem i repozytorium KB Score 3.0 zainstalować zależność: `python -m pip install 'cryptography>=42,<47'`.
2. Pobrać istniejące [zaszyfrowane archiwum PitchAPI](https://drive.google.com/file/d/1_wLVJtOSwjwQwHhjBa54-3f0-aCzhyqJ/view). Zachować oddzielnie oryginalny RSA private PEM — **nie przesyłać do czatu, GitHub Secrets ani Google Drive**.
3. Uruchomić z katalogu repozytorium (zamieniając lokalne ścieżki na rzeczywiste):

```bash
python -m scripts.step13_pitch_retrospective_local \
  --archive-zip /lokalna/sciezka/KB3_PITCH_PL_2023_2026_NATIVE_20261026.zip \
  --private-key /bezpieczna/lokalna/sciezka/recipient_private.pem \
  --research-policy RECONSTRUCTED_EVENT_TIME_RESEARCH_NOT_VERIFIED_PIT \
  --output /lokalna/sciezka/STEP13_RETROSPECTIVE_RESEARCH_RESULT.json
```

4. Dopuszczony wynik to **wyłącznie raport badawczy** zawierający jawne `historical_pit_backtest_performed=false`, `training_allowed=false`, `gate13_pass=false`, cztery foldy i walidacyjne metryki. Przy niespójności danych/programu/klucza powstaje błąd, nie zastępczy raport. **Nie udostępniać surowej bazy ani klucza**.
5. Prawidłowo wykonany raport będzie można przejrzeć, zweryfikować i następnie zdecydować, czy istnieją dostateczne podstawy do poprawiania algorytmu. Nie awansować do produkcji ani nie zaliczać pełnego kroku13 bez historycznej walidacji PIT/odrębnego odbioru.

**Stan po wdrożeniu:** implementacja offline i testy automatyczne gotowe, **rzeczywisty backtest na odszyfrowanym archiwum JESZCZE NIE URUCHOMIONY** (brak prywatnego klucza w środowisku połączonym z GitHub). Nie wygenerowano jeszcze rzeczywistych metryk. Zaplanowane 29 kroków pozostaje bez zmian, aktualnie **12/29 odebranych; krok13 W REALIZACJI; GATE13 PENDING.** Koszt API: 0 zł.

## 26.10.2026 — Weryfikacja AUTENTYCZNEGO zaszyfrowanego ZIP, wciąż w KROKU 13

Z pobranej ponownie [oryginalnej kopii na Google Drive](https://drive.google.com/file/d/1_wLVJtOSwjwQwHhjBa54-3f0-aCzhyqJ/view) wykonano lokalnie **rzeczywisty, niezależny sprawdzian bez klucza**. Plik ma **31 907 bajtów**, SHA256 `301bae69251d19a0192e12c2c033636b3f2822a15dcea2c4beaca28f4b45de2e`; zaszyfrowana zawartość ma **30 168 bajtów**, SHA256 `e5e14a2320e65f945a2709c4cd8dfb49ed38d45ccca3502b3e5ba7c21f84d343`. W ZIP obecny jest dokładny manifest źródłowy i zbiorcze podsumowanie 380+380+380 = **1140 historycznych rekordów deklarowanych przez źródło**, z oryginalnym czasem pobrania `2026-10-26T13:17:47.692940Z`. Łańcuch dowodowy `33c750f2db89a0df5faeba9348652a451f33548959839ff7bb0ca49210c2b367` jest zgodny z wcześniej przypiętym raportem.

[Weryfikator archiwum](../src/kb3_step13_archive_preflight.py) został dołączony do [lokalnego programu badawczego](../scripts/step13_pitch_retrospective_local.py), aby błędny, nieoryginalny lub podmieniony ZIP był automatycznie odrzucany przed próbą jego odszyfrowania. Raport z odczytu rzeczywistych zaszyfrowanych bajtów (nie surowych wyników) zamrożono w [STEP13_ORIGINAL_SEALED_ZIP_PREFLIGHT_2026-10-26.json](../data/audits/STEP13_ORIGINAL_SEALED_ZIP_PREFLIGHT_2026-10-26.json), SHA256 `aa810e1afa293f103b8f50cbb00f46fca4eff7beacdb425ade16d469b5170e48`. W osobnym środowisku lokalnym wykonano **9 kontroli technicznych**, w tym odrzucanie podstawień i uszkodzonych kopii; wszystkie zakończone powodzeniem.

**Bardzo ważne granice dowodu:** `archive_decrypted=false`, `archive_plaintext_integrity_verified_in_this_run=false`, `real_backtest_performed=false`, `real_backtest_metrics_available=false`, `training_allowed=false`, `gate13_pass=false`. Zawartości 1140 meczów nie odszyfrowano ani nie wykorzystano do treningu. Ostatnie GitHub Actions mają status FAILURE, ponieważ GitHub wysłał powiadomienie o wykorzystaniu **100% miesięcznych 2000 minut Actions**; najnowsze uruchomienie nie miało nawet dostępnych logów kroków zadania. **Nie określam tych uruchomień jako PASS.** Prawidłowe testy wykonano lokalnie na pliku ZIP i kopiach celowo zmodyfikowanych, bez nowych wywołań API.

**Następne bezpośrednie zadanie w tym samym kroku 13:** właściciel wykonuje lokalnie `scripts.step13_pitch_retrospective_local` z oryginalnym prywatnym kluczem RSA, bez udostępniania klucza komukolwiek; dopiero wtedy powstanie rzeczywisty raport badawczy 760 TRAIN / 380 VALIDATION. Dotychczasowy harmonogram nadal obejmuje **29 kroków**; zakończone **12/29**. Kroku14 nie rozpoczęto.

## 26.10.2026 — GitHub Actions działa ponownie: ponowiony audyt PR #34 na main

Po zmianie konfiguracji/limitu na koncie GitHub przez właściciela ponowiono **cztery dotychczasowe, zakończone wcześniej przez brak minut przebiegi** na niezmiennym merge commicie `72e08315f99fe0e763fcb367b686a6a6c317dba2` (PR #34). Wszystkie zakończyły się **SUCCESS** przy próbie nr 2:

- [Retrospective Research Contract, w tym kontrola rzeczywistego zamrożonego raportu szyfrogramu](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40402095894) — **PASS**, łącznie z testami offline anty-leakage, preflight i zabezpieczeniem bramki not-PIT.
- [Train-Only Poisson Fit Safety](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40402094465) — **PASS**.
- [ELO Poisson M0 Offline Math](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40402094411) — **PASS**.
- [Fold Replay Safety](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40402094393) — **PASS**.

To zastępuje starszą uwagę o nieuruchamialnym CI (prawdziwa przyczyna wcześniejszych automatycznych FAILURE: brak miesięcznych minut). **Nie** oznacza to, że 1140 prywatnych wyników historycznych zostało odszyfrowanych w CI, że wykonano realny backtest, ani że istnieją faktyczne przedmeczowe oceny modelu. Nadal konieczne lokalne odszyfrowanie oryginalnym prywatnym kluczem, a następnie badanie retrospektywne. **GATE13 PENDING, training_allowed=false, odbiór 12/29, krok14 nierozpoczęty, harmonogram 29 kroków bez zmian.**

## 27.10.2026 — przygotowanie uruchomienia na ASUS / Windows 10 (ciągle KROK 13, bez nowej pozycji)

**Stan techniczny:** użytkownik potwierdził przeniesienie prywatnego klucza RSA do laptopa ASUS. Nie podawano treści ani ścieżki klucza przez czat. ChatGPT ma dostęp do GitHub i zaszyfrowanego źródła, **nie** ma bezpośredniego dostępu do prywatnych plików Windows.

Dodano pomocniczy [launcher PowerShell 5.1 Windows 10](../scripts/step13_windows_local_start.ps1). Pomaga uruchomić istniejący, zweryfikowany runner `scripts.step13_pitch_retrospective_local`, bez zmian w modelu, foldach, limitach API i 29-krokowym harmonogramie.

### Instrukcja uruchomienia na laptopie

1. Na ASUS-ie otworzyć własne repozytorium [kb-score-3](https://github.com/karolbarankiewicz1984-ui/kb-score-3) w zalogowanej przeglądarce, pobrać aktualny **Code → Download ZIP** i rozpakować do dowolnego zwykłego folderu (bez klucza prywatnego!). Jeśli repo jest już sklonowane lokalnie, wystarczy zaktualizować `main`. Nie otwierać ZIP repo jako archiwum — potrzebna jest rozpakowana struktura folderów `src`, `scripts`, `data`.
2. Pobrać istniejący [oryginalny ZIP PitchAPI z Google Drive](https://drive.google.com/file/d/1_wLVJtOSwjwQwHhjBa54-3f0-aCzhyqJ/view) do `Pobrane`, bez rozpakowywania go. Oczekiwany SHA256: `301bae69251d19a0192e12c2c033636b3f2822a15dcea2c4beaca28f4b45de2e`.
3. Zapisać klucz PEM/KEY w `%LOCALAPPDATA%\KB3-Private` **poza** folderem repo i synchronizacją OneDrive; zachować kopię na telefonie. Nie wysyłać zawartości klucza do ChatGPT ani na GitHub.
4. Otworzyć rozpakowany folder repo w Eksploratorze, wpisać w pasku adresu `powershell` i nacisnąć Enter. W otwartym oknie uruchomić:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\step13_windows_local_start.ps1
```

To ustawienie ExecutionPolicy dotyczy **tylko uruchamianego procesu**, nie zmienia trwale polityki komputera. Skrypt pochodzi z repozytorium właściciela; należy zawsze otworzyć/obejrzeć plik przed uruchomieniem.
5. W dwóch oknach wybrać najpierw **oryginalny ZIP PitchAPI**, potem **swój prywatny klucz**. Skrypt sprawdzi pochodzenie ZIP, wykona testy offline, przygotuje oddzielne środowisko Python w folderze prywatnym; jeśli brakuje biblioteki `cryptography`, instaluje ją do tego środowiska z PyPI (jedyny sieciowy etap przygotowania). Gdy Python 3 nie jest zainstalowany, zatrzymuje się i pokazuje komunikat. Następnie lokalnie odszyfruje archiwum i wykona **retrospektywne badanie** przy ochronie TEST.
6. Wynik zbiorczy pojawi się w konsoli. Kopia JSON zostanie zapisana pod ścieżką `%LOCALAPPDATA%\KB3-Private\STEP13_RETROSPECTIVE_RESEARCH_RESULT.json`, NIE w repozytorium. Do rozmowy wystarczą tylko zagregowane metryki EXPANDING i ROLLING oraz status; **nigdy nie przesyłać prywatnego klucza**, nie przesyłać zaszyfrowanej ani odszyfrowanej bazy.

Runner poprawnie odrzuca nieoryginalny ZIP, nieprawidłowy nagłówek klucza, lokalizację klucza wewnątrz repo/OneDrive, brak Pythona, błędy integralności czy niespójne 760/380/0. Przy kluczu chronionym hasłem przerywa wykonanie; nie prosi o hasło. Weryfikację składni PowerShell i brak sieciowej transmisji klucza dodano do **istniejącego** workflow Step13. Program nie wykonuje zakładów ani realnego zatwierdzenia GATE13.

**Nawet po udanym wykonaniu:** oznaczenie `RECONSTRUCTED_EVENT_TIME_RESEARCH_NOT_VERIFIED_PIT`, `training_allowed=false`, `gate13_pass=false`; wyniki logloss/Brier z retrospekcji nie są niezależnym dowodem autentycznych dawnych prognoz. Rzeczywistego uruchomienia na laptopie przez ChatGPT nie można potwierdzić przed otrzymaniem jego raportu. **KROK13 W REALIZACJI; 12/29; KROK14 nierozpoczęty.**
