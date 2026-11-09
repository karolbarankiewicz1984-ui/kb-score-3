# KB Score 3.0 — końcowy audyt parowany CatBoost 20 vs 87 (2026-11-09)

**Status:** `RETROSPECTIVE_RESEARCH_ONLY`; nie jest to oficjalny fit v3, nie jest to PIT i nie jest to prospektywny Shadow.

Ponownie uruchomiono oba rzeczywiste skrypty CatBoost na tej samej historycznej bazie SQLite, uzyskano wektory prawdopodobieństw 1X2 i skojarzono je po `league|match_id|kickoff_utc`. Weryfikacja: 747/747 dokładnie tych samych spotkań, te same etykiety, zero duplikatów, 12 tygodni ISO.

| Metryka | Model 20 | Model 87 | Zysk 87 |
|---|---:|---:|---:|
| Top1 accuracy | 0.4484605 | 0.4886212 | +4.0161 pp |
| Brier sum3 | 0.6371830 | 0.6201228 | 0.0170602 mniej |
| Log loss | 1.0556964 | 1.0304821 | 0.0252143 mniej |

**Kontrola niepewności:** 5000 parowanych losowań bootstrap po tygodniach ISO (12 klastrów), seed 20261109; 95% percentylowy CI poprawy: accuracy **[+2.3506, +5.4523] pp**, Brier reduction **[0.00343, 0.02946]**, log loss reduction **[0.00556, 0.04301]**. To eksploracyjna niepewność na jednym retrospektywnym okresie, nie gwarancja prospektywnej przewagi ani korekta na wybór modelu po analizie danych.

Lokalne audytowalne wyniki: `validation_20.npz` SHA256 `fd675753a528d779e0f0fbfa10ec027ff55d69f20c456ff9cb65a54962d6e633`; `validation_87.npz` SHA256 `0882c365e2855489adb69650fcd97d04b62e1ba815a4a980e51cb282be04cba2`; `PAIRED_AUDIT_87_VS_20.json` i `paired_audit.py`. Dane nie są certyfikowanym źródłem PIT.

**Kontrola architektury:** skrypt 87 używa 87 nazw i kolejności kontraktu oraz okien, ale jego osobna rekonstrukcja nie jest formalnie zgodna bajtowo z `src/kb3_p1_shared_asof_features_v2.py` i `src/kb3_catboost_research_v3.py`. Nie wolno podłączać wytrenowanego CBM do oficjalnego `verified_view` bez fixture-level parity tests. Brakuje kwalifikowanego nowego przedmeczowego archiwum dla Shadow; nie wygenerowano pozornych prognoz.

**Decyzja:** etap retrospektywnego porównania 20 vs 87 zamknięty, model 87 zachowany jako osobny kandydat badawczy. Produkcyjny M0/Champion/TEST bez zmian. Przed prawdziwym Shadow potrzebne: (1) kontrola równości buildera na danych kontrolowanych, (2) bieżące dane i host-attested cutoff, (3) prospektywne prognozy po rzeczywistym czasie treningu, (4) rozliczenie zamrożonych prognoz.
