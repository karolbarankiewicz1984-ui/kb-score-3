"""KB Score 3.0 — GATE10 deterministic retrospective-data quality gate.

Checks real Step09 SQLite fixtures. This is NOT prematch feature validation.
Historical results are labels; post-event reads cannot masquerade as archived
information available before a fixture.
"""
import argparse
from collections import Counter
import datetime as dt
import hashlib
import json
from pathlib import Path
import sqlite3

from src.kb3_storage import connect, verify_database

LEAGUE = "Premier League"
SEASON = 2024
EXPECTED = 380
MIN_KICKOFF = dt.datetime(2024, 8, 1, tzinfo=dt.timezone.utc)
MAX_KICKOFF = dt.datetime(2025, 7, 1, tzinfo=dt.timezone.utc)
POSTMATCH_METRICS = {"xg", "goals", "shots", "fouls", "corner kicks",
                     "yellow cards", "red cards", "ball possession"}

def parse_time(value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("MISSING_TIMESTAMP")
    try:
        ts = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
        if ts.tzinfo is None:
            raise ValueError("NAIVE_TIMESTAMP")
        return ts.astimezone(dt.timezone.utc)
    except ValueError as exc:
        raise ValueError("INVALID_TIMESTAMP") from exc

def assess_fixture(row):
    """Pure row check, reusable by explicitly negative unit tests."""
    errors = []
    try:
        kickoff = parse_time(row["kickoff_utc"])
        if not (MIN_KICKOFF <= kickoff < MAX_KICKOFF):
            errors.append("KICKOFF_OUTSIDE_SEASON")
        if not str(row["kickoff_utc"]).endswith("Z"):
            errors.append("NONCANONICAL_UTC")
    except ValueError:
        errors.append("INVALID_KICKOFF")
    if row["home_team_id"] == row["away_team_id"]:
        errors.append("SAME_HOME_AWAY")
    if row["status"] != "FINISHED":
        errors.append("INCOMPLETE_SEASON_STATUS")
    for side in ("goals_home_90", "goals_away_90"):
        g = row[side]
        if not isinstance(g, int) or isinstance(g, bool) or g < 0:
            errors.append("MISSING_OR_INVALID_REGULATION_GOALS_" + side)
        elif g > 20:
            errors.append("OUTLIER_GOALS_REVIEW_" + side)
    return errors

def prematch_source_decision(*, fixture_kickoff, feature_cutoff,
                            observed_at, published_at, availability,
                            source_match_id=None, target_match_id=None,
                            contains_match_outcome=False,
                            source_match_finished_at=None):
    """Fail closed: evidence for features must exist *at prediction cutoff*."""
    reasons = []
    try:
        kickoff = parse_time(fixture_kickoff)
        cutoff = parse_time(feature_cutoff)
        if cutoff >= kickoff:
            reasons.append("CUTOFF_AT_OR_AFTER_KICKOFF")
    except ValueError:
        reasons.append("INVALID_FIXTURE_OR_CUTOFF")
        cutoff = None
    if availability != "VERIFIED_PREMATCH":
        reasons.append("NOT_VERIFIED_PREMATCH")
    if observed_at is None or published_at is None:
        reasons.append("MISSING_SOURCE_AVAILABILITY_PROOF")
    elif cutoff is not None:
        try:
            if parse_time(observed_at) > cutoff:
                reasons.append("OBSERVED_AFTER_CUTOFF")
            if parse_time(published_at) > cutoff:
                reasons.append("PUBLISHED_AFTER_CUTOFF")
        except ValueError:
            reasons.append("INVALID_SOURCE_TIME")
    if contains_match_outcome:
        if not source_match_id or not target_match_id:
            reasons.append("MISSING_MATCH_ID_PROOF")
        if source_match_id == target_match_id:
            reasons.append("TARGET_OUTCOME_LEAKAGE")
        if source_match_finished_at is None:
            reasons.append("MISSING_SOURCE_MATCH_FINISH_PROOF")
        else:
            try:
                finish=parse_time(source_match_finished_at)
                if cutoff is not None and finish > cutoff:
                    reasons.append("SOURCE_MATCH_FINISHED_AFTER_CUTOFF")
                if published_at is not None and parse_time(published_at) < finish:
                    reasons.append("OUTCOME_PUBLICATION_BEFORE_FINISH")
            except ValueError:
                reasons.append("INVALID_SOURCE_MATCH_FINISH_TIME")
    return {"eligible":not bool(reasons), "reasons":sorted(set(reasons))}

def analyze(db, *, expected_count=EXPECTED):
    issues=[]
    warnings=[]
    with connect(db) as c:
        c.row_factory=sqlite3.Row
        try:
            integrity=verify_database(c)
        except (ValueError,sqlite3.DatabaseError) as e:
            return {"result":"FAIL","critical_errors":["DATABASE_"+str(e)],
                    "warnings":[],"training_allowed":False}
        rows=c.execute("""
            SELECT f.fixture_id,f.season_id,f.home_team_id,f.away_team_id,
                   f.kickoff_utc,f.status,f.goals_home_90,f.goals_away_90,
                   s.start_year,s.season_label,cp.name AS competition
            FROM fixtures f JOIN seasons s ON f.season_id=s.season_id
            JOIN competitions cp ON cp.competition_id=s.competition_id
            ORDER BY f.kickoff_utc,f.fixture_id
        """).fetchall()
        count=len(rows)
        if count!=expected_count: issues.append("FIXTURE_COUNT_MISMATCH")
        if any(r["start_year"]!=SEASON or r["competition"]!=LEAGUE for r in rows):
            issues.append("FOREIGN_LEAGUE_OR_SEASON")
        result_errors=Counter()
        home=Counter()
        away=Counter()
        fixture_pairs=Counter()
        dates_by_team=Counter()
        for row in rows:
            home[row["home_team_id"]]+=1
            away[row["away_team_id"]]+=1
            fixture_pairs[(row["home_team_id"],row["away_team_id"])]+=1
            # Multiple games on the same day for one club indicate identity/time error.
            for tid in (row["home_team_id"],row["away_team_id"]):
                dates_by_team[(tid,str(row["kickoff_utc"])[:10])]+=1
            for e in assess_fixture(row): result_errors[e]+=1
        if result_errors:issues.extend(result_errors.keys())
        if len(set(home)|set(away))!=20:issues.append("UNEXPECTED_TEAM_COUNT")
        if any(home[tid]!=19 or away[tid]!=19 for tid in set(home)|set(away)):
            issues.append("HOME_AWAY_SCHEDULE_IMBALANCE")
        if len(fixture_pairs)!=count or any(n!=1 for n in fixture_pairs.values()):
            issues.append("DUPLICATE_HOME_AWAY_PAIR")
        if any(n>1 for n in dates_by_team.values()):
            issues.append("SAME_TEAM_MULTIPLE_FIXTURES_SAME_DATE")
        duplicate_maps=c.execute("""
            SELECT COUNT(*) FROM (
              SELECT provider_id,provider_fixture_id
              FROM fixture_provider_map GROUP BY 1,2 HAVING COUNT(*)>1
            )
        """).fetchone()[0]
        mapping=c.execute("""
           SELECT COUNT(*) AS n,COUNT(DISTINCT m.fixture_id) AS unique_match,
                  COUNT(DISTINCT m.provider_fixture_id) AS unique_ids
           FROM fixture_provider_map m JOIN providers p ON p.provider_id=m.provider_id
           WHERE p.name='API-Football' AND m.match_quality='STRICT' AND
                 m.review_status='APPROVED'
        """).fetchone()
        if duplicate_maps or (mapping["n"],mapping["unique_match"],mapping["unique_ids"])!=(count,count,count):
            issues.append("PROVIDER_MAPPING_INCONSISTENT")
        orphan_or_pending=c.execute("""
           SELECT COUNT(*) FROM fixture_provider_map
           WHERE match_quality <> 'STRICT' OR review_status <> 'APPROVED'
        """).fetchone()[0]
        if orphan_or_pending:
            warnings.append("UNAPPROVED_MAPPING_QUEUE_PRESENT_NOT_USED")
        snapshots=c.execute("""
             SELECT snapshot_id,availability_class,published_at_utc,captured_at_utc
             FROM source_snapshots
        """).fetchall()
        retro=sum(r["availability_class"]=="RETROSPECTIVE" for r in snapshots)
        if not retro:issues.append("NO_RETROSPECTIVE_SOURCE_EVIDENCE")
        # A source cannot claim VERIFIED_PREMATCH merely because the API
        # was queried after completion; require actual publication proof.
        unverified_pre=c.execute("""
           SELECT COUNT(*) FROM source_snapshots
           WHERE availability_class='VERIFIED_PREMATCH' AND published_at_utc IS NULL
        """).fetchone()[0]
        if unverified_pre:issues.append("PREMATCH_SOURCE_WITHOUT_PUBLICATION_PROOF")
        feature_count=c.execute("SELECT COUNT(*) FROM feature_snapshots").fetchone()[0]
        if feature_count:
            # Source-to-feature provenance graph is not implemented at step 10.
            warnings.append("FEATURE_PROVENANCE_NOT_YET_AUDITABLE")
        stats=c.execute("SELECT COUNT(*) FROM match_stat_observations").fetchone()[0]
        odds=c.execute("SELECT COUNT(*) FROM odds_snapshots").fetchone()[0]
        events=c.execute("SELECT COUNT(*) FROM match_events").fetchone()[0]
        if not stats:warnings.append("NO_MATCH_STATISTICS_IMPORTED")
        if not odds:warnings.append("NO_ODDS_IMPORTED")
        if not events:warnings.append("NO_MATCH_EVENTS_IMPORTED")
        # Any full-time match observation masquerading as prematch is forbidden.
        lookahead=c.execute("""
           SELECT COUNT(*) FROM match_stat_observations x
           JOIN source_snapshots s ON x.snapshot_id=s.snapshot_id
           WHERE s.availability_class='VERIFIED_PREMATCH'
             AND (lower(x.metric) LIKE '%goal%'
               OR lower(x.metric) LIKE '%foul%'
               OR lower(x.metric) LIKE '%corner%'
               OR lower(x.metric) LIKE '%xg%')
        """).fetchone()[0]
        if lookahead:issues.append("FINAL_MATCH_STATS_AS_PREMATCH_SOURCE")
        # Even if structural QA passes, this is NOT training-ready: real
        # historical observation timestamps were not archived for that time.
        if not any(r["availability_class"]=="VERIFIED_PREMATCH" for r in snapshots):
            warnings.append("NO_VERIFIED_PREMATCH_SOURCE_ARCHIVE")
        report={
           "schema":"kb3-step10-qa-v1",
           "dataset":{"league":LEAGUE,"season_start":SEASON,"fixtures":count,
                      "expected":expected_count,"teams":len(set(home)|set(away)),
                      "finished":sum(r["status"]=="FINISHED" for r in rows),
                      "first_kickoff_utc":rows[0]["kickoff_utc"] if rows else None,
                      "last_kickoff_utc":rows[-1]["kickoff_utc"] if rows else None,
                      "min_90min_home_goals":min((r["goals_home_90"] for r in rows if r["goals_home_90"] is not None),default=None),
                      "max_90min_home_goals":max((r["goals_home_90"] for r in rows if r["goals_home_90"] is not None),default=None),
                      "statuses":dict(sorted(Counter(r["status"] for r in rows).items())),
                      "provider_mappings":mapping["n"],
                      "source_snapshots":{"retrospective":retro,"verified_prematch":len(snapshots)-retro},
                      "match_statistics_rows":stats,"odds_rows":odds,"events_rows":events,
                      "feature_snapshots":feature_count},
           "sqlite":integrity,
           "fixture_rule_counts":dict(sorted(result_errors.items())),
           "critical_errors":sorted(set(issues)),
           "warnings":sorted(set(warnings)),
           "historical_integrity":"FAIL" if issues else "PASS",
           "prematch_feature_eligibility":"BLOCKED_NOT_AUDITED",
           "training_allowed":False,
        }
        report["result"]="FAIL" if issues else "PASS_WITH_COVERAGE_WARNINGS" if warnings else "PASS"
        return report

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--db",required=True,type=Path)
    p.add_argument("--outdir",required=True,type=Path)
    args=p.parse_args()
    report=analyze(args.db)
    args.outdir.mkdir(parents=True,exist_ok=True)
    manifest=args.outdir/"STEP10_QA.json"
    manifest.write_text(json.dumps(report,indent=2,sort_keys=True,ensure_ascii=False)+"\n",encoding="utf-8")
    print("KB3_STEP10_QA "+json.dumps({
        "result":report["result"],"dataset":report.get("dataset"),
        "critical_errors":report["critical_errors"],"warnings":report["warnings"],
        "training_allowed":report["training_allowed"]},sort_keys=True))
    if report["critical_errors"]:
        raise SystemExit(3)

if __name__=="__main__":
    main()
