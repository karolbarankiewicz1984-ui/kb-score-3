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

## 27.10.2026 — PIERWSZE prawdziwe retrospektywne metryki ELO+Poisson: PitchAPI (KROK 13 bez nowych etapów)

**Istotna zmiana:** Nie trzeba już ręcznego używania prywatnego RSA na laptopie do tego *retrospektywnego* badania. Skorzystano wyłącznie z istniejącego GitHub Actions i darmowego PitchAPI. [Uruchomienie #40422326740 PASS](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40422326740). Źródło pobrano ponownie `2026-10-26T23:49:21.170204Z` (czyli 27 października w Polsce). **Dokładnie 3 odczyty PitchAPI**: 2023/24, 2024/25, 2025/26; **0 kosztów nowego API, 0 wywołań API-Football**. Brak użycia klucza RSA, odds, danych meczowych TEST. Sprawdzono natywne match ID, kickoff i dokładnie trzy 380-meczowe sezony wobec wcześniej zamrożonego widoku Step12. Brak automatycznej podmiany meczów przy niezgodnościach. 9+10 testów offline PASS.

**Autentyczne wyniki sportowe wykorzystano**, ale są pobrane retrospektywnie w październiku 2026, NIE zapisane przed każdym spotkaniem 2023–2026. Przeprowadzony eksperyment wykorzystuje hipotetyczne opóźnienie otrzymania wyniku 48h po starcie i zamrożenie wszystkich prognoz na początku kwartału. Jest to uczciwy `RECONSTRUCTED_EVENT_TIME_RESEARCH_NOT_VERIFIED_PIT`, **nie wiarygodny historyczny backtest PIT ani forward test**. Nie uprawnia do produkcyjnego treningu, typów bukmacherskich ani zaliczenia GATE13.

### METRYKI — wszystkie 380 prawdziwych wyników VALIDATION (tylko zbiorczo)

| Metryka (im mniej, tym lepiej) | EXPANDING | ROLLING 24 miesięcy |
|---|---:|---:|
| 1X2 multiclass log loss, średnia ważona z 4 foldów | **1.0326367404** | 1.0343803886 |
| 1X2 multiclass Brier sum3, średnia ważona | **0.6185368951** | 0.6196881659 |
| Top-class ECE 5 koszyków, **średnia ważona ECE foldów, nie globalne ECE** | 0.0739533904 | **0.0733160087** |

### Szczegóły czterech zamrożonych kwartalnych walidacji

| Fold od UTC | VALIDATION n | TRAIN expanding | TRAIN rolling | Log loss EXP / ROLL | Brier EXP / ROLL |
|---|---:|---:|---:|---|---|
| 2025-07-01 | 60 | 760 | 760 | 1.028276 / 1.028276 | 0.612716 / 0.612716 |
| 2025-10-01 | 126 | 819 | 752 | 0.965705 / 0.968677 | 0.571618 / 0.573771 |
| 2026-01-01 | 123 | 940 | 744 | 1.108473 / 1.105917 | 0.674458 / 0.672175 |
| 2026-04-01 | 71 | 1069 | 776 | 1.023723 / 1.032210 | 0.609843 / 0.616140 |

**Interpretacja:** EXPANDING ma minimalną przewagę w agregacie log loss (+0.00174 na korzyść EXPANDING) i Brier (+0.00115 na korzyść EXPANDING). W foldzie 1 jest remis, w 2 i 4 EXPANDING wypada lepiej, w 3 ROLLING lepiej. Różnica nie jest rozstrzygająca, **nie ogłaszamy czempiona**. Fold 3 jest najsłabszy w obu metodach. W 8/8 zestawów parametr elastyczności ELO osiąga górny brzeg obecnej siatki `0.6` — sygnał do weryfikacji ustalonego zakresu, a nie do dopisywania nowego kroku. Parametry ELO K=20, home=65 nie były optymalizowane.

**Trwałe dowody:** [pełny zbiorczy JSON](../data/audits/STEP13_REAL_RETROSPECTIVE_PITCHAPI_2026-10-27.json), podpis kontrolny `3d950fff30b57c94a6f71462c7521cfda2cb0b27c666d59d09d274261efca803`, [źródłowa akcja z datą i testami](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40422326740), [niezależny transfer tego samego pliku bez pobierania danych z API](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40422560884). **Brak surowych wyników/meczów w GitHub, tylko zbiorcze metryki i hashe.** Dane TEST (380) nietknięte.

**Status:** to istotne wypełnienie części historyczno-badawczej kroku 13, ale nie certyfikacja PIT. Formalnie **KROK13 W REALIZACJI; GATE13 PENDING; training_allowed=false; 12/29**. Nie rozpoczynamy kroku14 ani nie modyfikujemy harmonogramu. Dalsza kontrola w obrębie kroku13: ewaluacja stabilności i przyszły forward-PIT bez przecieków.

## 27.10.2026 — Audyt stabilności REALNEJ walidacji kroku 13 (nie nowy etap)

W obrębie **tego samego kroku 13 / ELO+Poisson** wykonano i utrwalono dodatkową analizę **WYŁĄCZNIE NA ORYGINALNYM ZBIORCZYM RAPORCIE** [realnego retrospektywnego badania 380 meczów](../data/audits/STEP13_REAL_RETROSPECTIVE_PITCHAPI_2026-10-27.json). Nie odczytano nowych rekordów, nie wykonywano żadnego wywołania PitchAPI, nie użyto TEST, kursów, klucza RSA ani nowych modeli. Weryfikowalny [kod analizy](../src/kb3_step13_stability_audit.py) kontroluje podpis SHA256 oryginalnego raportu, niezmienność zbioru spotkań walidacyjnych, kompletność 4 foldów oraz przelicza z koszyków sumaryczną trafność najczęściej prognozowanej klasy 1X2, przeciętną pewność i ECE. Wynik ma własny SHA256 `10e75ea0a247ca3d446379238ac4f97aab6be90f8ee55aac6796cf7d83bdeb8e` i [niezmienny raport](../data/audits/STEP13_REAL_RETROSPECTIVE_STABILITY_2026-10-27.json).

### Trafność najczęściej wskazanej klasy 1X2 a deklarowana pewność (nie skuteczność kuponów)

| Kwartał | n | EXPANDING: liczba trafień / trafność / średnia deklarowana P | ROLLING: liczba trafień / trafność / średnia deklarowana P |
|---|---:|---|---|
| 2025 VII–IX | 60 | 31; 51.7%; 47.4% | 31; 51.7%; 47.4% |
| 2025 X–XII | 126 | 72; 57.1%; 48.0% | 72; 57.1%; 47.7% |
| 2026 I–III | 123 | 48; **39.0%**; **49.7%** | 48; **39.0%**; **48.8%** |
| 2026 IV–VI | 71 | 34; 47.9%; 47.7% | 33; 46.5%; 46.5% |
| 380 łącznie | 380 | 185; **48.68%**; 48.42% | 184; **48.42%**; 47.77% |

**Kluczowy rezultat:** w kwartale **I–III 2026** EXPANDING był zbyt pewny o **10.70 punktu procentowego**, ROLLING o **9.73 p.p.**, a log loss tego kwartału był najsłabszy w obu wariantach. Rozbieżności między kwartałami mają przeciwne znaki. Gdy błędy kwartałów połączą się, **pooled ECE** 5-bin (EXPANDING **0.01693**, ROLLING **0.01033**) daje zbyt uspokajające wrażenie; uzgodniona miara kontrolna **średnia ważona z ECE kwartalnych** jest wyższa: EXPANDING **0.07395**, ROLLING **0.07332**. Nie wolno zastępować drugiej pierwszą w raporcie odbiorowym. Samo ECE nie jest miarą trafności kuponu.

Zgodnie z wcześniej zamrożonymi wynikami EXPANDING minimalnie wygrywa log loss o 0.00174365 i Brier o 0.00115127; różnicy **nie oznaczamy jako statystycznie istotnej** (brak danych per-mecz do sparowanych przedziałów ufności). W **8/8** dopasowań `elo_goal_elasticity=0.6` osiąga maksymalny punkt ustalonej z góry siatki — sygnał **kontroli na TRAIN**, a NIE przyzwolenie na strojenie modelu z użyciem walidacji. W tym przeglądzie **nie zmieniano parametrów, siatki, wyników ani algorytmu** i **nie wybrano wersji produkcyjnej**.

**Zabezpieczenia:** [testy](../tests/test_step13_stability_audit.py) odrzucają podmieniony podpis raportu, niezgodność miar lub naruszenie danych walidacyjnych. [GitHub Actions — komplet testów i generator raportu](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40423988185) **SUCCESS**, wygenerowany raport zapisany na gałęzi audytowej, bez zapytań sieciowych do dostawców sportowych.

**Stan:** kroki 1–12 pozostają odebrane, **krok 13 nadal w realizacji**, GATE13 **PENDING**, training_allowed=false, historyczny PIT **nieudowodniony**, TEST **nieczytany**, harmonogram **29 pozycji bez zmian**, krok14 CatBoost **nie rozpoczęty**. W ramach tego kroku pozostaje przygotowanie przyszłego rzeczywistego testu forward/PIT i ustalona z góry diagnostyka wpływu Elo wyłącznie na TRAIN — nie automatyczna korekta na podstawie walidacji.

## 27.10.2026 — Diagnostyka tylko TRAIN: elastyczność ELO (wciąż krok 13)

Przeprowadzono jednorazowy eksperyment na **760 rzeczywistych wynikach TRAIN z sezonów 2023/24 i 2024/25**, zgodnych z przypiętym podziałem Step12. Źródło: 2 darmowe odczyty PitchAPI; wyniki pobrano retrospektywnie 2026-10-27 00:16:49 UTC. Nie odczytano VALIDATION ani TEST. Obliczono profilowe MLE średnich bramek Poissona na oryginalnej siatce 0.0–0.6 i oddzielnej siatce **diagnostycznej tylko na TRAIN** 0.0–1.2 co 0.1. Cel to dwubramkowy Poisson NLL na TRAIN, **nie log loss prognoz 1X2 na walidacji**.

| Próbka TRAIN | liczba | Najlepsza elastyczność na siatce diagnostycznej | Średni NLL |
|---|---:|---:|---:|
| sezon 2023/24 | 380 | 1.2 — górna krawędź | 3.112423 |
| sezon 2024/25 | 380 | 0.9 | 2.974701 |
| oba sezony | 760 | 1.0 | 3.055322 |
| oba sezony — stara siatka | 760 | 0.6 — górna krawędź | 3.071748 |

Na całym TRAIN cel bramkowy poprawił się względem starej granicy o 12.483966 NLL sumarycznie. Zmienne optimum pomiędzy sezonami nie gwarantuje generalizacji. **Nie zmieniono parametrów istniejącego M0 ani walidacji; nie wybrano zwycięzcy do produkcji.**

Źródła: [kod](../src/kb3_step13_train_elo_sensitivity.py), [testy](../tests/test_step13_train_elo_sensitivity.py), [agregat](../data/audits/STEP13_TRAIN_760_ELO_ELASTICITY_DIAGNOSTIC_2026-10-27.json), SHA256 `abaeaa142a6ab75301e964973724ce6f20cbf3efe137bd0b6c38e78a3412e846`, [GitHub Actions SUCCESS](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40425365353). Pierwszy bieg odrzucono na poziomie sztucznego testu granicznego przed wywołaniem API; poprawiono tylko dane testowe, nie zasady bezpieczeństwa.

**Formalnie 12/29 ukończonych; krok13 w toku, GATE13 PENDING, training_allowed=false, krok14 nierozpoczęty.** Nie zmieniamy harmonogramu 29 kroków.

## 27.10.2026 — rzeczywista sparowana niepewność EXPANDING vs ROLLING: brak wiarygodnego zwycięzcy (KROK13)

W ramach niezmienionego **kroku 13** wykonano [jednorazowe rzeczywiste porównanie sparowanych błędów 380 meczów walidacyjnych](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40457581450) — **SUCCESS**. Wykorzystano 3 sezony historyczne PitchAPI pobrane ponownie za pomocą istniejącego bezpłatnego źródła, **tylko TRAIN 760 + VALIDATION 380**, z **TEST 0**, bez kursów, XG i eksportu wyników pojedynczych meczów. Każdy zestaw prognoz został wyliczony zgodnie z zamrożonymi parametrami na początku folda oraz dopasowaniem Poissona wyłącznie z przeszłości. Przed obliczeniem niepewności rygorystycznie porównano każdy fold — średnie logloss/Brier, fitting, trening i SHA ID celów — z podpisanym [pierwotnym raportem prawdziwej retrospekcji](../data/audits/STEP13_REAL_RETROSPECTIVE_PITCHAPI_2026-10-27.json). Przy rozbieżności program kończy działanie bez raportu. **Nie stroimy parametrów pod walidację**.

Wykonano **3000 deterministycznych losowań bootstrapowych** na tych samych meczach, grupowanych według tygodnia kalendarzowego *wewnątrz każdego z czterech kwartalnych foldów* (38 klastrów). Opisywane granice to **orientacyjny interwał bootstrapowy**, a nie formalny dowód niezależności meczów ani PIT. Dodatnia różnica ROLLING−EXPANDING sprzyja EXPANDING, ujemna sprzyja ROLLING.

| Miara | ROLLING minus EXPANDING | Bootstrap 95% (klastry tygodni) | 0 w interwale? |
|---|---:|---|---|
| Multiclass log loss 1X2 | **+0.0017436482** | **[−0.0003789226, +0.0038354903]** | TAK |
| Multiclass Brier sum3 | **+0.0011512708** | **[−0.0004956491, +0.0027241987]** | TAK |

Według kwartałów delta logloss: lip–wrz 2025 **0.000000**, paź–gru 2025 **+0.002972**, sty–mar 2026 **−0.002556**, kwi–cze 2026 **+0.008486**. Wniosek: nawet obserwowana minimalna przewaga EXPANDING **nie jest odporna na niepewność doboru próby**, nie wyznaczamy zwycięzcy ani nie włączamy modelu produkcyjnie. Słabszy trzeci kwartał pozostaje znanym ryzykiem, nie jest efektem tego dodatkowego testu.

**Dowód:** [zamrożony raport wyłącznie agregatowy](../data/audits/STEP13_REAL_PAIRED_UNCERTAINTY_2026-10-27.json), SHA256 `e1a1694da3b43f944696b456521448015b855f47da8d91d181ee5d547a9d47d4`; [kod](../scripts/step13_paired_uncertainty_once.py); [testy blokady zmiany wyniku/raportu/TEST](../tests/test_step13_paired_uncertainty.py). Pierwszy syntetyczny CI odrzucił niepodpisany testowy raport zanim wysłano żądania do API, następnie naprawiono podpis sztucznego fixture i powtórzono. [Właściwy przebieg #40457581450 PASS](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40457581450), brak wycieku surowych meczów do artefaktów. **Żadne dane z 2026/27 TEST nie zostały odczytane**.

**Granice:** To nadal badanie `RECONSTRUCTED_EVENT_TIME_RESEARCH_NOT_VERIFIED_PIT`, a nie oryginalne źródłowe obserwacje sprzed dawnych spotkań. Bootstrap nie dowodzi istotności ani przewagi; rzeczywisty prospective PIT wymaga nowo zarejestrowanych przedmeczowych prognoz i uczciwego późniejszego porównania. KROK13 W REALIZACJI, GATE13 PENDING, `training_allowed=false`, ukończono **12/29**, krok14 nie rozpoczęty.

## 27.10.2026 — PIERWSZY RZECZYWISTY PROSPECTIVE PREMATCH SHADOW SNAPSHOT (oryginalny KROK 13)

Wykonano **rzeczywisty zapis prognoz przed rozpoczęciem przyszłych spotkań**, czego brakowało we wcześniejszych, tylko retrospektywnych badaniach. [GitHub Actions — one-shot 27.10.2026](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40459673538) **SUCCESS**, zamrożony plik [`STEP13_FIRST_PROSPECTIVE_PREMATCH_2026-10-27.json`](../data/forecasts/STEP13_FIRST_PROSPECTIVE_PREMATCH_2026-10-27.json) o podpisie SHA256 `9c346f79b1868fd1cb0d4d4ffa066f6f1629e09bbc6ce0454c5c8901e7645389`.

- **Prawdziwy zegar źródła:** `2026-10-27T06:12:08.686916Z`; **prawdziwy zegar zamrożenia prognoz po obliczeniach:** `2026-10-27T06:12:08.707287Z`. Daty kickoff wszystkich 10 wybranych spotkań to **31.10–02.11.2026**, co daje rzeczywiste prognozy przed spotkaniami. Dodatkowe opóźnienie minimum 48 h i bezwzględne sprawdzanie rozpoczęcia meczu oraz terminu. Historia rzeczywiście była obserwowana przed tymi datami, lecz oryginalna data publikacji przez dostawcę jest nieznana.
- **Dostawca:** tylko dotychczasowy PitchAPI, **3 zapytania**, bez nowych zakupów. Przeanalizowano 2 pełne sezony `2023/24` + `2024/25` po 380 meczów, łącznie dokładnie zamrożone `TRAIN 760`. Każde natywne ID/kickoff skontrolowano z krokiem12. Parametry dopasowania do tego TRAIN *identyczne* jak w oryginalnym, zamrożonym pierwszym foldzie: `base_home_goals=1.63733387301664`, `base_away_goals=1.4370968890275349`, `elo_goal_elasticity=0.6`; pozostałe Elo: 1500, K=20, scale 400, home advantage 65. **Nie wybierano zwycięzcy na walidacji i nie rozszerzano siatki treningowej.**
- **Ochrona danych:** 2025/26 `VALIDATION` wyników nie pobierano; z `TEST 2026/27` użyto *WYŁĄCZNIE* listy przyszłych spotkań `status=upcoming` z `score_home=None`, `score_away=None`. Wyniki TEST odczytane: **0**; brak przeszłych meczów TEST w składzie cech, brak odds, xG, API-Football. Przeciwko zamrożonemu terminarzowi 1520 ID odrzucono każdy konflikt match_id/kickoff. Program odmówi przy próbie odczytu wyniku, spóźnionym zamrożeniu lub niezgodnym TRAIN.
- **10 przyszłych spotkań:** Chelsea–Manchester United; Coventry City–Sunderland; AFC Bournemouth–Leeds United; Hull City–Ipswich Town; Brentford–Nottingham Forest; Manchester City–Brighton; Tottenham–Crystal Palace; Aston Villa–Fulham; Liverpool–Arsenal; Newcastle United–Everton. Pierwsze spotkanie 31 października 12:30 UTC, ostatnie 2 listopada 20:00 UTC. Dla Chelsea–Manchester United `P(1)=0.5626901969`, `P(X)=0.2156828298`, `P(2)=0.2216269733`, suma 1. Każdy z 10 zapisów posiada bazowe `ELO`, `xG` modelu (oczekiwane gole Poissona, **nie dane xG z API**), trzy prawdopodobieństwa 1X2, rozpoczęcie spotkania, chwilę odbioru źródła i zamrożenia oraz hash całego raportu.
- **Ważne ograniczenie jakości:** ratingi Elo zostały wyprowadzone **wyłącznie z historii 760 TRAIN zakończonej w czerwcu 2025** i NIE uwzględniają sezonu 2025/26 ani dotychczas rozegranych meczów 2026/27, celowo, aby nie dotknąć walidacji ani wyników TEST. Nowo awansowane drużyny zaczynają z Elo 1500. Model może przez to mieć słabą jakość. To kontrolowany **baseline shadow**, nie sposób do typowania bukmacherskiego.
- **Nie czytano jeszcze żadnego wyniku tych 10 meczów**, bo są w przyszłości. Nie powstały żadne uczciwe miary Brier, log loss ani ECE z tej nowej próby — będą możliwe dopiero PO meczach, po sprawdzeniu nienaruszalności zamrożonego raportu i zgodności późniejszego źródła. **Bez ponownego trenowania lub modyfikowania prognoz po wyniku.**
- Pierwszy przebieg workflow zatrzymał się na **sztucznym** teście stałości nazw drużyn, jeszcze przed wywołaniem PitchAPI. Po poprawieniu jedynie sztucznych testowych nazw nastąpił SUCCESS; nie osłabiono żadnej blokady. [Kod źródłowy](../scripts/step13_prematch_forward_once.py), [negatywne i pozytywne testy](../tests/test_step13_prematch_forward.py).

Ostateczny odbiór kroku13 nie został udzielony: **GATE13 PENDING**, `training_allowed=false`, `step14_started=false`, nadal **12/29**, brak nowej pozycji harmonogramu. Prospective snapshot faktycznie zamrożony przed kickoff, ale wyniki sportowe i ocena prognoz PENDING, brak zatwierdzonego modelu produkcyjnego. 

## 27.10.2026 — przed pierwszym meczem zamrożono PROTOKÓŁ przyszłego rozliczenia 10 prognoz (nadal krok13)

W ramach niezmienionego kroku13 przygotowano **czysty, niezależny matematycznie scorer** [`src/kb3_step13_forward_score.py`](../src/kb3_step13_forward_score.py) oraz [niezmienny kontrakt oceny](STEP_13_FORWARD_SCORING_CONTRACT.md) dla dokładnie 10 prognoz, zapisanych faktycznie PRZED meczami 31.10–02.11.2026.

- Oryginalne prognozy: [`STEP13_FIRST_PROSPECTIVE_PREMATCH_2026-10-27.json`](../data/forecasts/STEP13_FIRST_PROSPECTIVE_PREMATCH_2026-10-27.json), **SHA256 `9c346f79b1868fd1cb0d4d4ffa066f6f1629e09bbc6ce0454c5c8901e7645389`** jest przypięty w kodzie. Scorer **odmawia** uruchomienia przy modyfikacji choćby jednej wartości lub nieprawidłowym czasie zamrożenia przed kickoff.
- Wolno oceniać **wyłącznie 10 z góry wskazanych native match_id**. Są to 10 rekordów w oryginalnym holdoucie 380 TEST, więc po faktycznym odczycie ich etykiet te 10 będą już **ujawnioną próbą badawczą** i nie wolno wykorzystywać ich do późniejszego strojenia; pozostałych 370 nie odczytujemy ani nie udostępniamy. Dzisiaj **0 wyników TEST odczytanych** przez scorer, ponieważ testy korzystają wyłącznie ze sztucznych etykiet.
- Główne predeklarowane miary: 1X2 top1 (liczba i trafność), multiclass **log loss**, multiclass **Brier sum3**, 5-bin ECE top1 (tylko opisowo dla n=10); dodatkowo Poisson sum home+away NLL i MAE goli na drużynę. Żadna z tych metryk nie służy do automatycznego wyboru EXPANDING/ROLLING ani parametrów.
- Każdy wynik musi być `finished`, odpowiadać 1:1 ID drużyn i kickoff zamrożonego celu oraz posiadać autentycznie późniejszą datę obserwacji. **Najwcześniej po 02.11.2026 23:00 UTC** (3 godziny po kickoff ostatniego meczu); bezpieczniej po potwierdzeniu zakończenia wszystkich 10 spotkań 3 listopada. Opóźniony mecz, brak wyniku albo wynik zbyt wcześnie => nie częściowy raport, tylko FAIL. Sam czas/digest przekazany funkcji matematycznej **nie dowodzi jeszcze integralności źródła**; do faktycznej oceny trzeba wykonać później osobną udokumentowaną obserwację PitchAPI z receipt/ledger.
- Program nie wywołuje API, nie czyta danych TEST, nie uruchamia się cyklicznie. Ma [unit testy na syntetycznych wynikach](../tests/test_step13_forward_score.py) i jest kontrolowany przez istniejący workflow Step13. Brak nowego harmonogramu, zakupów API, promocji modelu i zmian w zamrożonych prognozach.

**Formalnie** `training_allowed=false`, `gate13_pass=false`, `step14_started=false`, nadal **12/29**, krok13 W REALIZACJI. Nie wolno obecnie podawać wyników 10 meczów, Brier/log loss z forward ani uważać kontraktu za wykonane rozliczenie.
