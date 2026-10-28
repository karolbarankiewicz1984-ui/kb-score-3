# KB Score 3.0 — zasady obsługi dostępów i integralności modelu

Decyzja właściciela projektu: **nie wymagać każdorazowego ręcznego zabezpieczania lub ponownego uwierzytelniania po jego stronie**. Zachować blokady niezbędne do poprawności naukowej i działania modelu.

## Obsługa techniczna — ograniczyć do minimum

1. Używać wcześniej skonfigurowanych dostępów, środowisk, kluczy API i GitHub Actions, jeśli są dostępne oraz uprawnione do danego zadania. Nie żądać od właściciela ponownego wpisywania klucza lub pobierania repozytorium przy każdej operacji.
2. Raz zatwierdzony oryginalny zaszyfrowany pakiet oraz weryfikację jego integralności traktować jako **utrwalony wynik audytu** dla identycznego, niezmienionego SHA, nie powtarzać wszystkich wcześniejszych procedur bez nowej przesłanki.
3. Kontrole techniczne wykonywać automatycznie i inkrementalnie: nowy albo zmieniony element sprawdzać, bez niepotrzebnego powtarzania prac niezmienionych.
4. Nie przekazywać prywatnego RSA PEM, wartości klucza API, odszyfrowanego archiwum ani prywatnych danych do GitHub, logów, raportów lub czatu. Jest to stała zasada implementacyjna, **nie prośba o każdorazową czynność użytkownika**.
5. Uczciwie rozdzielać możliwości: GitHub Actions może wykorzystywać skonfigurowany sekret do zapytań API, ale sekret nie jest możliwy do odczytania z GitHub na Windowsie; lokalny PEM pozostaje na komputerze właściciela. Jeśli brakujący dostęp naprawdę uniemożliwia konkretny eksperyment, wyjaśnić jednorazowo dokładną przyczynę i szukać najpierw sposobu bez dodatkowej ręcznej obsługi.
6. Minimalizować liczbę pobrań i płatnych żądań API, utrzymywać sensowny budżet żądań. Unikać tworzenia osobnego systemu zabezpieczeń dla każdej drobnej zmiany.

## Niezmienione rygory modelowe — nie usuwać

- **PIT / no leakage:** każda cecha historyczna musi być dostępna przed rzeczywistą godziną analizowanego meczu, ze sprawdzonym źródłem, tożsamością spotkania i drużyny oraz definicją statystyki. Żadnego korzystania z późniejszych wyników, historycznych korekt dostępnych dopiero po meczu lub fikcyjnych `published_at`.
- **Zamrożone zbiory:** TRAIN 760, VALIDATION 380 i odseparowany TEST 380 według oryginalnego kontraktu; nie oglądać etykiet TEST przed właściwym etapem.
- **Matematyka i audyt:** pozostają testy Elo, Poissona, CatBoost, kontrola kalibracji, deduplikacji, rozdzielenia sezonów i występowania błędów. Rzetelne wartości `null` i missingness flag zamiast dopisywania zer.
- **Wersjonowanie dowodów:** zmiany algorytmu, przeliczenie danych i zmiana źródła cechy muszą być jawne, porównywalne z poprzednim wynikiem. Nie zamieniać bez uzgodnienia FPL/Opta/Understat xG na oryginalne PitchAPI xG.
- **GATE14:** pierwotne wymagania 121 cech + 38 flag i pełnej historycznej dostępności pozostają do spełnienia. Uproszczenie obsługi dostępów **nie oznacza odblokowania treningu M1** ani zmiany obecnego statusu audytu.
- Zachować oryginalny M0, zamrożone wcześniejsze prognozy i zasady wiarygodnej walidacji.

## Zasada praktyczna

**Jednorazowa konfiguracja dostępu, ponowne wykorzystanie dowodów, automatyczne testy przy zmianie danych oraz minimum koniecznych działań właściciela.** Blokady metodologiczne istnieją po to, aby model prognozował uczciwie; nie przerzucać ciężaru bezpieczeństwa operacyjnego na właściciela przy każdym kolejnym kroku.
