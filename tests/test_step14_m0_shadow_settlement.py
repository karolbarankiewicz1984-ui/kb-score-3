import sqlite3,tempfile,unittest
from datetime import datetime,timezone,timedelta
from pathlib import Path
from src.kb3_m0_shadow_settlement import judge_match,settle,review_calibration,SettlementError
from src.kb3_three_league_sqlite_forward_features import commit_sqlite
from src.kb3_m0_shadow_1x2_live_freeze import freeze
from test_step14_three_league_sqlite_forward_features import fake_capture,stamp,NOW

class SettlementTests(unittest.TestCase):
 def test_logloss_brier_math(self):
    game={"id":"m_000123","time_utc":"2026-10-29T10:00:00Z","status":"finished",
          "score_home":2,"score_away":0,
          "home_team":{"id":"t_000001"},"away_team":{"id":"t_000002"}}
    pred=("ESP","m_000123",game["time_utc"],"2026-10-29T07:00:00Z",
          "t_000001","t_000002",{"1":0.6,"X":0.3,"2":0.1})
    r=judge_match(game,pred,observed=datetime(2026,10,29,14,tzinfo=timezone.utc))
    self.assertEqual(r["result_1x2"],"1")
    self.assertAlmostEqual(r["log_loss"],0.5108256237659907)
    self.assertAlmostEqual(r["brier_sum3"],0.26)
 def test_3h_lag_strict(self):
    match={"id":"m_000123","time_utc":"2026-10-29T10:00:00Z",
          "status":"finished","score_home":0,"score_away":0,
          "home_team":{"id":"t_000001"},"away_team":{"id":"t_000002"}}
    p=("ESP","m_000123",match["time_utc"],"2026-10-29T07:00:00Z","t_000001","t_000002",{"1":0.5,"X":0.25,"2":0.25})
    self.assertIsNone(judge_match(match,p,observed=datetime(2026,10,29,12,tzinfo=timezone.utc)))
 def test_wrong_fixture_or_team_rejected(self):
    match={"id":"m_000123","time_utc":"2026-10-29T10:00:00Z",
          "status":"finished","score_home":1,"score_away":0,
          "home_team":{"id":"t_000009"},"away_team":{"id":"t_000002"}}
    p=("ESP","m_000123",match["time_utc"],"2026-10-29T07:00:00Z","t_000001","t_000002",{"1":0.5,"X":0.25,"2":0.25})
    with self.assertRaisesRegex(SettlementError,"TEAM_IDENTITY"):
        judge_match(match,p,observed=datetime(2026,10,29,14,tzinfo=timezone.utc))
 def test_empty_before_any_finished_never_reads_api(self):
    class Explode:
      class leagues:
        @staticmethod
        def list():raise AssertionError("no API should be called until game ended")
    with tempfile.TemporaryDirectory() as t:
      db=Path(t)/"m0.sqlite"
      commit_sqlite(db,fake_capture(),cutoff_utc=stamp(NOW),
                  raw_cipher_sha="a"*64,raw_chain_sha="b"*64)
      freeze(db,now=datetime.now(timezone.utc))
      r=settle(db,Explode(),now=NOW)
      self.assertEqual((r["newly_settled"],r["total_settled"]),(0,0))
      self.assertEqual(r["calibration_reviews"][0]["state"],"COLLECTING")
      self.assertEqual(r["calibration_reviews"][0]["needed_for_first_fit"],100)
      with sqlite3.connect(db) as c:
        self.assertEqual(c.execute("SELECT COUNT(*) FROM m0_shadow_settlements").fetchone()[0],0)
        self.assertEqual(c.execute("SELECT COUNT(*) FROM m0_shadow_1x2_forecasts").fetchone()[0],12)
 def test_no_automatic_activation(self):
    with tempfile.TemporaryDirectory() as t:
      db=Path(t)/"m0.sqlite"
      commit_sqlite(db,fake_capture(),cutoff_utc=stamp(NOW),
                  raw_cipher_sha="a"*64,raw_chain_sha="b"*64)
      freeze(db,now=datetime.now(timezone.utc))
      with sqlite3.connect(db) as c:
        c.executescript((Path(__file__).parents[1]/"migrations/004_m0_shadow_settlement_calibration.sql").read_text())
        self.assertEqual(review_calibration(c,now=NOW)[0]["production_approved"],False)
        self.assertEqual(c.execute("SELECT COUNT(*) FROM m0_shadow_calibration_audits").fetchone()[0],0)
if __name__=="__main__":unittest.main()
