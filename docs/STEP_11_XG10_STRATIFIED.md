# KB Score 3.0 — krok 11: 10 dodatkowych źródłowych xG, osobny zaszyfrowany archiwum i bezpieczne cechy

**Data 26.10.2026. Status: część techniczna PASS, całe GATE11 nadal PENDING (10/29).** Bez treningu, prognoz i nowych zakupów. Brak zmian starszych modeli.

## Cel i próba

Nie ponawiano trzech rozpoznanych wcześniej spotkań PitchAPI. Nowy audyt [GitHub Actions #40308346204](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40308346204) pobrał **dziesięć zakończonych spotkań Premier League 2026/27 z dziesięciu różnych dat**, rozłożonych równomiernie wśród dostępnych ukończonych spotkań. Odczyt wykonany `2026-10-26T10:33:40.352299Z`. Dokładnie **12 zapytań PitchAPI** (katalog + terminarz + 10 feedów strzałowych) oraz jedno API-Football, bez błędów dostawców.

- **10/10** kompletnych strzałowych feedów xG obu drużyn.
- **5/10** ścisłych, jednoznacznych i natychmiast dopuszczonych par `EXACT_TIME_NAMES_SCORE_FT` (czas UTC, nazwy, wynik, final FT).
- **5/10** zachowano w kwarantannie, w tym 4 `ALIAS_REVIEW_REQUIRED` oraz 1 `NAME_DISAGREEMENT_OR_AMBIGUITY`. Nie przypisano im kanonicznych ID; nie ma automatycznego promowania aliasów.
- Poprzedni audyt z 25.10.2026 dał trzy osobno zaudytowane powiązania. **Łącznie 8 potwierdzonych par w tych 13 indywidualnych próbkach**, lecz to **nie** dowód pełnego pokrycia ligi ani wskaźnik skuteczności modelu. Starszego pilota 12 spotkań z innych sezonów nie należy automatycznie wliczać do tej samej próbki.

## Szyfrowanie i niezależny test odtworzenia

Nowe źródłowe payloady i oryginalne ID są zapisane tylko w zaszyfrowanym SQLite `KB3PIT1`, z AES-256-GCM i kopertą RSA-OAEP, **tym samym offline kluczem użytkownika** co wcześniejsze archiwa.

- [Prywatna zaszyfrowana kopia na Google Drive](https://drive.google.com/file/d/1l0Ng06QDIqM1h8IUH9m3Z8aER4f_COdC/view?usp=drivesdk), ZIP **85 496 B**.
- ZIP SHA-256: `303b0baafbafb2b4123c1d264d4387dd22b1540815cbe52a6e3469ee7d98c85d`.
- Szyfrogram SHA-256: `5be52306e2fa0eb6928366e831370104a75ee81a1559a7740161cc5dc802bbea`.
- Po pobraniu *ponownie z Drive*, odszyfrowaniu kluczem prywatnym spoza GitHuba i ponownym przeliczeniu treści: `PRAGMA integrity_check=ok`, `foreign_key_check=0`, pełne 380-record source hash chain oraz **10/10** rekordów xG zgodnych z zapisanymi sumami i oryginalnymi strzałami. Żadnej bazy surowej ani prywatnego klucza nie wysłano do GitHuba.
- [Trwały zbiorczy raport SHA i wyników](../data/audits/STEP11_XG10_STRATIFIED_REAL_2026-10-26.json).

## Integracja z istniejącym ELO, formą i xG

- `src/kb3_external_xg_asof.py` odczytuje ściśle dopasowane xG **z drugiego, niezależnego archiwum** bez przepisywania danych i bez łączenia dwóch niezależnych łańcuchów hashy w fałszywie pojedynczy zapis. Sprawdza rzeczywiste hashe i agregaty każdej bazy z manifestem, zgodność źródłowej odpowiedzi 380 spotkań między pierwszym i drugim archiwum oraz cutoff przed źródłową obserwacją. Rozbieżne hashy, zakres dostawcy lub naruszony manifest blokują całe źródło.
- `src/kb3_observed_features.py` i `scripts/step11_observed_features_audit.py` mają nowe **opcjonalne** parametry niezależnej bazy xG i jej manifestu. Nie zmieniają trybów `replay` oraz `verified`, nie podmieniają NULL zerem. Przy wykryciu kolizji źródła reviewed i strict dla jednego meczu następuje odmowa. Rygor czasowy: najpierw rzeczywisty odczyt źródła, dopiero potem xG w cechach późniejszych meczów.
- Niezależny test lokalny z rzeczywistych *dwóch* odszyfrowanych kopii Drive i kodu [Actions #40309429624](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40309429624): **380** zgodnych źródłowych meczów, **5** nowych ścisłych xG, brak modyfikacji obu baz. Dla przyszłego fixture `1557452`, cutoff `2026-10-26T10:45:00Z`: **80** poprzednich wyników oraz **1** historyczna xG-obserwacja w ostatnich 5 spotkaniach gospodarzy, **0** w analogicznym oknie gości. Przy cutoff `10:20Z`, czyli przed drugim pobraniem o `10:33:40Z`, nowego xG **0**; bez drugiego źródła także **0**. `training_allowed=false`.
- Wszystkie ten daty źródłowe są z obserwacji **26.10.2026**. Nie podano ani nie odtworzono oryginalnej daty opublikowania xG przez dostawcę. Nie ma z tego historycznego certyfikowanego backtestu za sezony 2023–2025.

## Testy i dalsze prace

[GitHub Actions #40309316442](https://github.com/karolbarankiewicz1984-ui/kb-score-3/actions/runs/40309316442): **140/140 PASS** — 101 testów Step11 i 39 wcześniejszych. W tym selekcja 10 rozłożonych dat, duplikaty, brak finalnego statusu, historia o zbyt krótkim odstępie, rygor czasowy, brak zweryfikowanej tożsamości, dwa oddzielne źródła, niezgodny hash całej odpowiedzi, zepsuty manifest, brak treningu. W PR nie wydajemy dodatkowych żądań API.

**GATE11 NADAL PENDING.** Do pracy: sprawdzenie pięciu kolejnych niejednoznacznych par *bez automatycznych aliasów*, dalsze faktyczne obserwacje z innych dni (nie da się uzyskać ich przez zmianę daty), próbka referencyjna większej liczby lig / typów źródeł, ocena kompletności xG i końcowy audyt przecieków. Bieżące wykonanie nie tworzy harmonogramu płatnych wywołań. K20, przewaga 65, retencja 0.85 nadal robocze i niewytrenowane.
