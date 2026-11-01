"""Step19 RESEARCH ONLY: immutable quote contract, no API purchases or production use."""
from __future__ import annotations
import hashlib,json,math,sqlite3
from pathlib import Path
from decimal import Decimal,InvalidOperation
from datetime import datetime,timezone,timedelta
MARKETS={"1X2":{"1","X","2"},"BTTS":{"YES","NO"},"TOTAL":{"OVER","UNDER"},"AH":{"HOME","AWAY"}}
SCHEMA="""
CREATE TABLE IF NOT EXISTS step19_research_quotes(
 id_sha256 TEXT PRIMARY KEY,snapshot_sha256 TEXT NOT NULL,
 country TEXT NOT NULL,fixture_provider TEXT NOT NULL,native_match_id TEXT NOT NULL,
 bookmaker TEXT NOT NULL,market TEXT NOT NULL,selection TEXT NOT NULL,line_key TEXT NOT NULL,
 price_decimal TEXT NOT NULL,captured_utc TEXT NOT NULL,kickoff_utc TEXT NOT NULL,
 source_sha256 TEXT NOT NULL, provider_published_utc TEXT,
 independent_host_proof INTEGER NOT NULL DEFAULT 0 CHECK(independent_host_proof=0),
 production_approved INTEGER NOT NULL DEFAULT 0 CHECK(production_approved=0),
 UNIQUE(snapshot_sha256,selection)
);
CREATE TRIGGER IF NOT EXISTS odds_no_update BEFORE UPDATE ON step19_research_quotes
BEGIN SELECT RAISE(ABORT,'STEP19_ODDS_IMMUTABLE'); END;
CREATE TRIGGER IF NOT EXISTS odds_no_delete BEFORE DELETE ON step19_research_quotes
BEGIN SELECT RAISE(ABORT,'STEP19_ODDS_IMMUTABLE'); END;
"""
def require(x,msg):
    if not x:raise ValueError(msg)
def utc(s):
    require(isinstance(s,str),"SOURCE_UTC_TIMESTAMP_REQUIRED")
    d=datetime.fromisoformat(s.replace("Z","+00:00"))
    require(d.tzinfo is not None,"ODDS_TIMEZONE_MISSING")
    return d.astimezone(timezone.utc)
def decimal(raw,low,high):
    require(not isinstance(raw,bool),"BOOLEAN_IS_NOT_ODDS")
    try:n=Decimal(str(raw))
    except (ValueError,InvalidOperation):raise ValueError("ODDS_INVALID_NUMBER") from None
    require(n.is_finite() and Decimal(str(low))<=n<=Decimal(str(high)),"ODDS_OUT_OF_RANGE")
    return n
def sha(x):
    return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(",",":"),
         ensure_ascii=False).encode("utf-8")).hexdigest()
def validate(q,*,observed_cutoff):
    require(isinstance(q,dict),"ODDS_SOURCE_NOT_DICTIONARY")
    market=q.get("market");side=q.get("selection")
    require(market in MARKETS and side in MARKETS[market],"ODDS_WRONG_MARKET_OR_SELECTION")
    country=q.get("country")
    require(country in ("ESP","ITA","GER","FRA","NED","BEL","TUR","POL"),
            "ODDS_PROTECTED_ENGLISH_TEST")
    for field in ("bookmaker","native_match_id","fixture_provider"):
        v=q.get(field);require(isinstance(v,str) and 1<=len(v)<=128,"ODDS_IDENTITY_INVALID")
    observed=utc(q.get("captured_at_utc"));cutoff=utc(observed_cutoff);kick=utc(q.get("kickoff_utc"))
    require(observed<=cutoff<kick and observed+timedelta(minutes=90)<kick,
            "ODDS_NOT_PROVEN_EARLY_PREMATCH")
    require(q.get("provider_published_at_utc") is None,
            "ODDS_UNVERIFIED_PROVIDER_PUBLICATION")
    source=q.get("source_sha256")
    require(isinstance(source,str) and len(source)==64 and
            all(c in "0123456789abcdef" for c in source),"ODDS_SOURCE_HASH_INVALID")
    if market in ("TOTAL","AH"):
        line=decimal(q.get("line"),-20 if market=="AH" else 0,20)
        require((line*4)%1==0,"ODDS_LINE_NOT_QUARTER")
        line_key=format(line.normalize(),"f")
    else:
        require(q.get("line") is None,"ODDS_LINE_NOT_ALLOWED")
        line_key="NO_LINE"
    price=decimal(q.get("price_decimal"),1.01,1000)
    return {"country":country,"fixture_provider":q["fixture_provider"],
      "native_match_id":q["native_match_id"],"bookmaker":q["bookmaker"],
      "market":market,"selection":side,"line_key":line_key,
      "price_decimal":format(price.normalize(),"f"),
      "captured_utc":observed.isoformat(),"kickoff_utc":kick.isoformat(),
      "source_sha256":source,"provider_published_utc":None}
def freeze(db_path,quotes,*,observed_cutoff):
    p=Path(db_path)
    require(p.name not in ("kb3_forward_eight.sqlite","observed_xg.sqlite"),
            "NO_CHANGES_TO_LIVE_MODEL_DATABASE")
    rows=[validate(q,observed_cutoff=observed_cutoff) for q in quotes]
    p.parent.mkdir(parents=True,exist_ok=True)
    with sqlite3.connect(p) as db:
        db.executescript(SCHEMA)
        added=0
        for r in rows:
            scope={key:r[key] for key in ("country","fixture_provider","native_match_id",
                "bookmaker","market","line_key","captured_utc","source_sha256")}
            sid=sha(scope);qid=sha(r)
            cur=db.execute("""INSERT INTO step19_research_quotes(
              id_sha256,snapshot_sha256,country,fixture_provider,native_match_id,
              bookmaker,market,selection,line_key,price_decimal,captured_utc,
              kickoff_utc,source_sha256,provider_published_utc)
              VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,NULL)
              ON CONFLICT(id_sha256) DO NOTHING""",
              (qid,sid,r["country"],r["fixture_provider"],r["native_match_id"],
               r["bookmaker"],r["market"],r["selection"],r["line_key"],
               r["price_decimal"],r["captured_utc"],r["kickoff_utc"],r["source_sha256"]))
            added+=cur.rowcount
        require(db.execute("PRAGMA integrity_check").fetchone()[0]=="ok","ODDS_DB_CORRUPT")
        total=db.execute("SELECT COUNT(*) FROM step19_research_quotes").fetchone()[0]
    return {"new_quotes":added,"total_quotes":total,"host_time_attested":False,
       "formal_step19_pass":False,"M0_or_production_modified":False}
def no_vig_complete(db_path,sid):
    with sqlite3.connect(f"file:{Path(db_path).resolve()}?mode=ro",uri=True) as db:
        rows=db.execute("""SELECT market,selection,price_decimal FROM step19_research_quotes
             WHERE snapshot_sha256=?""",(sid,)).fetchall()
    if not rows:return None
    market=rows[0][0]
    require(all(r[0]==market for r in rows),"ODDS_MARKET_DRIFT")
    if len(rows)!=len(MARKETS[market]) or {r[1] for r in rows}!=MARKETS[market]:
        return None
    implied={side:1/float(Decimal(price)) for _,side,price in rows}
    total=sum(implied.values())
    require(math.isfinite(total) and total>0,"ODDS_BAD_NO_VIG_DENOMINATOR")
    return {"market":market,"overround":total-1,
      "no_vig_probabilities":{k:v/total for k,v in implied.items()},
      "ROI_not_estimated":True,"source_host_attestation":"NOT_PROVEN"}
