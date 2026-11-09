# KB3 CatBoost v3 — zakończona kontrola starszego SQLite i prognoz (09.11.2026)

Oryginalny GitHub Actions ZIP artifact **13238225342** z run **41651485987** został rzeczywiście pobrany, odczytany i porównany z manifestami. ZIP SHA256: `3b783423f1b94e48661a7cb55ef3607330c4770808f87f34c27835899327a4c6`. Odczytany `forward_m0/kb3_forward_m0.sqlite` SHA256 `df39abd9daed3b43793a71bb58dc2c9eb548a69e2f84d4e397f671f0a42b7144`, `PRAGMA integrity_check=ok`.

## Zidentyfikowane rekordy

- **27** `m0_shadow_1x2_forecasts`: ESP 10, GER 6, ITA 11; cutoff w dniach 2026-10-29 (12), 2026-11-01 (9), 2026-11-03 (6). Zgodne liczności z trzema zamrożonymi plikami JSON: 12+9+6.
- **21** `m0_shadow_1x2_settlements`.
- **18** `m0_forward_sources`, z czego **18/18** bez `raw_provider_first_published_at_utc`.
- **27** `m0_forward_feature_records`, **0** z `eligible_for_original_M1=1`.
- **18** `source_snapshots`, wszystkie z `availability_class=NOT_VERIFIED`.
- Trzy `THREE_LEAGUE_DAILY_SOURCE.enc` 29.10, 01.11 i 03.11 mają SHA256 zgodne z manifestem **3/3**, ale wszystkie trzy manifesty deklarują `training_allowed=false`, `source_first_published_at_known=false`, `offsite_restore_verified=false`.

## Decyzja końcowa etapu

Weryfikacja starszych źródeł, tożsamości prognoz, cutoff i manifestów została wykonana w zakresie **dostępnych oryginalnych bajtów ZIP, SQLite, JSON i zaszyfrowanych payloadów**. Nie można uczciwie uznać tych rekordów za formalne TRAIN v3: brak odszyfrowanych natywnych odpowiedzi i niezależnych dowodów publikacji. Formalne dopuszczenie **0**, model `NOT_TRAINED`. Nie ma podstaw do wykonywania kolejnych pozornych kwalifikacji na tych samych dowodach.

**Rozdzielić dwie ścieżki:** (A) formalny v3: przyszłe natywne archiwa i niezależne czasy przed cutoff, następnie rzeczywisty TRAIN/VAL i prospektywne Shadow; (B) odrębny, jawnie niecertyfikowany retrospektywny eksperyment na istniejącej historii (już istnieją warianty 1007/376), bez przenoszenia wag i wyników do v3 Champion. Odtworzenie zaszyfrowanych payloadów wymaga dostępnego zgodnego klucza i istniejącej procedury restore; nie obchodzić szyfrowania.

Nie zmieniono M0, TEST, harmonogramu, danych ani progów bezpieczeństwa. Wpis dokumentuje zamknięcie audytu, **nie** ukończenie treningu.
