"""Real frozen CBM (sha256) + native feature-identity, no-label challenger tests.

Fixtures are offline synthetic; model binary is the ACTUAL 720-TRAIN .cbm
already in private repo. No new fit, API request, or protected English TEST.
"""
import copy,sqlite3,tempfile,unittest
from pathlib import Path
from test_step16_m0_720_eight_forward import fake_receipts,NOW
from src.kb3_step16_m0_720_eight_forward import (
    make_forecasts,freeze_sqlite,trained_params,Research720Error)
from src.kb3_step17_forward_challengers import (
    Challengers,freeze_new_challengers,elo_only_probabilities,
    vector_of_frozen_features,ELO,CAT,CBM_SHA)
class Step17ForwardChallengerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine=Challengers()
        cls.params,cls.sha,cls.manifest=trained_params()
    def test_source_720_actual_catboost_binary_85_features_frozen(self):
        self.assertEqual(self.engine.cbm_sha,CBM_SHA)
        self.assertEqual(len(self.engine.names),85)
        self.assertEqual(set(self.engine.class_order),{"1","X","2"})
        self.assertFalse(any("xg" in n for n in self.engine.names))
    def test_elo_points_are_not_treated_as_win_probability(self):
        for h,a in ((1500,1500),(1600,1450),(1450,1600)):
            p=elo_only_probabilities(h,a,self.params)
            expected=(1+10**((a-h-self.params.elo_home_advantage)/
                             self.params.elo_scale))**-1
            self.assertAlmostEqual(p["1"]+p["X"]/2,expected,places=12)
            self.assertAlmostEqual(sum(p.values()),1,places=12)
            self.assertTrue(all(x>0 for x in p.values()))
    def test_real_pre_match_twins_atomic_only_new_m0(self):
        sink=[]
        rows,per,shapes=make_forecasts(fake_receipts(),cutoff=NOW,
              params=self.params,param_sha=self.sha,manifest_sha=self.manifest,
              challenger_engine=self.engine,challenger_sink=sink)
        self.assertEqual(len(rows),64)
        self.assertEqual(len(sink),128)
        self.assertEqual(sum(r["engine"]=="ELO_ONLY" for r in sink),64)
        self.assertEqual(sum(r["engine"]=="CATBOOST_NO_XG" for r in sink),64)
        for row in sink:
            parent=next(p for p in rows if p["forecast_sha256"]==
                        row["source_m0_forecast_sha256"])
            self.assertEqual((row["league_country"],row["provider_match_id"],
                              row["kickoff_utc"],row["frozen_at_utc"],
                              row["feature_sha256"]),
                             (parent["league_country"],parent["provider_match_id"],
                              parent["kickoff_utc"],parent["generated_at_utc"],
                              parent["feature_sha256"]))
            self.assertEqual(set(row["p_1x2"]),{"1","X","2"})
            self.assertAlmostEqual(sum(row["p_1x2"].values()),1,places=10)
            self.assertFalse(row["target_result_used"])
            self.assertFalse(row["production_approved"])
        with tempfile.TemporaryDirectory() as td:
            db=Path(td)/"independent.sqlite"
            fresh=set()
            n,total=freeze_sqlite(db,rows,param_sha=self.sha,
                  manifest_sha=self.manifest,now=NOW,new_frozen_ids=fresh)
            self.assertEqual((n,total,len(fresh)),(64,64,64))
            outcome=freeze_new_challengers(db,sink,new_m0_ids=fresh)
            self.assertEqual(outcome["new_challengers"],128)
            self.assertEqual(outcome["new_common_fixture_pairs"],64)
            with sqlite3.connect(db) as c:
                self.assertEqual(c.execute("SELECT COUNT(*) FROM forecasts").fetchone()[0],64)
                self.assertEqual(c.execute("SELECT COUNT(*) FROM step17_frozen_challengers").fetchone()[0],128)
                with self.assertRaises(sqlite3.IntegrityError):
                    c.execute("UPDATE step17_frozen_challengers SET model_version='new'")
                with self.assertRaises(sqlite3.IntegrityError):
                    c.execute("DELETE FROM step17_frozen_challengers")
            # Replaying already frozen M0 matches does not backfill/recompute
            # challenger forecasts post hoc. Existing M0 archive stays unchanged.
            again=set()
            a,b=freeze_sqlite(db,rows,param_sha=self.sha,
                  manifest_sha=self.manifest,now=NOW,new_frozen_ids=again)
            self.assertEqual((a,b,len(again)),(0,64,0))
            repeat=freeze_new_challengers(db,sink,new_m0_ids=again)
            self.assertEqual(repeat["new_challengers"],0)
            self.assertEqual(repeat["old_m0_not_backfilled"],128)
            self.assertEqual(repeat["total_challengers"],128)
    def test_refuse_tampered_feature_hash_and_lookahead(self):
        sink=[]
        rows,_,_=make_forecasts(fake_receipts(),cutoff=NOW,
              params=self.params,param_sha=self.sha,manifest_sha=self.manifest,
              challenger_engine=self.engine,challenger_sink=sink)
        tampered=copy.deepcopy(rows[0])
        tampered["params_sha256"]="0"*64
        with self.assertRaisesRegex(Research720Error,"NO_SAME_MODEL"):
            self.engine.records({"sha256":tampered["feature_sha256"]},tampered)
        # Validate real original SHA, no chance to silently alter challenger P.
        with tempfile.TemporaryDirectory() as td:
            db=Path(td)/"immutable.sqlite"
            fresh=set()
            freeze_sqlite(db,rows,param_sha=self.sha,
                 manifest_sha=self.manifest,now=NOW,new_frozen_ids=fresh)
            bad=copy.deepcopy(sink)
            bad[0]["p_1x2"]={"1":0.9,"X":0.05,"2":0.05}
            with self.assertRaisesRegex(Research720Error,"IMMUTABLE_SHA_INVALID"):
                freeze_new_challengers(db,bad,new_m0_ids=fresh)
if __name__=="__main__":unittest.main()
