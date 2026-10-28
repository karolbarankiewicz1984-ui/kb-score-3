"""Step14: independently clocked, exact fixture/side historical xG gate.

FPL/Opta *player* expected_goals is an alternative observable source, not
the original PitchAPI team-match xG feature; do NOT silently substitute.
Frozen old raw bytes and independently attested PushEvent are mandatory.
Research-only counts, no player IDs, source values, native IDs, TEST or model fit.
"""
from __future__ import annotations
import csv,io,json,math
from collections import defaultdict,Counter
from datetime import timedelta
from hashlib import sha256
from pathlib import Path
from src.kb3_step14_multiseason_pit import fetch,utc
from src.kb3_step14_owner_elo_2023_to_2024 import FULL_2023,check_pinned_public_evidence

ROOT=Path(__file__).resolve().parents[1]
FULL_MERGED_SHA="e9c09c8856f1c86b4f920f46ddd5033af83409439dfda53be925df2a3e7c8a9e"
FULL_MERGED_PATH="data/2023-24/gws/merged_gw.csv"
SCHEMA="kb3-step14-xg-4gates-historical-player-source-only-v1"
METHOD="FPL_OPTA_PLAYER_SHOT_XG_SUM_BY_ORIGINAL_FIXTURE_SIDE"
REQUIRED_PLAYER={"fixture","opponent_team","was_home","team","expected_goals","element"}
REQUIRED_FIXTURE={"id","team_h","team_a","kickoff_time","finished"}

class XGFourGateError(ValueError):pass

def original_proof():
    p=ROOT/"data/audits/STEP14_FPL_2023_FULL_380_GHARCHIVE_PUSH_AND_XG_2026-10-28.json"
    report=json.loads(p.read_text(encoding="utf8"))
    check_pinned_public_evidence(report)
    return report

def valid_num(raw):
    if raw is None or not isinstance(raw,str) or not raw.strip():
        raise XGFourGateError("MISSING_PLAYER_XG")
    try:x=float(raw)
    except ValueError as exc:raise XGFourGateError("BAD_PLAYER_XG") from exc
    if not math.isfinite(x) or x<0 or x>20:
        raise XGFourGateError("BAD_PLAYER_XG")
    return x

def strict_id(x):
    if not isinstance(x,str) or not x.isdecimal():
        raise XGFourGateError("INVALID_FPL_ID")
    n=int(x)
    if n<=0:raise XGFourGateError("INVALID_FPL_ID")
    return n

def strict_side(x):
    if x=="True":return True
    if x=="False":return False
    raise XGFourGateError("UNKNOWN_FPL_VENUE_SIDE")

def extract_public_xg(fixtures_raw,players_raw,*,published_at,pinned_fixture_sha,pinned_player_sha,
                      require_full_grid=True):
    """Only old source files, never original RSA. Return research only *in RAM*.

    In-memory returned side-level numerics MUST NOT enter a model feature table;
    the calling audit serializes counts only. All joins are exact FPL
    fixture+side+opponent ID+stable team name, not fuzzy team string matching.
    """
    if sha256(fixtures_raw).hexdigest()!=pinned_fixture_sha:
        raise XGFourGateError("FIXTURE_ORIGINAL_BYTES_HASH_MISMATCH")
    if sha256(players_raw).hexdigest()!=pinned_player_sha:
        raise XGFourGateError("XG_ORIGINAL_BYTES_HASH_MISMATCH")
    push=utc(published_at)
    try:
        fixtures=list(csv.DictReader(io.StringIO(fixtures_raw.decode("utf-8-sig"))))
    except (UnicodeError,csv.Error) as exc:raise XGFourGateError("FIXTURE_CSV_PARSE") from exc
    if require_full_grid and len(fixtures)!=380:
        raise XGFourGateError("ORIGINAL_380_GRID_MISSING")
    fixture_index={};all_teams=set();teams_by_id={}
    for r in fixtures:
        if not REQUIRED_FIXTURE.issubset(r):
            raise XGFourGateError("FIXTURE_FIELDS_INCOMPLETE")
        fid=strict_id(r["id"])
        home,away=strict_id(r["team_h"]),strict_id(r["team_a"])
        if fid in fixture_index or home==away:
            raise XGFourGateError("DUPLICATE_OR_INVALID_FIXTURE")
        ko=utc(r["kickoff_time"])
        if r["finished"]=="True" and not (ko+timedelta(hours=3)<push):
            raise XGFourGateError("HISTORICAL_XG_FIXTURE_NOT_FINISHED_BEFORE_PUBLICATION")
        fixture_index[fid]={"home":home,"away":away,"kickoff":ko,"finished":r["finished"]}
        all_teams.update((home,away))
    if require_full_grid and len(all_teams)!=20:
        raise XGFourGateError("EXPECTED_20_FPL_TEAMS")
    reader=csv.DictReader(io.StringIO(players_raw.decode("utf-8-sig")))
    if not REQUIRED_PLAYER.issubset(reader.fieldnames or []):
        raise XGFourGateError("NOT_PLAYER_EXPECTED_GOALS_SCHEMA")
    side_totals=defaultdict(float);players_per_side=Counter()
    dedup=set();duplicates=0;first_unknown=None;rows=0
    for r in reader:
        rows+=1
        fid=strict_id(r["fixture"])
        fixture=fixture_index.get(fid)
        if fixture is None:
            raise XGFourGateError("PLAYER_XG_UNMATCHED_FIXTURE")
        if fixture["finished"]!="True":
            raise XGFourGateError("PLAYER_XG_ON_NOT_COMPLETED_HISTORICAL_FIXTURE")
        was_home=strict_side(r["was_home"])
        tid=fixture["home"] if was_home else fixture["away"]
        expected_opponent=fixture["away"] if was_home else fixture["home"]
        if strict_id(r["opponent_team"])!=expected_opponent:
            raise XGFourGateError("WRONG_OPPONENT_TEAM_FOR_FIXTURE_SIDE")
        # Immutable team ID is derived from source fixture sides, never
        # guessed from a player's name or team string.
        label=(r["team"] or "").strip()
        if not label:
            raise XGFourGateError("PLAYER_TEAM_NAME_EMPTY")
        if tid in teams_by_id and teams_by_id[tid]!=label:
            raise XGFourGateError("FPL_TEAM_NAME_CHANGED_FOR_ONE_TEAM_ID")
        teams_by_id[tid]=label
        other_tid=expected_opponent
        if other_tid in teams_by_id and teams_by_id[other_tid]==label:
            raise XGFourGateError("FPL_TEAM_LABEL_AMBIGUOUS")
        player_id=strict_id(r["element"])
        unique=(fid,tid,player_id)
        if unique in dedup:
            duplicates+=1
            raise XGFourGateError("DUPLICATE_PLAYER_FIXTURE_WOULD_DOUBLE_COUNT_XG")
        dedup.add(unique)
        xg=valid_num(r["expected_goals"])
        side_totals[(fid,tid)]+=xg
        players_per_side[(fid,tid)]+=1
    if len(set(teams_by_id.values()))!=len(teams_by_id):
        raise XGFourGateError("FPL_TEAM_LABELS_NOT_BIJECTIVE")
    sides_full=set()
    for fid,item in fixture_index.items():
        if item["finished"]=="True":
            sides=((fid,item["home"]),(fid,item["away"]))
            if all(players_per_side.get(side,0)>0 for side in sides):
                sides_full.add(fid)
    complete_fixtures=sum(x["finished"]=="True" for x in fixture_index.values())
    return {"published_at":published_at,"source_method":METHOD,
            "source_match_index":fixture_index,
            "FPL_team_labels_IN_MEMORY_ONLY":teams_by_id,
            "source_side_xg_values_IN_MEMORY_ONLY":side_totals,
            "source_side_row_counts":players_per_side,
            "finished_fixtures":complete_fixtures,
            "fixtures_with_both_sides_player_xg":len(sides_full),
            "fixture_count":len(fixture_index),
            "side_count_with_xg":len(side_totals),
            "player_rows":rows,
            "verified_FPL_team_ID_count":len(teams_by_id),
            "duplicate_player_fixture":duplicates}

def before_target(*,prior_fixture,prior_team,src,cutoff,target_kickoff,definition=METHOD):
    """All four conditions apply to the SAME historic value, not a nearby match."""
    if definition!=METHOD:
        raise XGFourGateError("ORIGINAL_TEAM_XG_SEMANTICS_NOT_EQUIVALENT")
    stamp=utc(src["published_at"])
    edge=utc(cutoff)
    target=utc(target_kickoff)
    if not stamp<=edge<target:
        raise XGFourGateError("SOURCE_NOT_PUBLIC_BEFORE_PREMATCH_CUTOFF")
    match=src["source_match_index"].get(prior_fixture)
    if match is None or match["finished"]!="True":
        raise XGFourGateError("PREDECESSOR_FIXTURE_NOT_IN_PINNED_BLOB")
    if prior_team not in (match["home"],match["away"]):
        raise XGFourGateError("TEAM_NOT_A_PARTICIPANT")
    if match["kickoff"]+timedelta(hours=3)>stamp or match["kickoff"]>=edge:
        raise XGFourGateError("HISTORIC_GAME_RESULT_NOT_PREVIOUSLY_AVAILABLE")
    if (prior_fixture,prior_team) not in src["source_side_xg_values_IN_MEMORY_ONLY"]:
        raise XGFourGateError("NO_PLAYER_XG_FOR_EXACT_FIXTURE_TEAM_SIDE")
    return True

def inspect_real_old_2023(*,fetcher=fetch):
    evidence=original_proof()
    p=evidence["full_season_EPL_2023_24"]
    if p["event_server_UTC"]!=FULL_2023["push"] or p["raw_sha256"]!=FULL_2023["sha"]:
        raise XGFourGateError("HISTORICAL_GHARCHIVE_CLOCK_CHANGED")
    base=f"https://raw.githubusercontent.com/{FULL_2023['repo']}/{FULL_2023['commit']}/"
    fixtures=fetcher(base+FULL_2023["path"])
    players=fetcher(base+FULL_MERGED_PATH,limit=40_000_001)
    if len(players)>=40_000_001:
        raise XGFourGateError("OLD_SOURCE_EXCEEDS_BOUNDED_READ")
    src=extract_public_xg(fixtures,players,published_at=FULL_2023["push"],
                          pinned_fixture_sha=FULL_2023["sha"],
                          pinned_player_sha=FULL_MERGED_SHA)
    if (src["finished_fixtures"]!=380 or src["fixtures_with_both_sides_player_xg"]!=380
        or src["player_rows"]!=29725 or src["verified_FPL_team_ID_count"]!=20):
        raise XGFourGateError("OLD_FPL_TEAM_FIXTURE_XG_COVERAGE_CHANGED")
    # A research-only availability example: previously published May-2024
    # player xG is usable before *2024-25* season kickoff, not 2023 targets.
    cutoff="2024-08-16T18:59:00Z"
    for fid,r in src["source_match_index"].items():
        for tid in (r["home"],r["away"]):
            before_target(prior_fixture=fid,prior_team=tid,src=src,
                cutoff=cutoff,target_kickoff="2024-08-16T19:00:00Z")
    return {"schema":SCHEMA,
        "fpl_source":"vaastav/Fantasy-Premier-League",
        "source_commit":FULL_2023["commit"],"fixture_sha256":FULL_2023["sha"],
        "player_xg_sha256":FULL_MERGED_SHA,
        "independent_publication_utc":FULL_2023["push"],
        "independent_public_push_event_id":FULL_2023["event_id"],
        "original_ft_matches":src["finished_fixtures"],
        "both_sides_exact_fixture_team_xg_matches":src["fixtures_with_both_sides_player_xg"],
        "team_fixture_side_records":src["side_count_with_xg"],
        "player_fixture_records":src["player_rows"],
        "stable_FPL_teams":src["verified_FPL_team_ID_count"],
        "strict_opponent_side_fixture_checks":"PASS",
        "historic_2023_player_xg_pre_2024_25_opening":"PASS",
        "historic_2023_player_xg_before_each_2023_24_target":False,
        "xg_source_definition":METHOD,
        "xga_only_derived_from_opponent_xg_not_repeated_player_xgc":True,
        "original_PitchAPI_team_xg_semantic_and_numeric_equivalence_proven":False,
        "historical_PitchAPI_provider_first_publication_clock_proven":False,
        "official_121_plus_38_train_pit_eligible":0,
        "validation_pit_eligible":0,
        "training_allowed":False,"gate14_pass":False,
        "private_RSA_or_scores_examined":False,"test_read":False,
        "xg_values_or_player_names_exported":False}

def main():
    import argparse
    p=argparse.ArgumentParser()
    p.add_argument("--output",required=True)
    dst=Path(p.parse_args().output)
    report=inspect_real_old_2023()
    dst.parent.mkdir(parents=True,exist_ok=True)
    encoded=json.dumps(report,sort_keys=True,ensure_ascii=False,indent=2)+"\n"
    if dst.exists():
        if dst.read_text(encoding="utf8")!=encoded:raise XGFourGateError("APPEND_ONLY_REPORT_CHANGED")
    else:dst.write_text(encoded,encoding="utf8")
    print(json.dumps({k:report[k] for k in (
         "original_ft_matches","both_sides_exact_fixture_team_xg_matches",
         "team_fixture_side_records","player_fixture_records",
         "strict_opponent_side_fixture_checks","historic_2023_player_xg_pre_2024_25_opening",
         "original_PitchAPI_team_xg_semantic_and_numeric_equivalence_proven",
         "gate14_pass")},sort_keys=True))
if __name__=="__main__":main()
