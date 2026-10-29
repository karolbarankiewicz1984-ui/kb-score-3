"""Recompute Step14 genuine 2023/24–2024/25 TRAIN after preserving FPL scores 3.0.

Historical FPL GW CSV used "3.0" as an integer goal score in old snapshots.
Original v1 integer-only parser rejected legitimate values and UNDERCOUNTED
TRAIN. This is a new append-only v2 research audit; v1 is never overwritten.
No original CatBoost, target score, test, or odds are used.
"""
from __future__ import annotations
import argparse,csv,gzip,hashlib,io,json,math
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from src.kb3_step14_multiseason_pit import fetch,raw_url
from scripts.step14_full_1140_native_public_pit_lineage import (
    independently_pinned_sources,old_source_rows)
from scripts import step14_train_760_dense_validation_1140_matrix as base

ROOT=Path(__file__).resolve().parents[1]
SCHEMA="kb3-step14-old-FPL-float-encoded-integer-FT-strict-corrected-2026-10-29-v2"
class CorrectedScoreError(ValueError):pass

def goal(value):
    """Real integer 90m goals, including old FPL CSV '3.0'; never round 3.5."""
    if type(value) not in (str,int,float) or value=="":
        raise CorrectedScoreError("MISSING_FT")
    try:n=float(value)
    except (TypeError,ValueError) as exc:raise CorrectedScoreError("INVALID_FT") from exc
    if not math.isfinite(n) or not n.is_integer() or n<0 or n>30:
        raise CorrectedScoreError("NOT_WHOLE_NONNEGATIVE_FT")
    return int(n)

def corrected_source(source,fetcher=fetch):
    if source.get("provider","FPL")=="OpenFootball":
        return base._source_rows(source,fetcher=fetcher)
    if source.get("provider","FPL")!="FPL":
        raise CorrectedScoreError("UNEXPECTED_SOURCE")
    raw=fetcher(raw_url(source),limit=3_000_001)
    if hashlib.sha256(raw).hexdigest()!=source["sha"]:
        raise CorrectedScoreError("SOURCE_SHA_CHANGED")
    old_source_rows(source,fetcher=lambda url,**kwargs:raw)
    repo=source["repo"];sha=source["commit"];season=source["season"]
    teams_raw=fetcher(f"https://raw.githubusercontent.com/{repo}/{sha}/data/{season}/teams.csv",limit=100_001)
    teams={}
    for row in csv.DictReader(io.StringIO(teams_raw.decode("utf-8-sig"))):
        ident=row["id"];name=base._team(row["name"])
        if ident in teams or name in teams.values():raise CorrectedScoreError("AMBIGUOUS_OLD_TEAM")
        teams[ident]=name
    if len(teams)!=20:raise CorrectedScoreError("OLD_TEAM_SET_NOT_20")
    stamped=base._utc(source["push"])
    past={};schedule={};quarantined=0;decimal_values=0
    for row in csv.DictReader(io.StringIO(raw.decode("utf-8-sig"),newline="")):
        if not row["kickoff_time"]:continue
        ko=base._utc(row["kickoff_time"])
        try:key=(teams[row["team_h"]],teams[row["team_a"]],ko.isoformat())
        except KeyError as exc:raise CorrectedScoreError("UNKNOWN_OLD_TEAM_ID") from exc
        if key in schedule:raise CorrectedScoreError("DUPLICATE_OLD_FIXTURE")
        finished=row["finished"]=="True"
        if finished:
            if (stamped-ko).total_seconds()<3*3600:
                raise CorrectedScoreError("OLD_SOURCE_RESULT_BEFORE_LAG")
            try:
                h=goal(row["team_h_score"]);a=goal(row["team_a_score"])
            except CorrectedScoreError:
                # An invalid predecessor stays a hole in any future 5/10/15.
                quarantined+=1;schedule[key]=True
                continue
            decimal_values+=str(row["team_h_score"]).endswith(".0")
            decimal_values+=str(row["team_a_score"]).endswith(".0")
            past[key]={"home":key[0],"away":key[1],"kickoff":ko,
                       "home_goals":h,"away_goals":a,
                       "home_xg":None,"away_xg":None}
        elif row["team_h_score"] or row["team_a_score"]:
            raise CorrectedScoreError("UNPLAYED_FT_PRESENT")
        schedule[key]=finished
    return {"source":source,"commit":sha,"witness":source["push"],
            "past":past,"schedules":schedule,"source_raw_sha256":source["sha"],
            "quarantined_invalid_completed_result_rows":quarantined,
            "historical_decimal_dot_zero_goal_cells_parsed_as_exact_integer":decimal_values,
            "source_time_independently_verified":True}

def run(root=ROOT):
    selected=[s for s in independently_pinned_sources()
              if s["season"] in ("2023-24","2024-25")]
    if len(selected)!=12:raise CorrectedScoreError("NOT_TWELVE_OLD_TRAIN_CLOCKS")
    with ThreadPoolExecutor(max_workers=6) as executor:
        old=list(executor.map(corrected_source,selected))
    report,rows=base.run(root,old_sources_override=old)
    if report["original_frozen_760_TRAIN_380_VALIDATION"]!={"TRAIN":760,"VALIDATION":380}:
        raise CorrectedScoreError("ORIGINAL_SPLIT_NOT_FIXED")
    if report["distinct_original_TRAIN_with_historical_public_result_FORM5"]<10:
        raise CorrectedScoreError("PREVIOUS_TRAIN_COVERAGE_REGRESSED")
    if (report["distinct_original_VALIDATION_with_historical_public_result_FORM5"]!=109
        or report["distinct_original_VALIDATION_with_historical_alternative_xG5"]!=107):
        raise CorrectedScoreError("VALIDATION_SOURCE_CHANGED")
    report["original_historic_FT_decimal_scores_recovery_version"]=SCHEMA
    report["historical_decimal_dot_zero_score_cells_correctly_parsed"]=sum(
        x.get("historical_decimal_dot_zero_goal_cells_parsed_as_exact_integer",0) for x in old)
    report["previous_v1_TRAIN_10_is_underestimate_from_strict_int_string_parser"]=True
    report["new_report_does_NOT_overwrite_previous_v1_original"]=True
    return report,rows

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--out",required=True);p.add_argument("--matrix",required=True)
    a=p.parse_args();out=Path(a.out);matrix=Path(a.matrix)
    if out.exists() or matrix.exists():raise CorrectedScoreError("APPEND_ONLY_V2")
    report,rows=run()
    out.parent.mkdir(parents=True,exist_ok=True);matrix.parent.mkdir(parents=True,exist_ok=True)
    with gzip.open(matrix,"wt",encoding="utf8",compresslevel=7) as f:
        for r in rows:f.write(json.dumps(r,ensure_ascii=False,sort_keys=True)+"\n")
    report["matrix_gzip_sha256"]=hashlib.sha256(matrix.read_bytes()).hexdigest()
    report["matrix_rows"]=len(rows)
    out.write_text(json.dumps(report,ensure_ascii=False,sort_keys=True,indent=2)+"\n")
    print(json.dumps({"corrected_train_FORM5":report["distinct_original_TRAIN_with_historical_public_result_FORM5"],
      "validation_FORM5":report["distinct_original_VALIDATION_with_historical_public_result_FORM5"],
      "validation_complete_xG5":report["distinct_original_VALIDATION_with_historical_alternative_xG5"],
      "old_dot_zero_FT_cells":report["historical_decimal_dot_zero_score_cells_correctly_parsed"],
      "original_model_fit":False,"GATE14":"PENDING"},sort_keys=True))

if __name__=="__main__":main()
