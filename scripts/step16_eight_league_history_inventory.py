"""Read-only inventory of predecessor-season fixture structure for eight leagues.

A count above round-robin regular-season size is not automatically an error:
postseason fixtures/format changes must be classified by provider match ID
before history is promoted to any multi-league training matrix.
"""
import argparse,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SEASONS="data/pit_sidecar/m0_720_eight/2026-11-01/forecast/RECEIPT.json"
COUNTRIES=("ESP","ITA","GER","FRA","NED","BEL","TUR","POL")
class HistoryInventoryError(ValueError):pass
def audit(original):
    if (original.get("league_count")!=8 or set(original.get("countries",[]))!=set(COUNTRIES)
        or original.get("original_2026_27_Premier_League_TEST_accessed") is not False
        or original.get("mode")!="forecast"):
        raise HistoryInventoryError("NOT_ORIGINAL_8_LEAGUE_RESEARCH_RECEIPT")
    raw=original.get("season_shapes",{})
    prior={};unclassified=[]
    for c in COUNTRIES:
        old=raw.get(c+"/2025/2026")
        current=raw.get(c+"/2026/2027")
        if not isinstance(old,dict) or not isinstance(current,dict):
            raise HistoryInventoryError("EIGHT_LEAGUE_SEASONS_NOT_COMPLETE")
        n=old.get("teams")
        if type(n) is not int or not 2<=n<=30:raise HistoryInventoryError("TEAM_COUNT_INVALID")
        regular=n*(n-1)
        if (type(old.get("all")) is not int or old.get("finished")!=old.get("all")
            or old.get("not_started")!=0 or not isinstance(old.get("id_sha256"),str)
            or len(old["id_sha256"])!=64):
            raise HistoryInventoryError("PREVIOUS_SEASON_NOT_FINAL_OR_SOURCE_HASH_INVALID")
        extra=old["all"]-regular
        state=("NEEDS_MATCH_ID_PHASE_CLASSIFICATION" if extra!=0 else
               "COUNT_CONSISTENT_WITH_DOUBLE_ROUND_ROBIN_NOT_ID_PROOF")
        prior[c]={"prior_season":"2025/2026","teams":n,"all_finished":old["all"],
                  "double_round_robin_reference":regular,
                  "difference_from_regular_season":extra,"state":state,
                  "provider_fixture_ids_sha256":old["id_sha256"],
                  "current_season_teams":current["teams"]}
        if extra!=0:unclassified.append(c)
    return {"schema":"kb3-step16-eight-league-history-structural-readonly-v1",
       "source_class":"OBSERVED_2026_RETROSPECTIVE_NOT_HISTORIC_PIT",
       "source_scope":"8 leagues previous season 2025/26",
       "historical_season_stats":prior,
       "prior_finished_fixture_rows":sum(v["all_finished"] for v in prior.values()),
       "requires_per_fixture_classification":unclassified,
       "native_match_ids_from_source_payload_opened":False,
       "old_provider_first_published_known":False,
       "source_provider_calls":0,
       "training_allowed_on_unclassified_historical_seasons":False,
       "original_m0_and_test_untouched":True,
       "no_production_promotion":True}
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--source",default=str(ROOT/SEASONS))
    p.add_argument("--out",required=True)
    args=p.parse_args()
    path=Path(args.source);dest=Path(args.out)
    if dest.exists():raise HistoryInventoryError("OUTPUT_APPEND_ONLY")
    source=path.read_bytes()
    report=audit(json.loads(source))
    report["receipt_source_sha256"]=hashlib.sha256(source).hexdigest()
    dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_text(json.dumps(report,sort_keys=True,indent=2,ensure_ascii=False)+"\n")
    print(json.dumps({"historical_fixture_rows":report["prior_finished_fixture_rows"],
          "unclassified":report["requires_per_fixture_classification"],
          "no_api_calls":True,"no_training":True},sort_keys=True))
if __name__=="__main__":main()
