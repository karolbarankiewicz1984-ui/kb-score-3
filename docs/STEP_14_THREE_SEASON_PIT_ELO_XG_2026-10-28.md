# KB Score 3.0 — krok 14: przegląd 2023/24, 2024/25, 2025/26, identyfikacja PitchAPI, Elo oraz xG (28.10.2026)

**Formalnie:** 13/29, **GATE14 PENDING**. Zapis źródłowy Step12 nie jest modyfikowany: pierwotne 760 TRAIN i 380 VALIDATION wciąż mają `feature_cutoff_utc=null`. **Nie ma oficjalnego produkcyjnego CatBoost M1 ani certyfikowanych historycznych cech 121+38.**

## A. Historyczna dostępność wcześniejszych wyników — rzeczywisty audyt

Dla każdego dokumentowanego publicznego źródła wymagano łącznie (1) oryginalnego Git SHA, (2) autentycznych bajtów starego pliku i `SHA256`, (3) **niezależnego `GH Archive PushEvent` dokładnie tego SHA na publicznej gałęzi z serwerowym UTC**, (4) ukończonych wyników z rzeczywiście wcześniejszych spotkań, (5) braku wyników docelowych. Godzina commita służy wyłącznie do odnalezienia godzinnego archiwum; nie jest `published_at`.

| Sezon i historyczna publikacja UTC | Stary plik zawierał FT | Kandydaci z warunkowo kompletną formą 5 | Poświadczenie |
|---|---:|---:|---|
| 2023/24, FPL 05.10.2023 14:38:59 | 70 | 8 | niezależny PushEvent 32344206544, SHA `96fbc38...` |
| 2023/24, FPL 04.12.2023 13:04:15 | 140 | 8 | niezależny PushEvent 33866831577, SHA `c4f66ee3...` |
| 2024/25, OpenFootball 02.10.2024 13:52:44 | 60 | 10 | niezależny PushEvent 42475053178, SHA `5f777dc6...` |
| 2025/26, OpenFootball 30.07.2025 16:20:53 | 0 | 0 | niezależny PushEvent 52743265113, SHA `fdca227e...` |

**Łącznie: 26 par (archiwalna migawka, publiczny mecz) z warunkowo dostępnymi poprzednimi pięcioma wynikami obu drużyn.** Nie jest to 26 podpisanych przykładów PitchAPI ani dowód kompletności 121+38 cech. Wśród dwóch wersji FPL 2023/24 te 70 i 140 wyników to częściowo **te same, powtórzone** mecze: **nie** wolno ich sumować jako 210 różnych wyników Elo.

Pozostałe stare SHA sprawdzono oddzielnie, ale dla wielu brak niezależnego archiwalnego zegara; pozostają **`UNVERIFIED`** nawet gdy surowe dane i liczniki zakończonych spotkań można dziś odtworzyć. Ponadto repozytorium FPL samo informuje, że przestało publikować cotygodniowe migawki po 2024/25. Nie twierdzimy, że prawdziwych statystyk w tych okresach nie było; potwierdzamy jedynie brak wymaganych, niezależnych dowodów ich pierwszej dostępności w konkretnych zbadanych plikach.

Źródło audytu: `src/kb3_step14_multiseason_pit.py`, `src/kb3_step14_three_season_discovery.py` i osobny workflow `.github/workflows/kb3-step14-three-season-asof.yml`. Ten workflow wykonuje prawdziwy sieciowy odczyt wyłącznie publicznych starych wersji, bez płatnych sportowych API i bez danych TEST.

## B. Tożsamość PitchAPI — tylko oryginalne mecze, nigdy zgodność samej godziny

**Rzeczywiście sprawdzone teraz:** oryginalna lokalna tożsamość 4 znanych natywnych meczów z poprzedniego autentycznego RSA owner-only audit. Tylko Everton–Newcastle 05.10.2024 ma obecnie poświadczoną w tej konkretnej starej migawce pełną, źródłową formę 5; trzy wczesne spotkania 2025/26 mają w lipcowym starym pliku **0 wyników**, a wrześniowy Bournemouth–Newcastle jest udokumentowaną zmianą terminarza, nie wolno go podmienić na starą inną parę.

**Przygotowany bezpieczny etap dokładniejszego połączenia:** `scripts/step14_multiseason_owner_native_join_local.py`. Jest to niezależny skrypt offline na komputer właściciela, korzystający z **tego samego zaszyfrowanego ZIP, oryginalnego RSA PEM, hash chain i niezmiennego SAFE INDEX**. Algorytm:

1. W pamięci odtwarza oryginalne 1140 terminarzy PitchAPI i natywne ID drużyn; odrzuca inne hashe i nieprawidłowe metadane.
2. Dla 2023 FPL porównuje identyfikatory 20 drużyn FPL z 20 oryginalnymi natywnymi identyfikatorami **według pełnego, dwukierunkowego zestawu wcześniejszych godzin spotkań** (dom/wyjazd). Wymaga bijekcji 20/20 i liczby wcześniejszych spotkań odpowiednio 70 lub 140; dopiero potem wybiera dokładną parę i kickoff każdego publicznego celu. W przypadkach niejednoznacznych **odmawia join**.
3. Dla 2024/25 i 2025/26 wymaga dokładnego kanonicznego home/away, sezonu oraz czasu UTC. Nie zamienia wyników później przeniesionych spotkań na inne ID.
4. Eksportuje tylko liczniki udanych połączeń i odmów. Nie zapisuje ani nie wyświetla prywatnych native ID, wyników, xG, etykiet, prywatnego PEM ani TEST; **nie tworzy zbioru treningowego**.

**Skryptu RSA nie uruchamiano w GitHub Actions ani tutaj**, ponieważ właściwy prywatny klucz pozostaje na komputerze właściciela. Testy CI są syntetyczne; nie wolno ich podawać jako autentycznego 1140/1140 PIT join. Wcześniejszy realny owner-local odczyt 1140/1140 tożsamości pozostaje odrębnym dowodem, nie certyfikatem cech.

Przykładowe polecenie na tym samym komputerze i z tymi samymi lokalnymi plikami co wcześniejszy RSA audit (wynik do nowego pliku, **nie w repozytorium**):

```powershell
py -3 -m scripts.step14_multiseason_owner_native_join_local --archive-zip "$HOME\Downloads\KB3_PITCH_PL_2023_2026_NATIVE_20261026.zip" --private-key "$HOME\Desktop\KB3_760_PAKIET_ODZYSKIWANIA_POUFNE\KB3_760_KLUCZ_ODZYSKIWANIA.pem" --output "$HOME\Desktop\KB3_STEP14_MULTISEASON_JOIN_PRIVATE_AGGREGATE.json"
```

## C. Osobno: ciągłość matematyki Elo

Zamrożone **parametry Step11**: `initial=1500`, `K=20`, `home_advantage=65`, `scale=400`, `season_retention=0.85`. Do Elo trafiają tylko wyniki rzeczywiście znane przed analizowanym meczem; przy jednoczesnym kickoffie brak informacji z równoległego meczu. Replayer badawczy `src/kb3_step14_elo_xg_readiness.py` rzeczywiście używa wcześniejszych, historycznie udostępnionych FT z 2023, sprawdza powtarzalność i symetryczną korektę Elo bez eksportu ratingów ani wyników.

**Pełnego oryginalnego, trzysezonowego łańcucha Elo nie zatwierdzono**: nie wykazano na historycznych zegarach wszystkich 380/380 wyników starszych sezonów jako dostępnych przed każdym późniejszym targetem, nie potwierdzono kompletnego połączenia starych publicznych wydarzeń z natywnymi IDs dla wszystkich 20 zespołów i nie udokumentowano zastosowania przenoszenia Elo między sezonami w ówczesnym PIT. Istniejący wielosezonowy replay PitchAPI działa retrospektywnie, lecz jego pobranie w 2026 nie legalizuje historycznego `as-of`.

## D. Osobno: xG

Oryginalne historyczne 2023/24–2025/26 PitchAPI nie zawiera niezależnych dowodów **`provider_original_published_at`** statystyk xG/xGA dla każdego wcześniejszego spotkania. Próba statystyk strzałów z 2026/27 jest autentyczna, lecz nie dowodzi wcześniejszej dostępności team xG z 2023–2026. Nie przenosimy player xG z FPL do team xG PitchAPI, nie podstawiamy braków jako zero i nie podszywamy się aktualnym `captured_at` pod historyczne `published_at`.

**Stan końcowy tego audytu:** ogólne dowody częściowych publicznych wyników — TAK; reprodukcja części matematyki Elo — TAK; pełny natywny PIT Elo — NIE; historyczne, porównywalne PIT xG — NIE; oryginalny **TRAIN 0/760, VALIDATION 0/380; GATE14 PENDING, M1 zablokowany**. Oryginalne M0, 20 prognoz, TEST oraz podział Step12 bez zmian.
