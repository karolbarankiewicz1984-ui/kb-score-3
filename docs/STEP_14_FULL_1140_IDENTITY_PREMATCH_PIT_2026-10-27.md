# KB Score 3.0 — Krok 14: pełny zakres 1140 ID, 1140 niezależnych terminarzy i 159 dowodów PIT (27.10.2026)

**Formalny status:** 13/29; krok 14 W REALIZACJI; **GATE14 PENDING**. Żadne historyczne statystyki bez wiarygodnego `as-of` sprzed meczu nie zostały dopuszczone do rzeczywistego CatBoost M1.

## 1. Co rzeczywiście zweryfikowano teraz, niezależnie i bez prywatnego RSA

[GitHub Actions #40543896275 — SUCCESS](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40543896275) przeprowadził realny audyt podpisanych indeksów: 760 TRAIN (2023/24 i 2024/25) oraz 380 VALIDATION (2025/26). Wszystkie **1140/1140** rekordów oryginalnego niezmiennego manifestu Step12 mają **brak `feature_cutoff_utc` i kompletnego źródłowego pre-match receipt**; żadnej statystyki na ich podstawie nie wolno certyfikować jako rzeczywiście dostępnej przed kickoff. Wyniki: **0/760** dopuszczonych TRAIN, **0/380** dopuszczonych VALIDATION. Nie jest to twierdzenie, że rzeczywistych przedmeczowych statystyk nie było nigdzie; jest to dokładnie twierdzenie, że **nie ma ich autentycznych timestampowanych dowodów w posiadanym źródle**.

Odseparowana [kopia wyników audytu PIT](../data/audits/STEP14_FULL_1140_PIT_GAP_2026-10-27.json) z hashem `dc6a5743ce7e0ee6f638983bd46295dff245993286b1515f46210cf8b73b0137` nie ujawnia żadnego wyniku meczu, etykiety, bukmachera, oryginalnego `t_...`, RSA ani danych TEST.

## 2. Pełny rejestr 1140 historycznych terminarzy — oddzielne źródło identyfikacji

Pobrano **realne**, publiczne dane z [OpenFootball](https://github.com/openfootball/football.json) dla Premier League 2023/24, 2024/25 i 2025/26, **380 + 380 + 380 rekordów**. Z każdego pliku przekazano do [frozen target-free referencji](../data/research/STEP14_OPENFOOTBALL_1140_TARGETFREE_2026-10-27.json) **wyłącznie datę, godzinę Europe/London, gospodarza i gościa**. Wyniki, score, etykiety, kursy i xG nie zostały przepisane. Zamrożony hash referencji: `fa924730da71e3ba24e89a3095f7d4d92de5e71dd252b893bd86cc2e4db53678`.

Wszystkie surowe publiczne źródła mają osobne SHA256:
- 2023/24: `03e13eafbf78dfe00d7e89dd3bf6643986eb6e8fd86c7664aeb8c5bc0bed88d0`
- 2024/25: `c3d18f552d83382cd4b6b21127adbbfe38e7f8618ddc979fb5404f2df07d0a75`
- 2025/26: `d6070bdf731546ccf97767f062e8af4bd26dd309dee69f6092025bf9c78f43c1`

**Ważne:** realna godzina pobrania tego zbioru to **2026-10-27**, a nie godzina z lat 2023–2026. Źródło służy tylko jako NIEZALEŻNA historyczna referencja dla identyfikacji meczu; nie certyfikuje kiedy przed meczem było dostępne ani danych Elo/xG/formy.

## 3. Rozbudowany prywatny weryfikator tożsamości na komputer właściciela

Powstał [`src/kb3_step14_full_identity_pit_audit.py`](../src/kb3_step14_full_identity_pit_audit.py) oraz [runner lokalny](../scripts/step14_full_native_identity_pit_local.py). Ten sam oryginalny ZIP zabezpieczony SHA256 `301bae69251d19a0192e12c2c033636b3f2822a15dcea2c4beaca28f4b45de2e` i ten sam lokalny, nieprzesyłany RSA PEM pozwolą w jednym przebiegu:

1. Odtworzyć oryginalne trzy podpisane listy PitchAPI z 1140 historycznych fixture IDs, weryfikując chain SHA, komplet 380 spotkań i 20 drużyn w każdym sezonie.
2. Dla **każdego z 1140** porównać oryginalne `fixture_id`, dokładny UTC i TRAIN/VALIDATION z przypiętym `STEP12_SAFE_MODEL_VIEW`; sprawdzić dwie natywne pary `home_team.id/away_team.id` oraz stałość nazw team ID i niemożność dwóch identycznych meczów.
3. Sprawdzić niezależnie parę gospodarza i gościa z **pełnym nowym publicznym terminarzem 1140**; rozdzielić statusy `EXACT_PUBLIC_TEAM_PAIR_AND_UTC_KICKOFF`, `SAME_PUBLIC_TEAM_PAIR_DIFFERENT_UTC_KICKOFF`, `NO_EXACT_PUBLIC_TEAM_PAIR_SAME_SEASON`, `PUBLIC_KICKOFF_TIME_UNAVAILABLE`. Nigdy nie dopasowywać meczu **samą godziną**.
4. Sprawdzić kandydatów w **60 historycznych wersjach publicznych materiałów** z osobnego audytu 25 blobów, rozdzielając `PUBLIC_SERVER_PUSH`, `GIT_COMMIT_DATE_ONLY`, `NO_MATCH` i zidentyfikowane wrześniowe `Bournemouth–Newcastle` po przesunięciu terminu. Starego snapshotu `Sunderland–Aston Villa` nie wolno przepisać jako inny mecz.
5. Zsumować **obowiązkowe 159 dowodów na rekord** w oryginalnym kontrakcie Step11: 121 cech i 38 masek missing; weryfikować czy istnieje *faktyczny dowód* wcześniejszej publikacji/odczytu każdej kategorii. Oryginalny historyczny source PitchAPI pobrano **dopiero w październiku 2026**, dlatego nie dostarcza on dowodu PIT dla meczów 2023–2026.
6. Wygenerować jeden nowy **prywatny JSON wyłącznie z agregatami**, bez jakiegokolwiek `fixture_id`, `t_...`, `score_home`, etykiety, kursów lub klucza. Ten JSON nie trafia do repozytorium.

**UWAGA:** autentyczny wynik lokalnej kontroli 1140 natywnych par nie był jeszcze uruchomiony w tej sesji, ponieważ klucz pozostaje wyłącznie u właściciela. GitHub przetestował kod na wyłącznie **sztucznych** 1140 przykładach; nie należy nazywać tego prawdziwym lokalnym PASS 1140/1140. Pierwsze realne cztery pary zostały wcześniej potwierdzone 4/4 przez właściciela osobno.

## 4. Co wiemy o historycznej dostępności poszczególnych statystyk?

| Kategoria | Cechy Step11 | Missing flags | Historyczny dowód `as-of` w oryginalnym PitchAPI ZIP z 26.10.2026 | Konsekwencja |
| --- | ---: | ---: | --- | --- |
| Elo + Elo rywala | 17 | 0 | BRAK dla 1140 historii | Nie dopuszczać historycznego TRAIN |
| Wyniki / forma / średnie gole poprzednich meczów | 36 | 12 | BRAK historycznych pre-match receipts dla 1140 | Wsteczne obliczenie to tylko badania |
| xG i xGA | 48 | 24 | BRAK historycznych pre-match receipts dla 1140 | Brak certyfikatu; nie stosować 0 zamiast braku |
| Historia, liczba spotkań, kompletność, czas odpoczynku | 20 | 2 | BRAK historycznych pre-match receipts dla 1140 | Nie dopuszczać jako pełnych certyfikowanych cech |
| **Razem** | **121** | **38** | **0/760 TRAIN, 0/380 VALIDATION z kompletem PIT** | **GATE14 PENDING** |

Prawidłowości **historycznie policzalne z zakończonych wyników** (chronologiczny Elo, wcześniejsze wyniki, forma) należy odróżnić od **rzeczywiście zapisanych przed meczem** wartości. Matematycznie opóźniony wynik nie dowodzi, że PitchAPI opublikowało go przed konkretnym cutoff. Historyczna zawartość terminarza z GH Archive może dowodzić niektórych dat/zespołów przed meczem, lecz nigdy nie certyfikuje automatycznie całego wektora cech.

## 5. Uruchomienie na Twoim Windows — bez instalacji dodatkowych programów

Ponownie pobierz aktualny [ZIP z GitHub](https://github.com/karolbarankiewicz1984-ui/kb-score-3) **po scaleniu tej zmiany**, rozpakuj do nowego folderu, otwórz jego katalog w PowerShell i uruchom **dokładnie jedno polecenie**, korzystając z tego samego oryginalnego ZIP i PEM co w pomyślnym sprawdzeniu 4/4:

```powershell
py -3 -m scripts.step14_full_native_identity_pit_local --archive-zip "$HOME\Downloads\KB3_PITCH_PL_2023_2026_NATIVE_20261026.zip" --private-key "$HOME\Desktop\KB3_760_PAKIET_ODZYSKIWANIA_POUFNE\KB3_760_KLUCZ_ODZYSKIWANIA.pem" --output "$HOME\Desktop\KB3_STEP14_1140_PIT_IDENTITY_AGGREGATE_PRIVATE.json"
```

W przypadku pozytywnego wykonania zobaczysz liczby `CHECKED 1140 TRAIN 760 VALIDATION 380 PUBLIC_SAMPLE 60 PUBLIC_FULL 1140 PUBLIC_EXACT N FIELD_PROOFS_REQUIRED 159 PIT_TRAIN_CERTIFIED 0 GATE14 PENDING`. `PUBLIC_EXACT N` będzie faktycznym odsetkiem meczów o zgodnych obu nazwach i identycznej godzinie w niezależnym źródle; **nie przewidujemy N z góry**. Jeżeli źródłowe dane okażą się niespójne, program zakończy kontrolę błędem zamiast przedstawiać zmyślony wynik. Raport tworzony jest tylko raz, poza folderem repozytorium, bez nadpisywania i bez sekretów.

**Nie należy przesyłać prywatnego RSA PEM, pełnego odszyfrowanego pliku meczów ani dwóch natywnych ID do czatu ani na GitHub.** Wystarczy ekran z agregatami albo bezpieczny JSON agregatów, jeżeli właściciel zechce go później wykorzystać.

## 6. Automatyczna kontrola techniczna

[GitHub Actions #40543896275](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40543896275) — **12/12** testów syntetycznej struktury lokalnej weryfikacji ID + **6/6** testów publicznych terminarzy i zachowania score-free. Dodatkowo zakończony PASS z prawdziwym podpisanym manifestem 1140 rekordów i **prawdziwym pobraniem 1140 neutralnych publicznych terminarzy**. Żaden test nie miał prywatnego PEM ani nie czytał wyników TEST.

**Stan formalny nie ulega zmianie:** 13/29; GATE14 PENDING; M0, 20 zamrożonych prognoz, pierwotny TRAIN/VALIDATION/TEST bez zmian; żadnych nowych płatnych wywołań PitchAPI.
