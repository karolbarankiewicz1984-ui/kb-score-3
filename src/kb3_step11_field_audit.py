"""GATE11 per-feature recorded-time provenance for PitchAPI/native and legacy observed.

The collector stores the exact source receipts in lineage; this module checks
that every predecessor was available *before* the target cutoff, then binds
all 105+ numeric/nullable output features to its latest required receipt time.
Unknown original provider publication is never rewritten as known.
Replay and synthetic historical backtests must NOT call this with a verified claim.
"""
from __future__ import annotations
from datetime import datetime,timezone,timedelta
from collections import defaultdict
from hashlib import sha256
import json

HOURS_AFTER_KICKOFF=timedelta(hours=3)
XG_CLOCK_FIELDS=("shot_observed_at_utc","actual_observed_at_utc",
                 "observed_completed_at_utc","observed_at_utc")
SOURCE_CLOCK_FIELDS=("source_observed_at_utc",)

class TemporalEvidenceError(ValueError):
    pass

def timestamp(value):
    if not isinstance(value,str):
        raise TemporalEvidenceError("MISSING_SOURCE_TIMESTAMP")
    try:
        d=datetime.fromisoformat(value.replace("Z","+00:00"))
    except ValueError as exc:
        raise TemporalEvidenceError("MALFORMED_SOURCE_TIMESTAMP") from exc
    if d.utcoffset() is None:
        raise TemporalEvidenceError("NAIVE_SOURCE_TIMESTAMP")
    return d.astimezone(timezone.utc)

def serialize(t):
    return t.astimezone(timezone.utc).isoformat().replace("+00:00","Z")

def source_time(source):
    if not isinstance(source,dict):
        raise TemporalEvidenceError("MISSING_XG_SOURCE")
    clocks=[source[key] for key in XG_CLOCK_FIELDS if source.get(key) is not None]
    if len(clocks)!=1:
        raise TemporalEvidenceError("AMBIGUOUS_XG_SOURCE_OBSERVED_TIME")
    actual=timestamp(clocks[0])
    approval=source.get("review_approval_not_before_utc")
    if approval is not None:
        actual=max(actual,timestamp(approval))
    return actual

def snapshot_time(evidence):
    if not isinstance(evidence,dict):
        raise TemporalEvidenceError("MISSING_OBSERVED_SOURCE_EVIDENCE")
    if evidence.get("source_observed_at_utc"):
        return timestamp(evidence["source_observed_at_utc"])
    capture=evidence.get("source_capture")
    if isinstance(capture,dict) and capture.get("observed_completed_at_utc"):
        return timestamp(capture["observed_completed_at_utc"])
    raise TemporalEvidenceError("MISSING_PRIMARY_SNAPSHOT_CLOCK")

def validate_observed_rows(history,*,cutoff,kickoff,target_id,target):
    if target["home_team_id"]==target["away_team_id"]:
        raise TemporalEvidenceError("TARGET_SAME_TEAM_BOTH_SIDES")
    seen=set()
    for row in history:
        mid=row.get("fixture_id")
        if mid==target_id or mid in seen:
            raise TemporalEvidenceError("DUPLICATE_OR_TARGET_IN_HISTORY")
        seen.add(mid)
        ko=row.get("date")
        if not isinstance(ko,datetime) or ko.utcoffset() is None:
            raise TemporalEvidenceError("HISTORY_DATE_NOT_DATETIME")
        ko=ko.astimezone(timezone.utc)
        if ko>=cutoff or ko>=kickoff:
            raise TemporalEvidenceError("FUTURE_RESULT_IN_PREMATCH_HISTORY")
        if row.get("home_team_id")==row.get("away_team_id"):
            raise TemporalEvidenceError("SAME_TEAM_BOTH_SIDES")
        if row.get("status")!="FINISHED":
            raise TemporalEvidenceError("NONFINAL_RESULT_IN_HISTORY")
        if not all(type(row.get(f)) is int and row[f]>=0
                   for f in ("goals_home_90","goals_away_90")):
            raise TemporalEvidenceError("INVALID_RESULT_SCORE")
        recorded=timestamp(row.get("captured_at_utc"))
        if not ko+HOURS_AFTER_KICKOFF<=recorded<=cutoff:
            raise TemporalEvidenceError("RESULT_KNOWN_AFTER_TARGET_CUTOFF")
        for valkey,srckey in (("xgh","xgh_source"),("xga","xga_source")):
            val=row.get(valkey);source=row.get(srckey)
            if (val is None)!=(source is None):
                raise TemporalEvidenceError("XG_VALUE_AND_SOURCE_MUST_AGREE")
            if val is not None:
                if isinstance(val,bool) or not isinstance(val,(int,float)) or not 0<=val<1e6:
                    raise TemporalEvidenceError("INVALID_XG_VALUE")
                when=source_time(source)
                if not ko+HOURS_AFTER_KICKOFF<=when<=cutoff:
                    raise TemporalEvidenceError("XG_KNOWN_AFTER_TARGET_CUTOFF")


def feature_clock_map(target,history,values,missing_flags,*,cutoff,source_evidence):
    """Map EACH output numeric/nullable field AND missing flag to actual receipts.

    Snapshot clock is included for zero-count, null and feature completeness
    claims. This is observed-at evidence; NOT provider publication certification.
    """
    base=snapshot_time(source_evidence)
    if base>cutoff:
        raise TemporalEvidenceError("LATEST_SOURCE_AFTER_CUTOFF")
    out={}
    sorted_history=sorted(history,key=lambda r:(r["date"],str(r["fixture_id"])))
    def assign(field,subset,kind="RESULT",xg_key=None):
        required=[base]
        for row in subset:
            required.append(timestamp(row["captured_at_utc"]))
            if xg_key is not None and row.get(xg_key) is not None:
                required.append(source_time(row[xg_key]))
        end=max(required)
        if end>cutoff:
            raise TemporalEvidenceError("FEATURE_RECEIPT_FUTURE_LEAK")
        # Hash ID *set* only; native team/fixture IDs are not public report fields.
        ids=sorted(str(r["fixture_id"]) for r in subset)
        proof=sha256(json.dumps(ids,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()
        out[field]={"latest_required_observed_at_utc":serialize(end),
          "evidence_class":"OBSERVED_AT_NOT_PROVIDER_PUBLISHED",
          "kind":kind,
          "included_games":len(subset),
          "fixtures_sha256":proof,
          "provider_original_published_at_utc":None,
          "training_allowed":False}
    for side,team,venue in (("home",target["home_team_id"],True),
                            ("away",target["away_team_id"],False)):
        allgames=[r for r in sorted_history
                  if team in (r["home_team_id"],r["away_team_id"])]
        homegames=[r for r in allgames if (r["home_team_id"]==team)==venue]
        assign("missing:"+side+"_days_since_last_kickoff",
               allgames,"HISTORY_COMPLETENESS")
        for suffix in ("elo","elo_games_available","prior_seasons_games_available",
                       "games_available","days_since_last_kickoff","venue_games_available"):
            assign(f"{side}_{suffix}",allgames if suffix!="venue_games_available" else homegames)
        for category,games in (("all",allgames),("venue",homegames)):
            for n in (5,10,15):
                group=games[-n:]
                prefix=f"{side}_{category}_{n}"
                assign(prefix+"_n",group)
                for suffix in ("points_avg","gf_avg","ga_avg","opponent_elo_avg"):
                    assign(prefix+"_"+suffix,group)
                for key in ("xg","xga"):
                    # Source direction is picked for each historical fixture,
                    # because a target home team also played away in history.
                    # Per-row source is selected from team home/away orientation.
                    for suffix in ("_n","_avg"):
                        assign(prefix+"_"+key+suffix,group,"XG_OBSERVATIONS_AND_RESULTS",
                               xg_key=None)
                    # Correct per-row time maxima are added explicitly below.
                    relevant=[source_time(r["xgh_source" if
                        (r["home_team_id"]==team)==(key=="xg") else "xga_source"])
                        for r in group if r.get("xgh_source" if
                        (r["home_team_id"]==team)==(key=="xg") else "xga_source") is not None]
                    if relevant:
                        for suffix in ("_n","_avg"):
                            obj=out[prefix+"_"+key+suffix]
                            obj["latest_required_observed_at_utc"]=serialize(max(
                                timestamp(obj["latest_required_observed_at_utc"]),*relevant))
                assign("missing:"+prefix+"_history",group,"HISTORY_COMPLETENESS")
                for key in ("xg","xga"):
                    assign("missing:"+prefix+"_"+key,group,"XG_COMPLETENESS")
    assign("elo_home_minus_away",sorted_history,"ELO_RESULTS")
    expected=set(values)|{"missing:"+k for k in missing_flags}
    if set(out)!=expected:
        raise TemporalEvidenceError("FIELD_LINEAGE_SCHEMA_MISMATCH:"+str(
            len(expected-set(out)))+":"+str(len(set(out)-expected)))
    if any(timestamp(v["latest_required_observed_at_utc"])>cutoff for v in out.values()):
        raise TemporalEvidenceError("FIELD_AFTER_CUTOFF")
    return dict(sorted(out.items()))
