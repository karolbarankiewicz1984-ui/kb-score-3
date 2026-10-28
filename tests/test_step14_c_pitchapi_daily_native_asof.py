import tempfile,unittest
from datetime import datetime,timezone,timedelta
from pathlib import Path
from scripts.step14_c_pitchapi_daily_native_asof_archive import (
    select_targets_and_predecessors,capture,CaptureError,BUDGET,MAX_PRIOR)
NOW=datetime(2026,10,28,18,0,tzinfo=timezone.utc)
def row(mid,when,status,h="t_aaaaaa",a="t_bbbbbb",score=None):
    return {"id":mid,"time_utc":when,"status":status,
        "home_team":{"id":h},"away_team":{"id":a},
        "score_home":score,"score_away":score}
class DailyAsOf(unittest.TestCase):
 def fixtures(self):
    return [
     row("m_aaaaaa","2026-10-20T18:00:00Z","finished",score=1),
     row("m_bbbbbb","2026-10-25T18:00:00Z","finished",score=2),
     row("m_cccccc","2026-10-28T17:30:00Z","finished",score=1),
     row("m_dddddd","2026-10-31T17:00:00Z","scheduled"),
     row("m_eeeeee","2026-11-01T16:00:00Z","not_started")]
 def test_only_future_target_and_true_prior_three_hour(self):
    targets,old=select_targets_and_predecessors(self.fixtures(),NOW)
    self.assertEqual([x["id"] for x in targets],["m_dddddd","m_eeeeee"])
    self.assertEqual([x["id"] for x in old],["m_bbbbbb","m_aaaaaa"])
 def test_future_target_with_leaked_score_rejected(self):
    rows=self.fixtures();rows[-1]["score_home"]=3
    with self.assertRaisesRegex(CaptureError,"FUTURE_HAS_RESULT"):
        select_targets_and_predecessors(rows,NOW)
 def test_no_future_is_empty_fail_closed(self):
    t,p=select_targets_and_predecessors(self.fixtures()[:2],NOW)
    self.assertEqual((t,p),([],[]))
 def test_no_secrets_no_work_without_key(self):
    with tempfile.TemporaryDirectory() as d:
        with self.assertRaisesRegex(CaptureError,"KEY_MISSING"):
            capture(dest=Path(d)/"daily",public_key="fake",key="")
 def test_budget_constant_no_owner_pem(self):
    self.assertEqual((BUDGET,MAX_PRIOR),(6,2))
 def test_no_future_match_before_now(self):
    a=[row("m_qwerty","2026-10-27T18:00:00Z","scheduled"),
       row("m_asdfgh","2026-10-28T19:00:00Z","scheduled")]
    f,_=select_targets_and_predecessors(a,NOW)
    self.assertEqual(len(f),1)
 def test_wrong_same_team_rejected(self):
    x=row("m_asdfgh","2026-10-31T18:00:00Z","scheduled",
       h="t_aaaaaa",a="t_aaaaaa")
    with self.assertRaisesRegex(CaptureError,"NATIVE_SAME_TEAM"):
        select_targets_and_predecessors([x],NOW)
if __name__=="__main__":unittest.main()
