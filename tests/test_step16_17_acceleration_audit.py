"""Strict offline audit acceptance. No real API or M0 fitting."""
import sqlite3,tempfile,unittest
from datetime import datetime,timedelta,timezone
from pathlib import Path
from scripts.step16_17_acceleration_audit import audit_m0,audit_history,audit_xg,open_readonly
AT=datetime(2026,11,1,20,tzinfo=timezone.utc)
class AuditTests(unittest.TestCase):
 def test_host_proof_required_and_no_fake_settlement(self):
  with tempfile.TemporaryDirectory() as t:
   db=Path(t)/"m0.sqlite"
   with sqlite3.connect(db) as c:
    c.executescript("""
    CREATE TABLE model_meta(model text,parameters_sha256 text,status text);
    CREATE TABLE forecasts(id text,league text,kickoff_utc text);
    CREATE TABLE settlements(forecast_id text);
    CREATE TABLE m0720_github_push_proofs(forecast_id text,github_server_event_utc text);
    CREATE TABLE step17_frozen_challengers(challenger_sha256 text,source_m0_forecast_sha256 text);
    CREATE TABLE step17_challenger_host_proofs(challenger_sha256 text);
    """)
    c.execute("INSERT INTO model_meta VALUES(?,?,?)",("M0_ELO_POISSON_RESEARCH_720TRAIN_V1","55310f0e1dd3842e6d876069ef21b1380901b3a6cc6884cf6ec6ea351a5812d1","RESEARCH_ONLY_NOT_APPROVED"))
    c.execute("INSERT INTO forecasts VALUES(?,?,?)",("x","POL","2026-11-02T20:00:00Z"))
   with open_readonly(db) as c:
    r=audit_m0(c,now=AT)
   self.assertEqual(r["counts"]["missing_github_host_proof"],1)
   self.assertEqual(r["counts"]["all_settlements"],0)
   with sqlite3.connect(db) as c:
    c.execute("INSERT INTO m0720_github_push_proofs VALUES(?,?)",("x","2026-11-02T18:29:00Z"))
   with open_readonly(db) as c:
    self.assertEqual(audit_m0(c,now=AT)["counts"]["host_attested_future_awaiting_match"],1)
 def test_proof_too_late_rejected(self):
  with tempfile.TemporaryDirectory() as t:
   p=Path(t)/"db"
   with sqlite3.connect(p) as c:
    c.executescript("""
    CREATE TABLE model_meta(model text,parameters_sha256 text,status text);
    CREATE TABLE forecasts(id text,league text,kickoff_utc text);
    CREATE TABLE settlements(forecast_id text);
    CREATE TABLE m0720_github_push_proofs(forecast_id text,github_server_event_utc text);
    """)
    c.execute("INSERT INTO model_meta VALUES(?,?,?)",("M0_ELO_POISSON_RESEARCH_720TRAIN_V1","55310f0e1dd3842e6d876069ef21b1380901b3a6cc6884cf6ec6ea351a5812d1","RESEARCH_ONLY_NOT_APPROVED"))
    c.execute("INSERT INTO forecasts VALUES('x','POL','2026-11-02T20:00:00Z')")
    c.execute("INSERT INTO m0720_github_push_proofs VALUES('x','2026-11-02T19:30:00Z')")
   with open_readonly(p) as c:
    with self.assertRaisesRegex(ValueError,"TOO_LATE"):audit_m0(c,now=AT)
 def test_history_counts_not_phase_proof(self):
  eight=("ESP","ITA","GER","FRA","NED","BEL","TUR","POL")
  shapes={}
  for c in eight:
   n=16 if c=="BEL" else 18
   total=n*(n-1)+(73 if c=="BEL" else 3 if c=="NED" else 0)
   shapes[c+"/2025/2026"]={"teams":n,"all":total,"finished":total,"not_started":0,"id_sha256":"a"*64}
  r=audit_history({"mode":"forecast","league_count":8,"countries":list(eight),
      "original_2026_27_Premier_League_TEST_accessed":False,
      "season_shapes":shapes,"coverage":{x:4 for x in eight},"network_calls":17})
  self.assertTrue(r["country_counts"]["BEL"]["needs_native_fixture_id_phase_review"])
  self.assertTrue(r["country_counts"]["NED"]["needs_native_fixture_id_phase_review"])
  self.assertFalse(r["new_multi_league_training_allowed"])
 def test_xg_requires_actual_db_and_33_limit(self):
  with tempfile.TemporaryDirectory() as t:
   p=Path(t)/"db"
   with sqlite3.connect(p) as c:
    c.execute("CREATE TABLE observed_native_xg(source_published_at_utc text)")
    c.execute("INSERT INTO observed_native_xg VALUES(NULL)")
   with open_readonly(p) as c:
    a=audit_xg(c,{"cumulative_verified_xg_matches":1,"hard_limit_calls":33,
       "network_calls":33,"future_form5_coverage":{"complete_last5_both_team_xg":0,
         "future_targets_scanned":5,"missing_by_country":{"ESP":5}}})
   self.assertEqual(a["provider_calls_if_16_pairs"],49)
   self.assertIsNone(a["provider_subscription_allows_49_calls"])
if __name__=="__main__":unittest.main()
