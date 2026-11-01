import unittest
from scripts.step16_eight_league_history_inventory import audit,HistoryInventoryError,COUNTRIES
class EightLeagueHistoryStructure(unittest.TestCase):
    def source(self):
        sh={}
        for c in COUNTRIES:
            sh[c+"/2025/2026"]={"teams":18,"all":306,"finished":306,
                    "not_started":0,"id_sha256":"a"*64}
            sh[c+"/2026/2027"]={"teams":18,"all":306,"finished":100,
                    "not_started":206,"id_sha256":"b"*64}
        return {"league_count":8,"countries":list(COUNTRIES),"mode":"forecast",
                "original_2026_27_Premier_League_TEST_accessed":False,
                "season_shapes":sh}
    def test_regular_and_postseason_separated(self):
        obj=self.source()
        obj["season_shapes"]["NED/2025/2026"]["all"]=309
        obj["season_shapes"]["NED/2025/2026"]["finished"]=309
        obj["season_shapes"]["BEL/2025/2026"]={"teams":16,"all":313,
            "finished":313,"not_started":0,"id_sha256":"c"*64}
        result=audit(obj)
        self.assertEqual(result["requires_per_fixture_classification"],["NED","BEL"])
        self.assertEqual(result["historical_season_stats"]["NED"]["difference_from_regular_season"],3)
        self.assertEqual(result["historical_season_stats"]["BEL"]["difference_from_regular_season"],73)
        self.assertFalse(result["training_allowed_on_unclassified_historical_seasons"])
    def test_incomplete_prior_fails(self):
        x=self.source();x["season_shapes"]["ESP/2025/2026"]["finished"]=100
        with self.assertRaises(HistoryInventoryError):audit(x)
    def test_protected_test_fails(self):
        x=self.source();x["original_2026_27_Premier_League_TEST_accessed"]=True
        with self.assertRaises(HistoryInventoryError):audit(x)
if __name__=="__main__":unittest.main()
