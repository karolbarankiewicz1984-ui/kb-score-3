import unittest
from src.kb3_step16_phase_validation_research import audit,classify
from src.kb3_step16_m0_720_eight_forward import hashobj
class PhaseTests(unittest.TestCase):
 def test_missing_new_data_pending(self):
    self.assertEqual(audit({})["status"],"PENDING_NEXT_REAL_FORECAST")
 def test_label_hint_is_not_approval(self):
    self.assertEqual(classify({"round":"Regular Season"}),"REGULAR_HINT_REQUIRES_REVIEW")
    self.assertEqual(classify({"stage":"Relegation play-offs"}),"NONREGULAR_HINT_REQUIRES_REVIEW")
    self.assertEqual(classify({"round":"regular","stage":"playoffs"}),"CONFLICTING_PROVIDER_HINTS")
 def test_source_ids_and_raw_hint_are_never_training_approval(self):
    data={};shapes={}
    for c,n,teams in (("NED",309,18),("BEL",313,16)):
      ids=["m_"+c+str(i) for i in range(n)]
      data[c]={"native_fixture_rows":n,"any_phase_pass_or_training_approval":False,
               "fixture_rows":[{"fixture_id":id,"formal_phase_reviewed":False,
                   "provider_stage_hints":{k:None for k in
                      ("round","stage","phase","competition_phase")}} for id in ids]}
      shapes[c+"/2025/2026"]={"all":n,"teams":teams,"id_sha256":hashobj(sorted(ids))}
    res=audit({"mode":"forecast","original_2026_27_Premier_League_TEST_accessed":False,
               "ned_bel_historical_phase_native_id_review":data,"season_shapes":shapes})
    self.assertEqual(res["results"]["BEL"]["extra_count_is_not_phase_proof"],73)
    self.assertFalse(res["training_allowed"])
    data["NED"]["fixture_rows"][0]["fixture_id"]="m_BAD"
    with self.assertRaises(ValueError):audit({"mode":"forecast",
      "original_2026_27_Premier_League_TEST_accessed":False,
      "ned_bel_historical_phase_native_id_review":data,"season_shapes":shapes})
if __name__=="__main__":unittest.main()
