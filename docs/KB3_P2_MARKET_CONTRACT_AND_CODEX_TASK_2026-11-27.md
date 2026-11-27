# KB3 P2-02 — kontrakt statystyk i zadanie implementacyjne

Data weryfikacji: 27.11.2026. Issue #190. P2-01 ukończone (#191): 7592 normalized observations; nie powtarzać audytu. P2-02 częściowo: publiczne reguły znalezione, zgodność rzeczywistego feedu niepotwierdzona. P2-03/04 otwarte.

## Źródła i ograniczenia

- PitchAPI: https://pitchapi.dev/ (Team stats: połowy i cały mecz, wartości tekstowe z format_type; nie wynika stąd dowód, że zarchiwizowana wersja SDK 0.1.6 wyklucza dogrywkę lub ma definicje identyczne z operatorem). Oryginalne payloady i wersja schematu wymagają sprawdzenia lokalnie, bez ujawniania kluczy.
- Superbet, komunikat 06/2022, nagłówek i data obowiązywania na stronie 16.12.2025 mimo starszej daty w URL: https://superbet.pl/wiki/oficjalny-komunikat-nr-06-2022-z-dnia-18-11-2024-r . Tylko faule odgwizdane; rożne faktycznie wykonane; kartki aktywnych graczy, z regułą przerwy, wykluczone ławka/sztab i po końcu. Łączna liczba kartek: żółta 1, bezpośrednia czerwona 2, wykluczenie po dwóch żółtych 3. Punkty karne to odrębna jednostka (10/25, limit 35 na gracza).
- STS: https://pomoc.sts.pl/pilka-nozna/ (aktualizacja 25.08.2026): liczba kartek 1/2/3, regulaminowy czas i uczestnicy gry; nie przenosić automatycznie szczegółowych reguł Superbet na STS. Wymagane konkretne definicje rynku i wersja regulaminu.
- Żaden z tych dokumentów nie poświadcza zbieżności rzeczywistego PitchAPI z dostawcą rozliczeń bukmachera. Brak dokładnej reguły strzałów, nie deklarować zgodności.

## Kontrakt wewnętrzny badawczy (propozycja do wdrożenia)

Zakres tylko 8 krajowych lig, mecz 2x45 z doliczonym czasem, bez ENG TEST, dogrywki i karnych. UCL początkowo wyłączona z powodu okresów i mapowania. Osobne targety count home/away/total: fouls_called, corners_taken, total_shots, shots_on_target, yellow_cards, straight_red_cards, second_yellow_dismissals, card_units. Nie utożsamiać surowych pól fouls/corners/red_cards z tymi targetami bez dowodu; czerwone z drugiej żółtej nie mogą zostać policzone podwójnie. Brak informacji to NULL + reason. Nie inferować strzałów ogółem z sumy podkategorii. Klucz fixture/team/period/native stat definition/source revision; source hash, observed UTC i rzeczywisty host proof. Rynki badawcze bez kursów, bez sugerowania dostępności linii.

## Zadanie dla Codex — pierwsza mała, bezpieczna partia

1. Odczytaj docs/ZMIANY.md, aktywny rejestr 24.11, issue #190 i #181, P2 inventory oraz P2 coverage script. Sprawdź main i otwarte PR, nie dubluj gotowych prac.
2. P2-02: przygotuj odrębny parser/walidator kontraktu period/team/stat semantics i read-only audyt oryginalnych snapshots dostępnych lokalnie. Użyj istniejących mechanizmów odszyfrowania wyłącznie jeżeli bezpiecznie dostępne; nie zapisuj kluczy ani raw payloadów w logach/PR. Zero nowych provider calls. Jeśli brak dowodu semantyki, oznacz UNKNOWN/QUARANTINE, nie PASS. Udokumentuj dokładny native field i źródło dla każdego potwierdzonego targetu.
3. Testy syntetyczne: prawidłowy 90min, extra time, brak period, brak jednej strony, zamienione native team IDs, niepełny mecz, późne source observation, niedozwolone 0 zamiast NULL, konflikty drugiej żółtej/czerwonej i nieznane zdarzenia. Każdy odrębny target i jawny reason. Nie dotykaj chronionego TEST, starego ledgeru, produkcji, M0, GATE15, FIT100/HOLDOUT50.
4. Przygotuj plan późniejszego P2-03/04, nie trenuj i nie rozliczaj rynku, dla którego nie potwierdzono targetu. Rozważyć baseline Poisson versus negative binomial na chronologicznych danych, skorygować nadmierną dyspersję; porównywać na identycznych meczach, z per-match/tydzień metrykami i jawnie niezależnym holdoutem. Żadnych automatycznych rekomendacji ani promocji. 
5. PR z testami CI, read-only raportem realnych danych jeśli dostępne, dopisz wyniki i blokery do rejestru. Nie scalaj bez PASS. Kryterium odbioru P2-02 per target, nie zbiorczy PASS na podstawie samej dokumentacji. Podaj co wykonano, czego nie i jakie dowody są wymagane.

P0/P1 nadal w istniejących workflow; 15/29 bez zmian. Dokumentacja jest częściowym wykonaniem P2-02, nie działającym modelem.
