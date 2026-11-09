# KB3 — rzeczywisty eksperymentalny trening 87 cech, 2026-11-09

Status: **TRAINED_RETROSPECTIVE_RESEARCH_ONLY**, **NOT PIT CERTIFIED**, **NOT OFFICIAL V3 FIT**. Nie dotykano M0/Champion/TEST ani płatnych API.

Z istniejącej bazy SQLite z GitHub Actions artifact `13635728620` przeprowadzono lokalny CatBoost MultiClass na **87 zmiennych** o nazwach, oknach all/venue 5/10/15, Elo, sezonowym retention i missing flags odpowiadających kontraktowi `kb3_catboost_asof_v3.json`. W eksperymencie zrekonstruowano cechy osobnym skryptem retrospektywnym, **nie** wywołano oryginalnego certyfikowanego `build_shared_features` ani `verified_view`. Źródłowe historyczne godziny publikacji pozostają niezweryfikowane. Wynik nie może być przeniesiony do oficjalnego modelu v3.

**Chronologiczny split:** TRAIN 2845 przed 2026-03-01, embargo 7 dni, VALIDATION 747 od 2026-03-08; osiem lig BEL ESP FRA GER ITA NED POL TUR. Trening CatBoost 1.2.8: 180 iterations, depth3, learning_rate0.035, l2_leaf_reg8, seed20261109. Bez strojenia na validation. Wykonano dodatkową kontrolę identyfikatorów: **identyczne 2845 train i 747 validation** z poprzednim modelem 20-cechowym (klucze league, match_id, kickoff UTC; 0 różnic).

| Metryka (te same 747 spotkań) | CatBoost 20 | CatBoost 87 |
|---|---:|---:|
| top1 | 0.4484605 | **0.4886212** |
| Brier sum3 | 0.6371830 | **0.6201228** |
| Log loss | 1.0556964 | **1.0304821** |

Poprawa top1 o 4.016 pp, Brier o 0.01706, log loss o 0.02521. To sygnał badawczy, nie wynik prospektywny. Per liga accuracy: BEL 0.4409/93, ESP 0.5130/115, FRA 0.4419/86, GER 0.4578/83, ITA 0.5094/106, NED 0.5125/80, POL 0.4583/96, TUR 0.5682/88.

Lokalnie zapisano rzeczywisty model `CATBOOST_RETRO_87_FEATURES_NOT_PIT.cbm` SHA256 `7e85bb28bcd92ddb3f1bdc5dc9534b80f5a7d9aff0db0873f59b1bd002b2170a`, raport `RETRO_87_TRAIN_REPORT.json`, skrypt `train_retro_87.py`. Są dostępne w bieżącej sesji, nie są włączone do repo ani produkcji.

**Kolejne bramki:** (1) test zgodności odtworzonej semantyki z oryginalnym builderem na niezależnych kontrolowanych fixture; (2) osobny, przyszły prospektywny Shadow z rzeczywistym przedmeczowym zamrożeniem i niezależnym archiwum; (3) audyt kalibracji i rozdzielności lig, bez promocji na podstawie retrospekcji.
