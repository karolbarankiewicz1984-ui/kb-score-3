"""KB3 Step11 observed-at fixture/xG inputs for the *same* Elo/form accumulator.

Accepts a previously decrypted, independently checksum-verified PIT SQLite
ledger and, optionally, a frozen reviewed-xG crosswalk + archive manifest.
This code never connects to an API, changes source rows, trains or predicts.
Capture time is NOT provider publication time or historical backtest certification.
"""
from __future__ import annotations
from collections import defaultdict
import json
import sqlite3

from src.kb3_features import (
    EloParameters,FeatureSafetyError,RESULT_LAG,_compose_features,utc_dt
)
from src.kb3_pit_ledger import (
    verify_chain,select_result_asof,as_utc,hexdigest,canonical
)
from src.kb3_xg_pit import verify_xg
from src.kb3_reviewed_xg import review


def _observed_index(db, cutoff):
    """Select the most recent *authentic recorded* full source snapshot as-of."""
    rows=db.execute("""
      SELECT capture_id,completed_at_utc,resource,origin,response_sha256,
             response_json,chain_sha256
      FROM captures
    """).fetchall()
    candidates=[r for r in rows if r[3]=="NETWORK_OBSERVED"
                and r[2]=="fixtures?league=39&season=2026"
                and as_utc(r[1])<=cutoff]
    if not candidates:
        raise FeatureSafetyError("NO_REAL_SOURCE_OBSERVATION_BEFORE_CUTOFF")
    candidates.sort(key=lambda r:(as_utc(r[1]),r[0]))
    cid,completed,resource,origin,hash_,raw,chain=candidates[-1]
    payload=json.loads(raw)
    if hexdigest(canonical(payload))!=hash_:
        raise FeatureSafetyError("SOURCE_CAPTURE_HASH_MISMATCH")
    found={}
    for match in payload["response"]:
        f=match["fixture"]
        fid=f["id"]
        if type(fid) is not int or fid in found:
            raise FeatureSafetyError("AMBIGUOUS_PROVIDER_FIXTURE_ID")
        if (match["league"]["id"]!=39 or match["league"]["season"]!=2026):
            raise FeatureSafetyError("WRONG_OBSERVED_COMPETITION")
        home,away=match["teams"]["home"]["id"],match["teams"]["away"]["id"]
        if not all(type(t) is int and t>0 for t in (home,away)) or home==away:
            raise FeatureSafetyError("INVALID_OBSERVED_TEAM_ID")
        found[fid]=match
    if len(found)!=380:
        raise FeatureSafetyError("INCOMPLETE_SOURCE_OBSERVATION")
    return found,{"capture_id":cid,"observed_completed_at_utc":completed,
                  "source_response_sha256":hash_,"chain_sha256":chain,
                  "provider_publication_known":False}


def build_observed_features(db, target_fixture_id, *, cutoff_utc,
                            archive_manifest=None,reviewed_crosswalk=None,
                            elo_params=None):
    """Observed-at builder with explicit, fail-closed xG provenance.

    For *reviewed* xG the approval's GitHub merge time is a second required
    barrier, in addition to the actual xG source observation time.
    """
    params=EloParameters() if elo_params is None else elo_params
    if not isinstance(params,EloParameters):
        raise FeatureSafetyError("INVALID_ELO_PARAMETERS")
    cutoff=utc_dt(cutoff_utc)
    if type(target_fixture_id) is not int:
        raise FeatureSafetyError("INVALID_TARGET_FIXTURE_ID")
    if (archive_manifest is None)!=(reviewed_crosswalk is None):
        raise FeatureSafetyError("XG_REVIEW_AND_ARCHIVE_EVIDENCE_REQUIRED_TOGETHER")
    verify_chain(db)
    has_xg=db.execute("""SELECT 1 FROM sqlite_master
                           WHERE type='table' AND name='pit_xg_observations'""").fetchone()
    if has_xg:
        verify_xg(db)  # Tampered quarantined xG is never silently overlooked.
    snapshots,selected=_observed_index(db,cutoff)
    if target_fixture_id not in snapshots:
        raise FeatureSafetyError("TARGET_MISSING_FROM_SOURCE_SNAPSHOT")
    target_src=snapshots[target_fixture_id]
    kickoff=utc_dt(target_src["fixture"]["date"])
    if cutoff>=kickoff:
        raise FeatureSafetyError("FEATURE_CUTOFF_NOT_BEFORE_KICKOFF")
    th=target_src["teams"]["home"]["id"]
    ta=target_src["teams"]["away"]["id"]
    target={"fixture_id":target_fixture_id,
            "home_team_id":th,"away_team_id":ta,
            "season_start_year":2026}
    xg_by_fixture={}
    approved_xg_since=None
    review_source={}
    if reviewed_crosswalk is not None:
        if not has_xg:
            raise FeatureSafetyError("XG_SOURCE_TABLE_MISSING")
        # Fail closed if either the source or review authority is missing.
        approved_xg_since=reviewed_crosswalk.get("review_approval_not_before_utc")
        commit=reviewed_crosswalk.get("review_approval_commit")
        if not approved_xg_since or not isinstance(commit,str) or not commit.startswith(
          "https://github.com/karolbarankiewicz1984-ui/kb-score-3/commit/"):
            raise FeatureSafetyError("NO_REVIEW_APPROVAL_PROVENANCE")
        approval_time=utc_dt(approved_xg_since)
        if approval_time<=cutoff:
            try:
                xg_by_fixture=review(db,archive_manifest,reviewed_crosswalk)
            except (ValueError,KeyError,TypeError) as exc:
                raise FeatureSafetyError("XG_SOURCE_REVIEW_FAILED") from exc
            review_source={"review_approval_not_before_utc":approved_xg_since,
                           "review_approval_commit":commit,
                           "encrypted_archive_sha256":archive_manifest["encrypted_sha256"],
                           "reviewed_fixture_count":len(xg_by_fixture)}
        else:
            xg_by_fixture={}
            approved_xg_since=None
    history=[]
    excluded=defaultdict(int)
    for fid,source in snapshots.items():
        if fid==target_fixture_id:
            continue
        source_start=utc_dt(source["fixture"]["date"])
        if source_start>=kickoff or source_start>=cutoff:
            excluded["not_before_cutoff"]+=1
            continue
        result=select_result_asof(db,fid,cutoff_utc)
        if result is None:
            excluded["no_pre_cutoff_source_result"]+=1
            continue
        recorded=utc_dt(result["observed_completed_at_utc"])
        if not (source_start+RESULT_LAG<=recorded<=cutoff):
            excluded["result_not_observed_after_minimum_lag"]+=1
            continue
        scores=(result["result_home_90"],result["result_away_90"])
        latest_status=(source["fixture"]["status"] or {}).get("short")
        if latest_status!="FT" or (source.get("score") or {}).get("fulltime") != {
          "home":scores[0],"away":scores[1]}:
            # The latest source state at cutoff cannot contradict selected FT.
            raise FeatureSafetyError("INCONSISTENT_SOURCE_RESULT_ASOF")
        h=source["teams"]["home"]["id"]
        a=source["teams"]["away"]["id"]
        xgh=xga=None
        xsource_h=xsource_a=None
        xg=xg_by_fixture.get(fid)
        if xg is not None and approved_xg_since is not None:
            observed_xg=utc_dt(xg["observed_completed_at_utc"])
            if max(observed_xg,utc_dt(approved_xg_since))<=cutoff:
                xgh,xga=xg["xg_home"],xg["xg_away"]
                provenance={"observation_id":xg["source_observation_id"],
                            "pitch_match_id":xg["pitch_match_id"],
                            "actual_observed_at_utc":xg["observed_completed_at_utc"],
                            "review_approval_not_before_utc":approved_xg_since,
                            "source_provider_published_at_utc":None,
                            "review_status":xg["review_status"]}
                xsource_h=dict(provenance)
                xsource_a=dict(provenance)
            else:
                excluded["reviewed_xg_not_available_at_cutoff"]+=1
        history.append({"fixture_id":fid,"season_start_year":2026,
            "home_team_id":h,"away_team_id":a,
            "kickoff_utc":source["fixture"]["date"],"date":source_start,
            "status":"FINISHED","goals_home_90":scores[0],
            "goals_away_90":scores[1],
            "snapshot_id":result["capture_id"],
            "result_provider_name":"API-Football",
            "result_record_updated_at_utc":None,
            "captured_at_utc":result["observed_completed_at_utc"],
            "published_at_utc":None,
            "xgh":xgh,"xga":xga,
            "xgh_source":xsource_h,"xga_source":xsource_a})
    source_evidence={
        "source_class":"NETWORK_OBSERVED_NOT_PROVIDER_PUBLICATION_CERTIFIED",
        "source_scope":"API-Football Premier League season 2026",
        "source_capture":selected,
        "asof_capture_chain_sha256":selected["chain_sha256"],
        "source_snapshot_rows":len(snapshots),
        "provider_first_publication_time_known":False,
        "historical_prematch_backtest_certified":False,
        "reviewed_xg_source":review_source if review_source else None,
        "archived_ciphertext_restore_must_be_verified_externally":True,
    }
    return _compose_features(target,history,
                             cutoff=cutoff,kickoff=kickoff,
                             target_id=target_fixture_id,mode="observed",params=params,
                             excluded=excluded,source_evidence=source_evidence)


def load_observed_features(ledger_file,fixture_id,cutoff,*,review_manifest_path=None,
                           reviewed_crosswalk_path=None):
    """Read existing restored, independently validated ledger; never download/decrypt."""
    from pathlib import Path
    def read_json(path):
        return json.loads(Path(path).read_text(encoding="utf8"))
    if (review_manifest_path is None)!=(reviewed_crosswalk_path is None):
        raise FeatureSafetyError("XG_REVIEW_AND_ARCHIVE_EVIDENCE_REQUIRED_TOGETHER")
    manifest=read_json(review_manifest_path) if review_manifest_path else None
    crosswalk=read_json(reviewed_crosswalk_path) if reviewed_crosswalk_path else None
    with sqlite3.connect("file:"+str(Path(ledger_file).resolve())+"?mode=rw",uri=True) as db:
        return build_observed_features(db,fixture_id,cutoff_utc=cutoff,
                                       archive_manifest=manifest,
                                       reviewed_crosswalk=crosswalk)
