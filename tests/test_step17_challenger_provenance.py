"""Real signed CatBoost model + synthetic offline fixtures, strict archived-binary proof.

GitHub API and PitchAPI are never contacted by these tests.
"""
import io,json,sqlite3,tempfile,unittest,zipfile
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch
from test_step16_m0_720_eight_forward import fake_receipts,NOW
from src.kb3_step16_m0_720_eight_forward import (
    make_forecasts,freeze_sqlite,trained_params,settle_sqlite,stamp,hashobj)
from src.kb3_step16_m0_720_calibration import append_proofs
from src.kb3_step17_forward_challengers import Challengers,freeze_new_challengers
from src.kb3_step17_challenger_provenance import (
    audit_challengers,paired_settled_report,paired_settled_report_from_connection,
    _archived_challengers)
from src.kb3_pit_ledger import as_utc

class ChallengerProvenanceTests(unittest.TestCase):
 def setUp(self):
    self.tmp=tempfile.TemporaryDirectory()
    self.addCleanup(self.tmp.cleanup)
    self.db=Path(self.tmp.name)/"immutable.db"
    self.engine=Challengers()
    self.params,self.sha,self.manifest=trained_params()
    self.now=NOW
    sink=[]
    self.items,_,_=make_forecasts(fake_receipts(),cutoff=NOW,
                params=self.params,param_sha=self.sha,manifest_sha=self.manifest,
                challenger_engine=self.engine,challenger_sink=sink)
    ids=set()
    freeze_sqlite(self.db,self.items,param_sha=self.sha,manifest_sha=self.manifest,
                  now=NOW,new_frozen_ids=ids)
    freeze_new_challengers(self.db,sink,new_m0_ids=ids)
    self.blob=self.zip(self.db.read_bytes())
    self.server=NOW+timedelta(minutes=1)
    proofs=[]
    for i,p in enumerate(self.items):
        info={"forecast_id":p["forecast_sha256"],
              "model":"M0_ELO_POISSON_RESEARCH_720TRAIN_V1",
              "github_event_id":"actions-artifact:55555",
              "github_commit_sha":"a"*40,
              "github_server_event_utc":stamp(self.server),
              "original_forecast_sha256":p["forecast_sha256"],
              "source":"GITHUB_SERVER_ACTIONS_ARTIFACT_PLUS_EXACT_DB_BYTES",
              "audit_utc":stamp(self.server+timedelta(minutes=1))}
        proofs.append(info|{"proof_id":hashobj(info)})
    append_proofs(self.db,proofs,now=self.server+timedelta(minutes=1))
 def zip(self,contents):
    buf=io.BytesIO()
    with zipfile.ZipFile(buf,"w",zipfile.ZIP_DEFLATED) as z:
        z.writestr("forward_m0_720_eight/kb3_forward_eight.sqlite",contents)
    return buf.getvalue()
 def context(self,created=None,blob=None):
    created=created or self.server
    meta={"id":55555,"name":"KB3_STEP16_M0_720_EIGHT_LEAGUE_FREEZE_SETTLEMENT_SOURCE_EVIDENCE",
          "expired":False,"created_at":stamp(created),
          "archive_download_url":"https://api.github.com/test/zip"}
    return patch("src.kb3_step17_challenger_provenance._gh_json",
                 return_value=meta),patch(
                 "src.kb3_step17_challenger_provenance._gh_artifact_zip",
                 return_value=blob if blob is not None else self.blob)
 def test_128_exact_original_challenger_rows_host_attested_no_future_label(self):
    original=_archived_challengers(self.blob)
    self.assertEqual(len(original),128)
    x,y=self.context()
    with x,y:
        audit=audit_challengers(self.db,token="SYNTHETIC_TOKEN",
                           now=self.server+timedelta(minutes=3))
    self.assertEqual(audit["new_github_proofs"],128)
    self.assertEqual(audit["errors"],0)
    self.assertEqual(audit["total_verified_challenger_forecasts"],128)
    empty=paired_settled_report(self.db)
    self.assertEqual(empty["unique_fixtures"],0)
    self.assertFalse(empty["winner_auto_selected"])
    # A genuine 90-minute label only after game has ended+3h.
    fixture=self.items[0]
    label={"id":fixture["provider_match_id"],
       "time_utc":fixture["kickoff_utc"],"home_team":{"id":fixture["home_team_id"]},
       "away_team":{"id":fixture["away_team_id"]},
       "status":"finished","score_home":2,"score_away":1}
    settled=settle_sqlite(self.db,{
        (fixture["league_country"],fixture["provider_match_id"]):label},
        observed_at=NOW+timedelta(days=5),source_chain_sha="b"*64)
    self.assertEqual(settled["new_settlements"],1)
    after=paired_settled_report(self.db)
    self.assertEqual(after["unique_fixtures"],1)
    self.assertEqual(after["full_five_common_fixtures"],0)
    pair=after["fair_same_game_pairwise"]["M0_ELO_POISSON_720TRAIN__vs__CATBOOST_NO_XG"]
    self.assertEqual(pair["common_n"],1)
    self.assertEqual(pair["deltas"]["log_loss"]["status"],
                     "INSUFFICIENT_INDEPENDENT_WEEKS")
    self.assertFalse(after["enough_for_formal_step17"])
    with sqlite3.connect(self.db.as_uri()+"?mode=ro",uri=True) as c:
        from_readonly = paired_settled_report_from_connection(c)
    self.assertEqual(from_readonly,after)
    trio=from_readonly["exact_three_engine_comparison"]
    self.assertEqual([w["common_n"] for w in trio["per_iso_week"].values()],[1])
    x,y=self.context()
    with x,y:
        repeat=audit_challengers(self.db,token="SYNTHETIC_TOKEN",
                           now=NOW+timedelta(days=6))
    self.assertEqual(repeat["new_github_proofs"],0)
    with sqlite3.connect(self.db) as c:
        with self.assertRaises(sqlite3.IntegrityError):
            c.execute("DELETE FROM step17_challenger_host_proofs")
        c.execute("DROP TRIGGER step17_proofs_no_update")
        c.execute("UPDATE step17_challenger_host_proofs SET github_artifact_id='wrong-artifact'")
    with sqlite3.connect(self.db.as_uri()+"?mode=ro",uri=True) as c:
        with self.assertRaisesRegex(ValueError,"STEP17_PAIR_HOST_PROOF_CHANGED"):
            paired_settled_report_from_connection(c)
 def test_no_artifact_or_invalid_binary_never_proves(self):
    # Only real exact bytes can prove. An archive with the original M0 table
    # but no challenger rows is not a valid challenger proof.
    with sqlite3.connect(self.db) as conn:
        rows=conn.execute("SELECT COUNT(*) FROM step17_frozen_challengers").fetchone()[0]
    self.assertEqual(rows,128)
    broken=self.zip(b"not a sqlite file")
    x,y=self.context(blob=broken)
    with x,y:
        result=audit_challengers(self.db,token="SYNTHETIC_TOKEN",
                              now=NOW+timedelta(days=3))
    self.assertEqual(result["new_github_proofs"],0)
    self.assertGreater(result["errors"],0)
    result=audit_challengers(self.db,token="",now=NOW+timedelta(days=3))
    self.assertEqual(result["new_github_proofs"],0)
 def test_host_upload_after_start_does_not_certify_prematch(self):
    latest=max(as_utc(p["kickoff_utc"]) for p in self.items)+timedelta(hours=1)
    x,y=self.context(created=latest)
    with x,y:
        result=audit_challengers(self.db,token="SYNTHETIC_TOKEN",
                                  now=latest+timedelta(minutes=1))
    self.assertEqual(result["new_github_proofs"],0)
    self.assertEqual(result["total_verified_challenger_forecasts"],0)

if __name__=="__main__":unittest.main()
