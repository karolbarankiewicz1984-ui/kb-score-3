"""KB Score 3.0 / Step 09 — auditable, resumable retrospective fixture import.

Only API-Football league 39 season 2024 in this pilot. No model training.
Raw API responses and SQLite outputs must NOT be committed to Git.
"""
import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import urllib.error
import urllib.parse
import urllib.request

from src.kb3_storage import connect, file_hash, initialize, verify_database

LEAGUE_ID = 39
SEASON = 2024
EXPECTED_COUNT = 380
BASE = "https://v3.football.api-sports.io"
TEAM_VALID_FROM = "1900-01-01T00:00:00Z"
STATUS_MAP = {
    "NS": "SCHEDULED", "TBD": "SCHEDULED",
    "1H": "LIVE", "HT": "LIVE", "2H": "LIVE", "ET": "LIVE",
    "BT": "LIVE", "P": "LIVE", "SUSP": "LIVE", "INT": "LIVE",
    "FT": "FINISHED", "AET": "FINISHED", "PEN": "FINISHED",
    "PST": "POSTPONED", "CANC": "CANCELLED", "ABD": "ABANDONED",
    "AWD": "AWARDED", "WO": "AWARDED",
}

class ImportConflict(ValueError):
    pass

class SimulatedInterruption(Exception):
    pass

def utc_now():
    return dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")

def canonical_bytes(obj):
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")

def sha256(data):
    return hashlib.sha256(data).hexdigest()

def parse_kickoff(raw):
    if not isinstance(raw, str):
        raise ImportConflict("MISSING_KICKOFF")
    try:
        date = dt.datetime.fromisoformat(raw.replace("Z", "+00:00"))
        if date.tzinfo is None:
            raise ValueError("naive date")
        return date.astimezone(dt.timezone.utc).isoformat().replace("+00:00", "Z")
    except (TypeError, ValueError) as exc:
        raise ImportConflict("INVALID_KICKOFF") from exc

def nonnegative_or_none(value):
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ImportConflict("INVALID_GOALS")
    return value

def parse_rows(payload, *, expected_count=EXPECTED_COUNT, league_id=LEAGUE_ID, season=SEASON):
    if not isinstance(payload, dict):
        raise ImportConflict("INVALID_API_RESPONSE")
    if payload.get("errors"):
        raise ImportConflict("API_ERRORS_PRESENT")
    if (payload.get("paging") or {}).get("total", 1) != 1:
        raise ImportConflict("PAGINATED_FIXTURE_LIST_INCOMPLETE")
    data = payload.get("response")
    if not isinstance(data, list):
        raise ImportConflict("MISSING_RESPONSE_ARRAY")
    if len(data) != expected_count:
        raise ImportConflict("COUNT_MISMATCH_%s_EXPECTED_%s" % (len(data), expected_count))
    rows = []
    ids = set()
    for item in data:
        fixture = item.get("fixture") or {}
        league = item.get("league") or {}
        teams = item.get("teams") or {}
        fid = fixture.get("id")
        if (not isinstance(fid, int) or isinstance(fid, bool) or fid <= 0
                or fid in ids):
            raise ImportConflict("DUPLICATE_OR_INVALID_PROVIDER_FIXTURE_ID")
        ids.add(fid)
        if league.get("id") != league_id or league.get("season") != season:
            raise ImportConflict("LEAGUE_SEASON_MISMATCH")
        home, away = teams.get("home") or {}, teams.get("away") or {}
        hid, aid = home.get("id"), away.get("id")
        if not all(isinstance(v, int) and not isinstance(v, bool) and v > 0 for v in (hid, aid)):
            raise ImportConflict("INVALID_TEAM_ID")
        if hid == aid:
            raise ImportConflict("HOME_EQUALS_AWAY")
        if not all(isinstance(v, str) and v.strip() for v in (home.get("name"), away.get("name"))):
            raise ImportConflict("INVALID_TEAM_NAME")
        raw_status = (fixture.get("status") or {}).get("short")
        if raw_status not in STATUS_MAP:
            raise ImportConflict("UNSUPPORTED_STATUS_%s" % raw_status)
        status = STATUS_MAP[raw_status]
        # 90-minute result: NEVER substitute AET/PEN totals for regulation scores.
        score = (item.get("score") or {}).get("fulltime") or {}
        if raw_status == "FT" and (score.get("home") is None or score.get("away") is None):
            score = item.get("goals") or {}
        hg = nonnegative_or_none(score.get("home"))
        ag = nonnegative_or_none(score.get("away"))
        if status == "FINISHED" and (hg is None or ag is None):
            raise ImportConflict("FINISHED_WITHOUT_90MIN_RESULT")
        if status != "FINISHED":
            # Do not silently record potentially partial/live match goals as settled 90m.
            hg, ag = None, None
        rows.append({
            "provider_fixture_id": str(fid),
            "home_provider_id": str(hid), "home_name": home["name"].strip(),
            "away_provider_id": str(aid), "away_name": away["name"].strip(),
            "kickoff_utc": parse_kickoff(fixture.get("date")),
            "status": status, "goals_home_90": hg, "goals_away_90": ag,
            "source_status": raw_status,
        })
    return sorted(rows, key=lambda x: int(x["provider_fixture_id"]))

def fetch_api(key, *, league_id=LEAGUE_ID, season=SEASON):
    if not key:
        raise RuntimeError("MISSING_API_FOOTBALL_KEY")
    params = urllib.parse.urlencode({"league": league_id, "season": season})
    req = urllib.request.Request(
        BASE + "/fixtures?" + params,
        headers={"x-apisports-key": key, "Accept": "application/json",
                 "User-Agent": "KBScore3-Step09-Pilot/1.0"},
    )
    with urllib.request.urlopen(req, timeout=35) as result:
        content = result.read(6_000_001)
        if len(content) > 6_000_000:
            raise RuntimeError("OVERSIZED_API_RESPONSE")
        return json.loads(content)

def reference_ids(c, now, response_hash, *, league_id=LEAGUE_ID,
                  season=SEASON, competition_name="Premier League", country="England"):
    c.execute("INSERT OR IGNORE INTO providers(name, created_utc) VALUES (?,?)", ("API-Football", now))
    provider = c.execute("SELECT provider_id FROM providers WHERE name=?", ("API-Football",)).fetchone()[0]
    c.execute("INSERT OR IGNORE INTO competitions(name,country,type) VALUES (?,?,?)",
              (competition_name, country, "LEAGUE"))
    comp = c.execute("SELECT competition_id FROM competitions WHERE name=? AND country=? AND type=?",
                     (competition_name, country, "LEAGUE")).fetchone()[0]
    c.execute("INSERT OR IGNORE INTO seasons(competition_id,start_year,season_label) VALUES (?,?,?)",
              (comp, season, f"{season}/{str(season+1)[-2:]}"))
    season_pk = c.execute("SELECT season_id FROM seasons WHERE competition_id=? AND start_year=?",
                          (comp, season)).fetchone()[0]
    snapshot_id = f"api-football-fixtures-{league_id}-{season}-" + response_hash[:24]
    c.execute("""
        INSERT OR IGNORE INTO source_snapshots
            (snapshot_id,provider_id,endpoint_label,captured_at_utc,source_data_hash,availability_class)
        VALUES (?,?,?,?,?,'RETROSPECTIVE')
    """, (snapshot_id,provider,f"fixtures?league={league_id}&season={season}",now,response_hash))
    return provider,season_pk,snapshot_id

def get_team(c, provider, external_id, name):
    old = c.execute("""
        SELECT team_id FROM team_provider_map
        WHERE provider_id=? AND external_team_id=?
        ORDER BY valid_from_utc DESC LIMIT 1
    """, (provider, external_id)).fetchone()
    if old:
        return old[0]
    c.execute("INSERT INTO teams(canonical_name,country) VALUES (?,?)",(name,"England"))
    tid=c.execute("SELECT last_insert_rowid()").fetchone()[0]
    c.execute("""
        INSERT INTO team_provider_map
           (provider_id,external_team_id,team_id,valid_from_utc)
        VALUES (?,?,?,?)
    """,(provider,external_id,tid,TEAM_VALID_FROM))
    return tid

def import_rows(db, rows, response_hash, *, stop_after=None,
                league_id=LEAGUE_ID, season=SEASON,
                competition_name="Premier League", country="England"):
    initialize(db)
    now=utc_now()
    with connect(db) as c:
        provider,season_pk,snapshot_id=reference_ids(
            c,now,response_hash,league_id=league_id,season=season,
            competition_name=competition_name,country=country)
    inserted=0
    reused=0
    for row in rows:
        with connect(db) as c:
            home=get_team(c,provider,row["home_provider_id"],row["home_name"])
            away=get_team(c,provider,row["away_provider_id"],row["away_name"])
            existing=c.execute("""
                SELECT f.fixture_id,f.season_id,f.home_team_id,f.away_team_id,
                       f.kickoff_utc,f.status,f.goals_home_90,f.goals_away_90
                FROM fixture_provider_map m JOIN fixtures f ON f.fixture_id=m.fixture_id
                WHERE m.provider_id=? AND m.provider_fixture_id=?
                  AND m.match_quality='STRICT' AND m.review_status='APPROVED'
            """,(provider,row["provider_fixture_id"])).fetchone()
            expected=(season_pk,home,away,row["kickoff_utc"],row["status"],
                      row["goals_home_90"],row["goals_away_90"])
            if existing:
                if tuple(existing[1:]) != expected:
                    raise ImportConflict("EXISTING_FIXTURE_DIFFERS_REVIEW_REQUIRED")
                reused+=1
            else:
                # Fail closed on unresolved/conflicting mappings rather than promote REVIEW.
                ambiguous=c.execute("""
                    SELECT match_quality FROM fixture_provider_map
                    WHERE provider_id=? AND provider_fixture_id=?
                """,(provider,row["provider_fixture_id"])).fetchone()
                if ambiguous:
                    raise ImportConflict("EXISTING_UNAPPROVED_PROVIDER_MAPPING")
                c.execute("""
                    INSERT INTO fixtures(season_id,home_team_id,away_team_id,kickoff_utc,
                        status,goals_home_90,goals_away_90,result_source,created_utc,updated_utc)
                    VALUES (?,?,?,?,?,?,?,?,?,?)
                """,(season_pk,home,away,row["kickoff_utc"],row["status"],
                     row["goals_home_90"],row["goals_away_90"],"API-Football",now,now))
                fixture_id=c.execute("SELECT last_insert_rowid()").fetchone()[0]
                c.execute("""
                    INSERT INTO fixture_provider_map
                       (provider_id,provider_fixture_id,fixture_id,match_quality,
                        review_status,source_snapshot_id,kickoff_utc,reviewed_at_utc,reviewer_ref)
                    VALUES (?,?,?,'STRICT','APPROVED',?,?,?,?)
                """,(provider,row["provider_fixture_id"],fixture_id,snapshot_id,
                     row["kickoff_utc"],now,"AUTHORITATIVE_PROVIDER_SELF_ID"))
                inserted+=1
        if stop_after is not None and inserted + reused == stop_after:
            raise SimulatedInterruption("TEST_INTERRUPTION_AFTER_COMMIT")
    with connect(db) as c:
        verify_database(c)
        matches=c.execute("""
            SELECT COUNT(*) FROM fixture_provider_map m
            JOIN fixtures f ON f.fixture_id=m.fixture_id
            WHERE m.provider_id=? AND f.season_id=?
              AND m.match_quality='STRICT' AND m.review_status='APPROVED'
        """,(provider,season_pk)).fetchone()[0]
        total=c.execute("SELECT COUNT(*) FROM fixtures WHERE season_id=?",(season_pk,)).fetchone()[0]
        if matches != len(rows) or total != len(rows):
            raise ImportConflict("COUNT_AFTER_IMPORT_MISMATCH")
    return {"inserted":inserted,"reused":reused,"total":total,
            "snapshot_id":snapshot_id,"fixture_mapping_count":matches}

def pilot(outdir, *, payload):
    outdir=Path(outdir)
    outdir.mkdir(parents=True,exist_ok=True)
    rows=parse_rows(payload)
    response_hash=sha256(canonical_bytes(payload))
    rows_hash=sha256(canonical_bytes(rows))
    # Same input is reused; a second API call might return revisions, not an idempotency test.
    database=outdir/"premier-league-2024-25.sqlite3"
    first=import_rows(database,rows,response_hash)
    second=import_rows(database,rows,response_hash)
    if first["inserted"] != EXPECTED_COUNT or second["inserted"] != 0 or second["reused"] != EXPECTED_COUNT:
        raise ImportConflict("IDEMPOTENCE_TEST_FAILED")
    resume_db=outdir/"resume-test.sqlite3"
    interrupted=False
    try:
        import_rows(resume_db,rows,response_hash,stop_after=17)
    except SimulatedInterruption:
        interrupted=True
    if not interrupted:
        raise ImportConflict("INTERRUPTION_TEST_FAILED")
    resumed=import_rows(resume_db,rows,response_hash)
    if resumed["inserted"] != EXPECTED_COUNT - 17 or resumed["reused"] != 17:
        raise ImportConflict("RESUME_TEST_FAILED")
    with connect(resume_db) as c:
        verify_database(c)
    statuses={}
    for row in rows:
        statuses[row["source_status"]]=statuses.get(row["source_status"],0)+1
    output={
       "schema":"kb3-step09-import-pilot-v1",
       "classification":"RETROSPECTIVE_NOT_PREMATCH",
       "competition":"Premier League", "league_id":LEAGUE_ID,
       "season_start":SEASON, "expected":EXPECTED_COUNT,
       "source_rows":len(rows), "unique_provider_fixtures":len({r["provider_fixture_id"] for r in rows}),
       "provider_response_sha256":response_hash, "canonical_rows_sha256":rows_hash,
       "sqlite_sha256":file_hash(database), "sqlite_bytes":database.stat().st_size,
       "first_import":first,"repeat_import":second,
       "resume_after_17":resumed, "status_counts":statuses,
       "db_schema_version":1,
       "backup_classification":"TEMPORARY_ACTIONS_ARTIFACT_NOT_OFFSITE_BACKUP",
       "offsite_encrypted_archive":"NOT_YET_IMPLEMENTED",
       "gate09":"PENDING_DURABLE_ARCHIVE",
    }
    manifest=outdir/"step09-manifest.json"
    manifest.write_text(json.dumps(output,ensure_ascii=False,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    return output

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--outdir",default="audit/step09")
    args=parser.parse_args()
    payload=fetch_api(os.environ.get("API_FOOTBALL_KEY","").strip())
    summary=pilot(args.outdir,payload=payload)
    # No secrets or raw API record contents in logs.
    print("GATE09_PILOT_RESULT "+json.dumps({
        k:summary[k] for k in ("source_rows","expected","unique_provider_fixtures",
          "provider_response_sha256","canonical_rows_sha256","sqlite_sha256",
          "first_import","repeat_import","resume_after_17","status_counts",
          "backup_classification","gate09")
    },sort_keys=True))
if __name__=="__main__":
    main()
