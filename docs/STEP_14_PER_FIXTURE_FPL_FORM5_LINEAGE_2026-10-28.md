# KB Score 3.0 — krok 14: rejestr dowodowy poprzednich wyników na poziomie pojedynczego meczu (28.10.2026)

**Status:** osobny kontrakt badawczy publicznego źródła; **GATE14 PENDING, 13/29**. Bez zmian Step12, Step13 M0, 20 podpisanych prognoz, podziału TRAIN/VALIDATION/TEST i oryginalnych dowodów. Nie trenuje się oficjalnego CatBoost M1.

## Dlaczego to jest potrzebne

Nawet jeżeli dane o 70 wcześniejszych wynikach faktycznie istniały 05.10.2023 14:38:59 UTC w publicznym historycznym SHA, nie dowodzi to automatycznie, że pięć ostatnich meczów drużyny dla **każdego przyszłego** spotkania można obliczyć z tego pliku. Następne wyniki mogą się pojawić **po** publikacji migawki; źródło z października stałoby się niepełne. Nie wolno podmieniać danych po fakcie.

## Implementacja bez oryginalnego TRAIN

- Skrypt `src/kb3_step14_fpl_form5_lineage.py`: jednorazowo pobiera publiczny archiwalny `fixtures.csv` ligi 2023/24 z konkretnego, zweryfikowanego SHA `96fbc38...`, kontroluje rzeczywisty `SHA256=07b88250...`, 380 fixture ID, dokładnie 70 wcześniej zakończonych FT i 310 pustych przyszłych wyników.
- Dowód zegara **nie** pochodzi z `git author/committer date`, lecz z niezależnego `GH Archive PushEvent ID 32344206544`, `2023-10-05T14:38:59Z`. Skrypt odmawia pracy przy zmianie czasu, źródła, hasha lub fladze braku potwierdzenia.
- Dla każdego przyszłego, jeszcze nierozpoczętego meczu w tej historycznej migawce: lista faktycznie wcześniejszych meczów każdej drużyny, kontrola że **wszystkie** wcześniejsze w danym sezonie były już zakończone i ich wyniki znajdowały się w starej opublikowanej migawce. Dopiero wtedy wybiera po pięć ostatnich `fixture_id`; wyniki bramkowe i punkty nie są eksportowane.
- Gdy źródło jest nieaktualne, brakuje godziny meczu, istnieje nierozstrzygnięte wcześniejsze spotkanie, nie ma pięciu poprzedników, albo występuje konflikt czasu — oznacza rekord jako niedopuszczony/niekompletny. Żadna wartość nie jest imputowana.
- Każdy rekord zawiera oryginalny publiczny `fixture_id`, stary czas meczu, `source SHA`, `public_push_utc`, identyfikator niezależnego zdarzenia, ewentualnie pięć ID poprzedników dla gospodarzy i gości. Nie eksportuje `FT` ani etykiety meczu docelowego.
- W workflow `.github/workflows/kb3-step14-fpl-per-fixture-lineage.yml` testy syntetyczne uruchamiane są przed próbą realnego publicznego CSV; bez kluczy, bez płatnego sportowego API; artefakt badawczy GitHub Actions, nie produkcyjny model.

## Granice dowodu

Taki rezultat potwierdza co najwyżej:

**Dla publicznego meczu FPL w starej, autentycznej migawce można warunkowo zrekonstruować wejścia publicznej formy 5 poprzednich wyników.**

Nie potwierdza jeszcze: poprawnego powiązania tego publicznego target `fixture_id` z natywnym PitchAPI `m_...` i rzeczywistą (w razie przekładania) godziną, oryginalnych cech `PitchAPI` 121+38, pełnego wcześniejszego łańcucha Elo, historycznego xG, ani możliwości treningu. Tych dowodów nie wolno zastępować technicznym powodzeniem kodu.

## Kolejność kolejnych prac

1. Odczytać realny raport z zatwierdzonego publicznego SHA: policzyć **ile konkretnie przyszłych spotkań** spełnia ścisłe kryterium kompletnej formy 5 w danej migawce. Nie podawać liczby bez wykonanego raportu.
2. Rozszerzyć zbiór autentycznie timestampowanych migawek publicznych (FPL 2023/24 oraz OpenFootball 2024/25–2025/26). Każdy nowy rekord tylko po niezależnej weryfikacji czasu publikacji i bez mieszania różnych wersji bez rozliczenia każdej zależności.
3. Dla potencjalnych targetów potwierdzić `home`, `away`, sezon oraz **bezpieczny wcześniejszy cutoff** względem autentycznego natywnego meczu; Ipswich–Everton zachowuje pierwotną granicę 14:00 UTC.
4. Osobno dowieść pełnego, nieprzerwanego łańcucha Elo (w tym historii startowej) i równoważności ewentualnych danych xG. Braki pozostają `NOT_PROVEN`.
5. Dopiero po spełnieniu wszystkich obowiązujących bramek formalnych rozpocząć produkcyjne M1; **aktualnie 0/760 TRAIN PIT oraz 0/380 VALIDATION PIT**.

Dokument nie ogłasza nowych zaliczonych kroków i nie zmienia harmonogramu 29 etapów.
