"""Negative tests for complete historic public Elo cutoff and xG clocks."""
import csv,io,json,unittest
from datetime import datetime,timedelta,timezone
from src.kb3_step14_elo_rollover_xg_clock_discovery import (
    SEARCHES,ELO_CUTOFF,DiscoveryError,git_candidates,matched_push,
    inspect_ft,inspect_xg,original_season_retention,
    prepare_2023_full_ft_rollover,scan
)

def synthetic_380():
    buf=io.StringIO()
    writer=csv.DictWriter(buf,fieldnames=["id","team_h","team_a","team_h_score","team_a_score","kickoff_time","finished"])
    writer.writeheader()
    k=0
    for h in range(1,21):
        for a in range(1,21):
            if h==a:continue
            when=datetime(2023,8,12,tzinfo=timezone.utc)+timedelta(minutes=90*k)
            writer.writerow(dict(id=str(k),team_h=str(h),team_a=str(a),
                team_h_score="1.0",team_a_score="0.0",
                kickoff_time=when.isoformat().replace("+00:00","Z"),
                finished="True"))
            k+=1
    return buf.getvalue().encode("utf8")

class SeasonBoundaryTests(unittest.TestCase):
    def test_2024_25_first_kickoff_is_documented(self):
        self.assertEqual(ELO_CUTOFF,"2024-08-16T19:00:00Z")
    def test_eight_five_original_retention_formula(self):
        self.assertEqual(original_season_retention(1600),1585)
        self.assertEqual(original_season_retention(1400),1415)
        self.assertEqual(original_season_retention(1500),1500)
    def test_reject_nonfinite_elo(self):
        with self.assertRaises(DiscoveryError):
            original_season_retention(float("nan"))
    def test_unverified_published_at_no_full_elo_proof(self):
        data=synthetic_380()
        proof=inspect_ft(data,None)
        self.assertEqual(proof["old_completed_FT"],380)
        self.assertFalse(proof["full_380_FT_public_asof_2024_25_opening"])
    def test_full_380_public_ft_rollover_only_with_independent_time(self):
        b=synthetic_380()
        p=prepare_2023_full_ft_rollover(b,"2024-06-15T14:00:00Z")
        self.assertEqual(p["full_public_2023_24_results_replayed"],380)
        self.assertEqual(p["rated_full_2023_24_team_count"],20)
        self.assertFalse(p["actual_2024_25_native_elo_feature_pit_proven"])
        self.assertNotIn("ratings",p)
    def test_clock_after_2024_opening_fails_closed(self):
        with self.assertRaises(DiscoveryError):
            inspect_ft(synthetic_380(),"2024-08-20T08:00:00Z")
    def test_commit_date_never_claims_publication(self):
        rows=[{"sha":"a"*40,"commit":{"committer":{"date":"2024-06-01T10:00:00Z"}}},
              {"sha":"b"*40,"commit":{"committer":{"date":"2024-08-01T11:00:00Z"}}}]
        selected=git_candidates(rows,SEARCHES[0])
        self.assertEqual(len(selected),2)
        self.assertTrue(all("git_committer_search_hint_only" in s for s in selected))
        self.assertNotIn("independent_source_publication_utc",selected[0])
    def test_unavailable_gharchive_remains_unproven(self):
        r=matched_push("a"*40,"2024-06-01T10:00:00Z",
                       lambda hour:{"status":"READ_UNAVAILABLE","events":[]})
        self.assertIsNone(r["independent_source_publication_utc"])
    def test_foreign_sha_or_ref_rejected(self):
        r=matched_push("a"*40,"2024-06-01T10:00:00Z",
                       lambda hour:{"status":"READ_OK","events":[{
                         "repository":"vaastav/Fantasy-Premier-League",
                         "ref":"refs/heads/private",
                         "shas":["a"*40],
                         "server_created_at_utc":"2024-06-01T10:15:00Z","event_id":"12"}]})
        self.assertFalse(r["exact_sha_published_confirmed"])
    def test_exact_independent_server_push(self):
        r=matched_push("a"*40,"2024-06-01T10:00:00Z",
                       lambda hour:{"status":"READ_OK","events":[{
                         "repository":"vaastav/Fantasy-Premier-League",
                         "ref":"refs/heads/master",
                         "shas":["a"*40],
                         "server_created_at_utc":"2024-06-01T10:15:00Z","event_id":"12"}]})
        self.assertTrue(r["exact_sha_published_confirmed"])
    def test_old_player_xg_never_same_as_original_pitchapi_team_xg(self):
        x=inspect_xg(b"element,fixture,team,expected_goals\n1,123,2,0.1\n","2024-06-01T10:15:00Z")
        self.assertTrue(x["old_fpl_row_has_player_expected_goals_column"])
        self.assertFalse(x["native_pitchapi_team_match_xg_values_equivalence_proven"])
    def test_no_commit_eligible_is_not_380_proven(self):
        opt=SEARCHES[0]
        out=scan(opt,fetcher=lambda _:b"[]",
                 clock_reader=lambda _:{"status":"READ_OK","events":[]})
        self.assertEqual(out["state"],"NO_HISTORICAL_FILE_COMMIT_IN_SEARCH_WINDOW")
        self.assertFalse(out["old_blob_publication_verified"])

if __name__=="__main__":unittest.main()
