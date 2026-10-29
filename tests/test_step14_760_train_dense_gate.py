import unittest
from scripts.step14_2025_dense_25_historical_witnesses import (
    NEW,SOURCE_LIST)
from scripts.step14_train_760_dense_validation_1140_matrix import (
    _team,_asof_values,_best_public_candidate,RecoverError)
from scripts.step14_train_validation_final_m1_fit_gate import evaluate,GateReject
from scripts.step14_fpl_core_2025_independent_asof import _utc
from src.kb3_step14_bridge import EXPECTED_FEATURES,EXPECTED_MISSING

class TrainDensePITIsolationTests(unittest.TestCase):
    def test_twentyfive_independently_pinned_historic_sources(self):
        self.assertEqual(len(NEW),11)
        self.assertEqual(len(SOURCE_LIST),25)
        self.assertEqual(len({r[0] for r in SOURCE_LIST}),25)
        self.assertTrue(all(_utc(x[3])<_utc("2026-06-01T00:00:00Z") for x in SOURCE_LIST))
    def test_fixed_team_aliases_are_not_fuzzy(self):
        self.assertEqual(_team("Luton"),"luton town")
        self.assertEqual(_team("Sheffield Utd"),"sheffield united")
        self.assertEqual(_team("Ipswich"),"ipswich town")
        self.assertEqual(_team("Newcastle"),"newcastle united")
        self.assertEqual(_team("Man Utd"),"manchester united")
    def test_original_fpl_nonxg_fields_must_not_fake_xg_zero(self):
        v={k:None for k in EXPECTED_FEATURES}
        m={k:None for k in EXPECTED_MISSING}
        v["home_all_5_xg_n"]=0
        v["away_all_5_xg_avg"]=1.9
        m["home_all_5_xg"]=False
        row={"research_features_not_native_PitchAPI":v,
             "research_missing_flags_not_native_PitchAPI":m}
        src={"witness":"2024-05-01T00:00:00Z","commit":"old"}
        values,flags=_asof_values({},[],src,row)
        self.assertIsNone(values["home_all_5_xg_n"])
        self.assertIsNone(values["away_all_5_xg_avg"])
        self.assertIsNone(flags["home_all_5_xg"])
        self.assertIsNone(values["home_elo"])
    def test_trusted_source_must_contain_target_in_old_unplayed_schedule(self):
        t={"home":"a","away":"b","ko":_utc("2024-05-10T15:00:00Z"),
           "key":("a","b",_utc("2024-05-10T15:00:00Z").isoformat())}
        src={"witness":"2024-05-09T10:00:00Z","schedules":{},
             "past":{},"commit":"old"}
        self.assertIsNone(_best_public_candidate(t,[t],[src]))
    def test_fit_gate_rejects_2026_retro_elo_as_native_public(self):
        with self.assertRaisesRegex(GateReject,"GATE_SOURCE_SHA"):
            evaluate({"schema":"wrong"},[],b"fake")
    def test_fit_gate_rejects_2026_27_test_injected(self):
        import hashlib
        with self.assertRaisesRegex(GateReject,"NOT_ORIGINAL_1140"):
            evaluate({"schema":"kb3-step14-full-760-train-plus-dense-validation-public-PIT-research-159-field-v1",
                      "matrix_gzip_sha256":hashlib.sha256(b"test").hexdigest()},
                     [],b"test")

if __name__=="__main__":
    unittest.main()
