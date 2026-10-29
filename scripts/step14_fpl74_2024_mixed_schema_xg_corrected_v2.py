"""Old 2024/25 FPL data format correction: 7 extra score columns after GW21.

Old merged_gw.csv headers retained 42 columns, while later GW22+ rows
sometimes have 49 (seven extra numeric fields BEFORE the 'modified' field).
The original raw SHA is retained; normalization only removes those 7 columns,
with exact validation of gameweek, remaining field types, and opponent/side.

Never infer provenance from the corrected rows or change original M1/PIT.
Append-only new v2 outputs; old source report and 31 xG5 stay immutable.
"""
from __future__ import annotations
from collections import Counter
from hashlib import sha256
from pathlib import Path
import argparse,csv,gzip,io,json,math
from scripts import step14_fpl74_asof_train_xg_recovery as old
from scripts.step14_train_760_dense_validation_1140_matrix import _team
from scripts.step14_fpl_core_2025_independent_asof import _utc
from src.kb3_step14_xg_four_gates import extract_public_xg,METHOD

SCHEMA="kb3-step14-fpl74-player-xg-2024-mixed-42-and-49-column-old-csv-v2"
class MixedFPLSchemaError(ValueError):pass
MIXED_LOG={}

def normalize_csv(original):
    if not isinstance(original,bytes):raise MixedFPLSchemaError("NOT_ORIGINAL_OLD_BYTES")
    decoded=original.decode("utf-8-sig")
    stream=csv.reader(io.StringIO(decoded,newline=""))
    header=next(stream,None)
    if not header or len(header)!=42 or (
        header[14],header[19],header[21],header[22],header[39],header[41])!=(
        "fixture","kickoff_time","modified","opponent_team","was_home","GW"):
        raise MixedFPLSchemaError("NOT_RECOGNIZED_ORIGINAL_2024_OLD_HEADER")
    out=io.StringIO(newline="")
    writer=csv.writer(out,lineterminator="\n")
    writer.writerow(header)
    dropped=0;unchanged=0;rows=0
    for row in stream:
        if not row:continue
        rows+=1
        if len(row)==42:
            unchanged+=1
        elif len(row)==49:
            # GW22 introduced seven extra integer fields before modified.
            if (row[28] not in ("True","False")
                or row[46] not in ("True","False")
                or not row[48].isdecimal() or int(row[48])<22
                or any(not x.isdecimal() for x in row[21:28])):
                raise MixedFPLSchemaError("UNKNOWN_49_COLUMN_FORMAT")
            row=row[:21]+row[28:]
            dropped+=1
        else:raise MixedFPLSchemaError("UNEXPECTED_SOURCE_FIELD_COUNT")
        if (len(row)!=42 or row[39] not in ("True","False")
            or not row[14].isdecimal() or not row[22].isdecimal()
            or not row[41].isdecimal()):
            raise MixedFPLSchemaError("NORMALIZED_FPL_ROW_STILL_WRONG")
        writer.writerow(row)
    if rows==0:raise MixedFPLSchemaError("EMPTY_HISTORICAL_XG")
    result=out.getvalue().encode("utf-8")
    return result,{"rows":rows,"unchanged_42_column_rows":unchanged,
                   "corrected_GW22_plus_49_column_rows":dropped,
                   "original_old_file_sha256":sha256(original).hexdigest(),
                   "normalized_in_memory_sha256":sha256(result).hexdigest()}

def normalized_fpl_source(blob,src,fetcher=old.fetch):
    pin=src["source"]
    original=old._raw(pin["commit"],pin["season"],"gws/merged_gw.csv",
                       max_bytes=30_000_000,fetcher=fetcher)
    if not original:raise MixedFPLSchemaError("EMPTY_HISTORIC_PLAYER_XG")
    player_blob=original;repaired=0
    if pin["season"]=="2024-25":
        player_blob,meta=normalize_csv(original)
        repaired=meta["corrected_GW22_plus_49_column_rows"]
        MIXED_LOG[pin["commit"]]=meta
    old_sha=sha256(original).hexdigest()
    xg=extract_public_xg(src["fixture_raw"],player_blob,
         published_at=pin["push"],pinned_fixture_sha=pin["sha"],
         pinned_player_sha=sha256(player_blob).hexdigest())
    team_raw=old._raw(pin["commit"],pin["season"],"teams.csv",
          max_bytes=100_000,fetcher=fetcher)
    names={}
    for row in csv.DictReader(io.StringIO(team_raw.decode("utf-8-sig"))):
        ident=int(row["id"]);name=_team(row["name"])
        if ident in names or name in names.values():raise MixedFPLSchemaError("OLD_TEAMS_AMBIGUOUS")
        names[ident]=name
    lookup={}
    for row in csv.DictReader(io.StringIO(src["fixture_raw"].decode("utf-8-sig"))):
        if not row["kickoff_time"]:continue
        key=(names[int(row["team_h"])],names[int(row["team_a"])],
             _utc(row["kickoff_time"]).isoformat())
        if key in lookup:raise MixedFPLSchemaError("DUPLICATE_FIXTURE")
        lookup[key]=(int(row["id"]),int(row["team_h"]),int(row["team_a"]))
    past={}
    for key,previous in src["past"].items():
        row=dict(previous);row["home_xg"]=None;row["away_xg"]=None
        pair=lookup.get(key)
        if pair:
            fid,h,a=pair
            if (xg["source_side_row_counts"].get((fid,h),0)>=11 and
                xg["source_side_row_counts"].get((fid,a),0)>=11):
                hx=xg["source_side_xg_values_IN_MEMORY_ONLY"].get((fid,h))
                ax=xg["source_side_xg_values_IN_MEMORY_ONLY"].get((fid,a))
                if hx is not None and ax is not None:
                    row["home_xg"]=round(hx,8);row["away_xg"]=round(ax,8)
        past[key]=row
    return {"sha256":old_sha,"player_rows":xg["player_rows"],
        "fixture_both_sides_xg":sum(
            row["home_xg"] is not None and row["away_xg"] is not None
            for row in past.values()),
        "corrected_49_column_old_GW22_plus_rows":repaired,
        "past":past,"source_metric":METHOD}

def run(root=old.ROOT):
    original=old._fpl_side_xg
    try:
        old._fpl_side_xg=normalized_fpl_source
        report,rows=old.run(root)
    finally:
        old._fpl_side_xg=original
    if report["original_74_fpl_revisions_examined"]!=74:
        raise MixedFPLSchemaError("HISTORIC_74_MISSING")
    if report["original_760_TRAIN_public_FORM5_total_after_74"]!=54:
        raise MixedFPLSchemaError("TRAIN_F5_CONTRACT_CHANGED")
    if report["TRAIN_with_complete_historic_ALTERNATIVE_FPL_Opta_player_xG5"]<31:
        raise MixedFPLSchemaError("CORRECTED_XG_BECAME_WORSE")
    report["v2_parser_schema"]=SCHEMA
    report["corrected_old_2024_snapshots"]=sum(
         item["corrected_GW22_plus_49_column_rows"]>0 for item in MIXED_LOG.values())
    report["total_raw_old_FPL_rows_schema_corrected"]=sum(
         item["corrected_GW22_plus_49_column_rows"] for item in MIXED_LOG.values())
    report["source_original_raw_SHA_preserved"]=True
    report["selected_FPL_2024_raw_vs_transformed_source_sha"]={
         k:{"original_sha256":v["original_old_file_sha256"],
            "normalized_sha256":v["normalized_in_memory_sha256"],
            "corrected_rows":v["corrected_GW22_plus_49_column_rows"]}
         for k,v in MIXED_LOG.items()}
    report["earlier_31_results_remain_immutable"]=True
    return report,rows

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--summary",required=True)
    p.add_argument("--matrix",required=True)
    args=p.parse_args();summary=Path(args.summary);matrix=Path(args.matrix)
    if summary.exists() or matrix.exists():raise MixedFPLSchemaError("APPEND_ONLY_V2")
    report,rows=run()
    summary.parent.mkdir(parents=True,exist_ok=True);matrix.parent.mkdir(parents=True,exist_ok=True)
    with gzip.open(matrix,"wt",encoding="utf8",compresslevel=7) as f:
        for item in rows:f.write(json.dumps(item,sort_keys=True,ensure_ascii=False)+"\n")
    report["matrix_gzip_sha256"]=sha256(matrix.read_bytes()).hexdigest()
    summary.write_text(json.dumps(report,sort_keys=True,indent=2,ensure_ascii=False)+"\n")
    print(json.dumps({"fpl_old_revisions":74,"old_train_F5":report["original_760_TRAIN_public_FORM5_total_after_74"],
         "old_train_alternative_xG5":report["TRAIN_with_complete_historic_ALTERNATIVE_FPL_Opta_player_xG5"],
         "old_rows_corrected":report["total_raw_old_FPL_rows_schema_corrected"],
         "source_snapshots_corrected":report["corrected_old_2024_snapshots"],
         "original_GATE14":"PENDING"},sort_keys=True))

if __name__=="__main__":main()
