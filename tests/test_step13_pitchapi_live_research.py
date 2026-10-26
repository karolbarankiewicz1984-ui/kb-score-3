"""Only artificial labels; real immutable fixture IDs are used as a skeleton.

NEVER get real historical scores in ordinary CI tests.
"""
from __future__ import annotations
import copy
import json
from pathlib import Path
import unittest

from scripts.step13_pitchapi_research_once import (
    SEASONS, LEAGUE, extract_research_rows, assemble,
    SCHEMA, EXPECTED_COUNT,
)


def fixtures():
    path=Path(__file__).resolve().parents[1]/"data/splits/STEP12_SAFE_MODEL_VIEW_2026-10-26.json"
    safe=json.loads(path.read_text(encoding="utf8"))
    seasons={}
    for year in SEASONS:
        year_start=int(year[:4])
        original=[f for f in safe["fixtures"] if
                  year_start<=int(f["kickoff_utc"][:4])<=year_start+1 and
                  f["kickoff_utc"]>=f"{year_start}-07-01T00:00:00Z" and
                  f["kickoff_utc"]<f"{year_start+1}-07-01T00:00:00Z"]
        assert len(original)==380
        matchlist=[]
        for i,fixture in enumerate(original):
            home=(i%20)+1
            away=((i+7)%20)+1
            matchlist.append({
                "id":fixture["fixture_id"],"time_utc":fixture["kickoff_utc"],
                "home_team":{"id":f"t_{home:06d}","name":f"SYNT_TEAM_{home}"},
                "away_team":{"id":f"t_{away:06d}","name":f"SYNT_TEAM_{away}"},
                "status":"finished",
                "score_home":i%4,"score_away":(i*3+1)%4,
            })
        seasons[year]={"matches":matchlist}
    return safe,seasons


class Step13LiveProviderResearchContracts(unittest.TestCase):
    def test_exact_frozen_ids_and_synthetic_only_replay(self):
        safe,season=fixtures()
        rows,digests=extract_research_rows(season,safe_view=safe)
        self.assertEqual(len(rows),EXPECTED_COUNT)
        self.assertEqual(len(digests),3)
        self.assertFalse(any("odds" in r for r in rows))
        self.assertFalse(any("source" in r for r in rows))
        report=assemble(season,safe_view=safe,observed_at="2026-10-27T00:30:00Z")
        self.assertEqual(report["schema"],SCHEMA)
        self.assertEqual(report["validation_partition_rows"],380)
        self.assertEqual(report["train_partition_rows"],760)
        self.assertEqual([f["validation_count"] for f in report["folds"]],
                         [60,126,123,71])
        self.assertEqual(report["provider_requests_exactly"],3)
        self.assertFalse(report["test_partition_data_requested"])
        self.assertFalse(report["training_allowed"])
        self.assertFalse(report["gate13_pass"])
        self.assertFalse(report["historical_pit_backtest_performed"])
        self.assertFalse(report["source_scores_in_report"])
        self.assertFalse(report["owner_private_rsa_key_used"])
        self.assertTrue(report["real_match_outcomes_used_for_research"])
        for method in ("EXPANDING","ROLLING_24_CALENDAR_MONTHS"):
            self.assertEqual(report["overall"][method]["validation_n"],380)

    def test_kickoff_drift_fails_closed(self):
        safe,season=fixtures()
        season["2023/2024"]["matches"][0]["time_utc"]="2023-08-15T19:00:00Z"
        with self.assertRaisesRegex(ValueError,"DRIFT"):
            extract_research_rows(season,safe_view=safe)

    def test_fixture_id_changed_fails_closed(self):
        safe,season=fixtures()
        season["2023/2024"]["matches"][0]["id"]="m_ZZzz99"
        with self.assertRaisesRegex(ValueError,"DRIFT"):
            extract_research_rows(season,safe_view=safe)

    def test_fetched_test_season_rejected_even_if_valid_data(self):
        safe,season=fixtures()
        season["2026/2027"]={"matches":[]}
        with self.assertRaisesRegex(ValueError,"WRONG_SEASON"):
            extract_research_rows(season,safe_view=safe)

    def test_extra_odds_ignored_not_model_feature(self):
        safe,season=fixtures()
        season["2023/2024"]["matches"][0]["bookmaker_odds"]=3000
        a=extract_research_rows(season,safe_view=safe)[0]
        self.assertEqual(len(a),1140)
        self.assertEqual(set(a[0]),
            {"fixture_id","home_team_id","away_team_id","kickoff_utc",
             "goals_home_90","goals_away_90"})

    def test_duplicate_or_incomplete_match_fails(self):
        safe,season=fixtures()
        season["2023/2024"]["matches"].pop()
        with self.assertRaisesRegex(ValueError,"INCOMPLETE"):
            extract_research_rows(season,safe_view=safe)

    def test_safe_train_partition_poison_fails(self):
        safe,season=fixtures()
        safe["training_allowed"]=True
        with self.assertRaisesRegex(ValueError,"PROMOTED"):
            extract_research_rows(season,safe_view=safe)

    def test_invalid_goals_fails(self):
        safe,season=fixtures()
        season["2025/2026"]["matches"][0]["score_home"]=None
        with self.assertRaisesRegex(ValueError,"FINAL_SCORE"):
            extract_research_rows(season,safe_view=safe)

    def test_report_uses_real_retrieval_time_not_historical_pit(self):
        safe,season=fixtures()
        report=assemble(season,safe_view=safe,observed_at="2026-10-27T11:00:00Z")
        self.assertEqual(report["provider_read_at_utc"],"2026-10-27T11:00:00Z")
        self.assertEqual(report["source_category"],
                         "REAL_PROVIDER_RETRIEVED_NOW_RETROSPECTIVE_EVENTTIME_ONLY")
        self.assertFalse(report["historical_original_provider_pubtime_certified"])
        self.assertFalse(report["model_production_eligible"])


if __name__=="__main__":
    unittest.main()
