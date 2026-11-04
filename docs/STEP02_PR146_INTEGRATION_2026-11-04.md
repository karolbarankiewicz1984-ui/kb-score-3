# KB Score 3.0 — krok 02: kontrolowana integracja PR #146

**2026-11-04. Status:** STAGING / NO LIVE / NO MERGE.

Integracja jest złożona z 16 plików PR #146 przeniesionych bez zmian na aktualną bazę main (poza poprawką bezpiecznego push). Główny rejestr zmian docs/ZMIANY.md pozostawiono z najnowszymi wpisami main; nie kopiowano przestarzałej wersji z PR. Wyjściowe SHA kodu: PR #146 HEAD 42d3dd343bf6e4ff2ee8f6123eab22edcfb49118; main bb08bc0b7df9379b38cc78b9848eeb7989d0cc99.

**Dodatkowa poprawka:** usunięcie `git pull --rebase origin main` z aktualnego workflow, który commitował binarną bazę SQLite. Odrzucony push nie jest równoznaczny z sukcesem ani powodem do odtworzenia prognozy po kickoff. Niezmienne encrypted źródło/artefakt do audytu i ręcznego odzysku.

**Przed GO LIVE:** pełne CI z nowego HEAD; bieżące dopasowanie archiwalnych 126 forecast / 74 settlement; niezależny test failure injection do SQLite i git push; upewnienie się, że trzy zaplanowane próby nie przekraczają zaakceptowanego limitu zapytań; potwierdzenie braku dostępu do chronionego ENG TEST i niezmienionych parametrów M0. Po przejściu bramek oddzielny kontrolowany pilot na prawdziwych nowych fixture z dowodem host publication przed kickoff−90min. Bez kupowania API i bez obsługi prywatnych kluczy.
