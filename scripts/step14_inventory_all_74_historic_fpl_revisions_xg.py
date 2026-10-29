"""Step14: scan ALL 74 exact historical FPL fixture revisions and player-xG blobs.

A GitHub commit timestamp does NOT establish publication before a match.
Only the 12 independently GHArchive-server-witnessed immutable source SHAs
already certified in this repo may provide source-clock-qualified research.
All other revisions are inventoried / xG inspected but are NEVER promoted to
PIT. No actual original PitchAPI M1 training, 2026/27 TEST, or odds.
"""
from __future__ import annotations
import argparse,csv,hashlib,io,json,math,os,time
from collections import Counter,defaultdict
from concurrent.futures import ThreadPoolExecutor,as_completed
from pathlib import Path
from urllib.error import HTTPError,URLError
from urllib.parse import quote
from urllib.request import Request,urlopen
from scripts.step14_full_1140_native_public_pit_lineage import independently_pinned_sources
from scripts.step14_train_760_decimal_FPL_FT_corrected_v2 import goal

ROOT=Path(__file__).resolve().parents[1]
REPO="vaastav/Fantasy-Premier-League"
SCHEMA="kb3-step14-all-74-github-fpl-fixture-revisions-and-public-player-xg-audit-v1"
# PIN exact 38 + 36 fixture-CSV revision commits. These are NOT publication receipts!
REVISIONS={
 "2023-24":"""204c134d8e90e2b6e69ec252aa3ef6f10f21e73c 5218c9f360c0415d7272775239f88ab0eb15e91d 2981ebc1630d6e0211c5847731c8fb79cecba785 8f5194d666f608200916f2b62f8976e8c8beff87 6f1e864e5a5bb58a0ad92a257e86df7a7d4816db d7e0beda3436c5051116e1aeef652e96119ebf92 436f1ff2d306783d3e3892dc3d3ce21712cbc08e 7d6f6aafa94a937116f308a2393fb12e86c5771f 4e6447daccfb053a496e4aebd37d264dfa949676 cbf39345fdfa826870e37b1b2c777b543fed56d2 8a90a7cbf8dd336676a5d599605fe4fd5f9bcc40 446af195d2ee324a1217f34a5a2b591189efc983 f061aafa88a921dd70fd2b0f72b8020889d8e589 73cf14c852c5bbafde20ba11ebc5acd6eff965aa 5f49140e78b2052634abae57ce15e40f41dc32f7 8a0d23451ea7c07699ba903feb364e8fe0085c0e 546143eb5d0ae6d250e074374152e8be4b15719b 15783a5630abadb309ff4c3edbb3dc32e6a2b426 2f06c2ae70511a7075d02913784ec77a5fb21aa1 d8a6fc58722beaa625195de9d51a0333dcb46439 62f7b7c0b2d897834613475b15d6dc3301f13e70 392588ec1664432358f9481b81c3a8c1d53a60a3 d54ac4c7b35ccca5fcf2d46ee62362a67efa45e8 c4f66ee30ef026bb7e8b7184b2427f9708c77d74 acee0e28f8b201062270d709a7d72e4787680872 caf799bb68f58fb26ac80d8cb762c353891232f5 028f925c32fabb34798e416c569070d0cae329a2 e92d9881f2ef025a7a1093e47fdf02d9aa2f8655 615da45c450fb13993b7e8da4c8388d7e2f57703 32184fc221871431d8215c5dc8385af0eda7bdde 96fbc38ee6e36e3a7250081a787b65a1a27c944d 8b05861fb33ee89bae34c2b6d06564449a5885db b9122f8c98f10a8217e5fb67bc4de447f6c685d5 b0ec80fec6916117225a6fbee11c35d8773c6f94 2abff9370632b3b36bbdfa0870805b60fb392ef0 2749a5964950b3b34992cebde0351ac9e09fb54f be15e285f106d1becc6f24c0c470ec9ada8c935a 9ba09ce183b51e13c26f44295ac10803426ab24f""".split(),
 "2024-25":"""a7089bab28e2a6012cde62b4fbd692f975792a55 e3a961c6b47342884268f59d6cb1730b3be194b2 3558a3310103f24e17f02d684479067a2de099c5 761d80463ce8b7a74e1e67f7763910b4c4e14a10 29e6c2f4590b1a03f218552ca676b9495539cfdc c6f14b56fd810fcde3e9faec1c858c659142b99e f89612e6799fb3f8c91939aed87a998078dfb4b6 58de8250c856e3476d45557422b257a3659b2b26 a8fce2b6ef72a5f44639e2c0f9333e86c827db58 814519241dbac0cf82eafa6ce227821e705f652b a0b8a68297efcf2a9b13b9e132a70913d590b246 58e46cd9b9fe439d875ed56bd1a398c69b08b570 0f5da695398c293dca037c36c703fce88a161195 b9618a5d9eebce9bc5ab0e6683bfb8fc420ac848 c56971db31bd27acbc0ec3a96bc00da7870d68a7 e369a3a0943eb6c7cb240053c0e2827f91b57eaa 36f07bb50c876ac49255650fd4478c856f086735 c9a593826e077670fa300e825022b2979282d069 74d804715f821380314efc128bc3e1037750f23f dfdae0e489f8520228a4ffeae11fc70d6aef7804 651e9adea9e420416fdde96faf920de232383036 bc76591d36196c0ef59b34db42d0167867686298 27c87bd13ef72dd8ed2ad6584a0d8d20f070f559 e3135daf0fcb706cc41f237e5c691517bd3432c1 d7a9ea76d98e7453bdca8893224da894b9b55e28 2840028eaea97d5255e96620ad2e06942cc8fe90 80b1a9fd9efc30dab63fb4aba8afe3f1c6273e75 d0f7342e2f5f7176d507badb10ee2db76f564409 57caf7e165ba47b48de9f307785aac79cb03b8af f42ed38d279afc705448ebc2b89e48838a0fdfba 3c76203d2997a89f0735d2591e76e7c849a2f491 9d4b5d89af45f85be8c9215f713000072bdbe3dd ec2a907dae6e97f76406c742a15e56653f3d170e 403e10b7b661252698745d1101d1086cec31e0f1 c43f0d83d2b9d769c8dadb64959c16b01713cfaa 754b30c54394651bf6722fe47b4896d44c355ddd""".split()
}
if [len(REVISIONS[x]) for x in ("2023-24","2024-25")]!=[38,36]:
    raise ValueError("NOT_PINNED_EXACT_74_REVISION_COUNT")
if len(set(REVISIONS["2023-24"]+REVISIONS["2024-25"]))!=74:
    raise ValueError("REVISIONS_NOT_DISTINCT")
class RevisionXGError(ValueError):pass

def _get(url,limit=40_000_001,optional=False,token=None):
    req=Request(url,headers={"User-Agent":"KB3-step14-74-public-old-xg",
          **({"Authorization":"Bearer "+token} if token and "api.github.com" in url else {})})
    for retry in range(3):
        try:
            with urlopen(req,timeout=45) as f:
                data=f.read(limit+1)
                if len(data)>limit:raise RevisionXGError("RAW_BLOB_TOO_LARGE")
                return data
        except HTTPError as e:
            if optional and e.code==404:return None
            if e.code in (403,429,500,502,503,504) and retry<2:
                time.sleep(retry+1);continue
            raise
        except (URLError,TimeoutError):
            if retry<2:time.sleep(retry+1);continue
            raise
    raise RevisionXGError("REQUEST_FAILED")

def _uri(sha,path):
    return f"https://raw.githubusercontent.com/{REPO}/{sha}/{path}"

def _history():
    token=os.environ.get("GITHUB_TOKEN")
    for season,until in (("2023-24","2024-06-01T00:00:00Z"),
                         ("2024-25","2025-06-01T00:00:00Z")):
        u=f"https://api.github.com/repos/{REPO}/commits?path=data%2F{season}%2Ffixtures.csv&until={quote(until)}&per_page=100"
        js=json.loads(_get(u,limit=5_000_000,token=token))
        found=[x["sha"] for x in js]
        if found!=REVISIONS[season]:
            raise RevisionXGError("GITHUB_HISTORICAL_FIXTURE_REVISION_LIST_DRIFT")
        for x in js:
            yield {"season":season,"sha":x["sha"],
                   "git_committer_utc_NOT_independent_publication":x["commit"]["committer"]["date"]}

def _player_agg(players,fixtures):
    """Research aggregation; fails closed at row/side errors without pretending PIT."""
    fpl={}
    for row in fixtures:
        if not row.get("id") or not row.get("team_h") or not row.get("team_a"):
            continue
        if row["id"] in fpl:raise RevisionXGError("DUPLICATE_FPL_FIXTURE")
        fpl[row["id"]]=row
    source=io.StringIO(players.decode("utf-8-sig"),newline="")
    rd=csv.DictReader(source)
    required={"fixture","element","opponent_team","was_home","expected_goals","minutes"}
    if not required<=set(rd.fieldnames or []):raise RevisionXGError("OLD_XG_REQUIRED_FIELDS_MISSING")
    seen=set();tot=defaultdict(float);members=Counter();active=Counter();rows=0;invalid=0
    for x in rd:
        rows+=1;fid=x["fixture"];fixture=fpl.get(fid)
        if fixture is None or fixture["finished"]!="True":
            invalid+=1;continue
        if x["was_home"] in ("True","true","TRUE","1"):home=True
        elif x["was_home"] in ("False","false","FALSE","0"):home=False
        else:invalid+=1;continue
        side=fixture["team_h"] if home else fixture["team_a"]
        opposite=fixture["team_a"] if home else fixture["team_h"]
        if x["opponent_team"]!=opposite or not x["element"]:invalid+=1;continue
        key=(fid,side,x["element"])
        if key in seen:invalid+=1;continue
        seen.add(key)
        try:val=float(x["expected_goals"]);minutes=float(x["minutes"])
        except (TypeError,ValueError):invalid+=1;continue
        if not all(math.isfinite(z) for z in (val,minutes)) or not 0<=val<=20 or not 0<=minutes<=130:
            invalid+=1;continue
        tot[(fid,side)]+=val
        members[(fid,side)]+=1
        if minutes>0:active[(fid,side)]+=1
    # A bad player record could change xG; don't certify any sides
    # from a source with any invalid rows.
    quality="PASS" if invalid==0 else "SOURCE_HAS_INVALID_PLAYER_XG_ROWS"
    usable={k:round(v,4) for k,v in tot.items()
            if active[k]>=11 and members[k]>=11} if quality=="PASS" else {}
    return {"player_rows":rows,"invalid_rows":invalid,
            "side_records_valid_at_least_11_played":len(usable),
            "all_xg_rows_strict_validation":quality},usable

def scan_one(meta,verified):
    sha,season=meta["sha"],meta["season"]
    root=f"data/{season}"
    try:
        fraw=_get(_uri(sha,f"{root}/fixtures.csv"),limit=3_000_000)
        if fraw is None:raise RevisionXGError("MISSING_FIXTURE_RAW")
        fixtures=list(csv.DictReader(io.StringIO(fraw.decode("utf-8-sig"),newline="")))
        if len(fixtures)!=380 or len({z["id"] for z in fixtures})!=380:
            raise RevisionXGError("NOT_FULL_380_GRID")
        completed=sum(z["finished"]=="True" for z in fixtures)
        pin=verified.get(sha)
        if pin and (hashlib.sha256(fraw).hexdigest()!=pin["sha"] or completed!=pin["ft"]):
            raise RevisionXGError("PUBLISHED_PINNED_FT_BYTES_MISMATCH")
        path=f"{root}/gws/merged_gw.csv"
        raw=_get(_uri(sha,path),limit=40_000_000,optional=True)
        result={**meta,"fixture_sha256":hashlib.sha256(fraw).hexdigest(),
           "source_finished_fixture_count":completed,
           "old_merged_gw_player_xg_exists":bool(raw),
           "old_merged_gw_player_xg_sha256":hashlib.sha256(raw).hexdigest() if raw else None,
           "old_merged_gw_bytes":len(raw) if raw is not None else None,
           "independent_publication_upper_bound_clock_proven":True,
           "direct_GHArchive_push_proven":pin is not None,
           "independent_GHArchive_push_utc":pin["push"] if pin else None,
           "independent_GHArchive_event_id":str(pin.get("event",pin.get("event_id"))) if pin else None,
           "original_pitchapi_team_xg_equivalence_proven":False}
        if raw:
            try:
                audited,tot=_player_agg(raw,fixtures)
                result.update(audited)
                result["eligible_for_historical_RESEARCH_xg_source"]=audited["all_xg_rows_strict_validation"]=="PASS"
            except (UnicodeError,RevisionXGError,csv.Error) as e:
                result.update({"player_xg_audit_failure":type(e).__name__+":"+str(e),
                               "eligible_for_historical_RESEARCH_xg_source":False})
        else:
            result["eligible_for_historical_RESEARCH_xg_source"]=False
            result["player_xg_audit_failure"]="OLD_MERGED_GW_EMPTY_OR_MISSING"
        return result
    except Exception as e:
        return {**meta,"scan_status":"BLOCKED","failure":type(e).__name__+":"+str(e),
                "independent_publication_upper_bound_clock_proven":True,
                "direct_GHArchive_push_proven":sha in verified,
                "eligible_for_historical_RESEARCH_xg_source":False}

def run():
    witnessed=[x for x in independently_pinned_sources() if x.get("provider","FPL")=="FPL"]
    if len(witnessed)!=11 or len({x["commit"] for x in witnessed})!=11:
        raise RevisionXGError("EXISTING_EXTERNAL_GHARCHIVE_11_DIRECT_FPL_PROOFS_CHANGED")
    proven={x["commit"]:x for x in witnessed}
    ancestry=json.loads((ROOT/"data/audits/STEP14_ALL_74_FPL_REVISIONS_ANCHORED_GHARCHIVE_2026-10-29.json").read_text())
    if (ancestry.get("hist_publication_qualified_ancestor_revisions")!=74
        or not ancestry.get("all_74_source_revisions_inventoried")
        or ancestry.get("not_externally_witnessed_revisions")!=0):
        raise RevisionXGError("UNTRUSTED_GHARCHIVE_ANCESTRY_PROOF")
    ancestors={x["sha"]:x for x in ancestry["fpl_revisions"]}
    if (len(ancestors)!=74 or set(ancestors)!=set(REVISIONS["2023-24"]+REVISIONS["2024-25"])
        or not all(x["certified_before_target"] and x.get("witnessed_public_by_utc") for x in ancestors.values())):
        raise RevisionXGError("PINNED_74_HISTORIC_ANCESTRY_SHAS_DRIFT")
    if not set(proven)<=set(ancestors):raise RevisionXGError("DIRECT_GHARCHIVE_SHAS_MISSING")
    history=list(_history())
    for x in history:
        x["GHArchive_proven_public_BY_utc_NOT_initial_publication"]=ancestors[x["sha"]]["witnessed_public_by_utc"]
        x["publication_proof"]="GIT_ANCESTOR_OF_INDEPENDENTLY_TIMESTAMPED_GHARCHIVE_PUSH"
        x["direct_old_GHArchive_push_event_confirmed"]=x["sha"] in proven
    scans=[]
    with ThreadPoolExecutor(max_workers=9) as executor:
        tasks=[executor.submit(scan_one,x,proven) for x in history]
        for future in as_completed(tasks):
            scans.append(future.result())
    scans.sort(key=lambda x:(x["season"],REVISIONS[x["season"]].index(x["sha"])))
    if len(scans)!=74:raise RevisionXGError("74_REVISION_SCAN_INCOMPLETE")
    per=Counter(x["season"] for x in scans)
    recovered=[x for x in scans if x.get("old_merged_gw_player_xg_exists")]
    valid=[x for x in scans if x.get("eligible_for_historical_RESEARCH_xg_source")]
    return {"schema":SCHEMA,"repo":REPO,
      "exact_revisions_pinned":74,"revision_counts_by_season":dict(per),
      "raw_old_player_xg_merged_files_available":len(recovered),
      "old_player_xg_strict_sources_with_historic_upper_bound_witness":len(valid),
      "previously_direct_GHArchive_clock_certified_FPL_commits":len(proven),
      "other_revisions_proven_public_no_later_than_GHArchive_witnessed_ancestor":74-len(proven),
      "all_74_GHArchive_ancestry_upper_bounds_verified":True,
      "original_committer_date_NOT_accepted_as_publication_clock":True,
      "distinct_ancestor_proven_player_xg_source_SHAs":[x["sha"] for x in valid],
      "no_automatic_promotion_to_original_PitchAPI_team_xG":True,
      "no_original_catboost_training":True,"GATE14":"PENDING",
      "TEST_2026_27_accessed":False,"revisions":scans}

def main():
    p=argparse.ArgumentParser();p.add_argument("--out",required=True);a=p.parse_args()
    out=Path(a.out)
    if out.exists():raise RevisionXGError("APPEND_ONLY")
    result=run()
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(result,ensure_ascii=False,sort_keys=True,indent=2)+"\n")
    print(json.dumps({k:result[k] for k in ("exact_revisions_pinned",
      "revision_counts_by_season","raw_old_player_xg_merged_files_available",
      "old_player_xg_strict_sources_with_historic_upper_bound_witness",
      "previously_direct_GHArchive_clock_certified_FPL_commits")},sort_keys=True))
if __name__=="__main__":main()
