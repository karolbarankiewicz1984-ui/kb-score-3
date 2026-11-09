# KB Score 3.0 — starsze archiwa źródłowe i dowody czasu, 09.11.2026

## Rzeczywiście odnalezione starsze artefakty GitHub Actions

| Run | Artifact | Host created UTC | Zakres |
|---|---:|---|---|
| 41481041537 | 13159687689 | 2026-11-02T16:24:01Z | trzy ligi, zaszyfrowane źródła |
| 41635067083 | 13230171721 | 2026-11-03T12:22:00Z | Step14 C native as-of encrypted |
| 41651485987 | 13238225342 | 2026-11-03T14:13:32Z | trzy ligi, zaszyfrowane źródła i M0 snapshots |
| 41719944546 | 13272115890 | 2026-11-03T21:14:54Z | trzy ligi, zaszyfrowane źródła |
| 41848296270 | 13331503968 | 2026-11-04T14:31:19Z | trzy ligi, zaszyfrowane źródła |
| 42047007817 | 13425091466 | 2026-11-05T14:39:25Z | trzy ligi, zaszyfrowane źródła |

GitHub API potwierdza istnienie i niewygaśnięcie powyższych artefaktów. W pełni pobrano i zbadano **tylko** ZIP `13238225342`, SHA256 ZIP `3b783423f1b94e48661a7cb55ef3607330c4770808f87f34c27835899327a4c6`.

## Faktyczny odczyt ZIP 13238225342

Archiwum zawiera trzy zaszyfrowane `THREE_LEAGUE_DAILY_SOURCE.enc` z 2026-10-29, 2026-11-01, 2026-11-03 oraz manifesty i receipt, SQLite M0 Shadow i trzy pliki zamrożonych prognoz.

Wszystkie trzy `SHA256(ciphertext)` obliczono z rzeczywistych bajtów i porównano z manifestem: **3/3 zgodne**.
- 2026-10-29: 114206 bajtów, SHA `c75c3207bafbaa986abd64a1b0ef98409bcd4dd9e44dce7e2fe974c08fb13c4d`
- 2026-11-01: 115658 bajtów, SHA `d1bbaff07abb292d77646da00c4a871f01f8354867ce60d510f93dab3868fd96`
- 2026-11-03: 114201 bajtów, SHA `4e66e5c12e1e84beb149bafc77a63276b85539f61adac5415f90c0597560f354`

Manifest deklaruje `AES-256-GCM+RSA-OAEP-SHA256+gzip`, `offsite_restore_verified=false`, `provider_publication_proven=false`, `training_allowed=false`. Weryfikacja ciphertext SHA **nie jest** odszyfrowaniem, potwierdzeniem natywnych response bytes ani PIT. Co więcej: późniejszy host-created timestamp artefaktu nie dowodzi niezależnego archiwizowania wewnętrznej migawki w dacie wpisanej w nazwie katalogu.

## Decyzja

- Odnaleziono autentyczne starsze hostowane archiwa, które mogą posłużyć jako kandydaci do dalszego badania cutoff; **nie** przyznano im automatycznie kwalifikacji v3.
- Zaszyfrowane natywne dane wymagają kontrolowanego restore/receipt i oryginalnego czasu utworzenia wcześniejszego archiwum dla każdej prognozy. Nie omijać zabezpieczeń ani nie podstawiać daty katalogu za host timestamp.
- `formally_admitted_v3_training_rows=0`, `model_status=NOT_TRAINED`, M0/Champion/TEST bez zmian.
- Następny krok: read-only sprawdzić `forward_m0/kb3_forward_m0.sqlite` i zamrożone JSON dla identyfikatorów i cutoff; zestawić z metadanymi starszych ZIP, nie odszyfrowując bez dostępnego prawidłowego klucza. Następnie spróbować uzyskać rzeczywiste native bytes zgodnie z istniejącą procedurą, bez obchodzenia szyfrowania.
