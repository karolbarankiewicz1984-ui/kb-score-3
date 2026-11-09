"""Exact 87-column comparison: original V3 shared builder vs independent retro algorithm.
Synthetic receipts ONLY: never use as PIT certification.
Run: python -m unittest tests.test_kb3_retro87_original_parity -v
"""
import unittest
from datetime import datetime,timedelta,timezone
from src.kb3_p1_shared_asof_features_v2 import build_shared_features

UTC=timezone.utc
def stamp(t): return t.isoformat().replace("+00:00","Z")
def baseline(target,cutoff,rows):
    """Recreate retro_87.py algorithm using exactly the same fixture inputs.
    This intentionally uses the actual retro algorithm: kickoff+3h maturity,
    Elo k20, home advantage65, scale400, season retention .85, and last-N windows.
    """
    hist={};ratings={};years={};counts={}
    def rate(team,year):
        old=years.get(team)
        if old is not None and year>old:
            ratings[team]=1500+(ratings.get(team,1500)-1500)*(.85**(year-old))
        years[team]=year
        return ratings.get(team,1500.)
    for row in sorted(rows,key=lambda r:(r["kickoff_utc"],str(r["fixture_id"]))):
        ko=datetime.fromisoformat(row["kickoff_utc"].replace("Z","+00:00"))
        if ko+timedelta(hours=3)>cutoff:continue
        a,b=str(row["home_team_id"]),str(row["away_team_id"])
        yr=row["season_start_year"];eh,ea=rate(a,yr),rate(b,yr)
        gh,ga=row["goals_home_90"],row["goals_away_90"]
        exp=1/(1+10**((ea-eh-65)/400))
        change=20*((1 if gh>ga else .5 if gh==ga else 0)-exp)
        hist.setdefault(a,[]).append((ko,yr,True,gh,ga,3 if gh>ga else 1 if gh==ga else 0,ea))
        hist.setdefault(b,[]).append((ko,yr,False,ga,gh,3 if ga>gh else 1 if ga==gh else 0,eh))
        counts[a]=counts.get(a,0)+1;counts[b]=counts.get(b,0)+1
        ratings[a]=eh+change;ratings[b]=ea-change
    out={}
    for side,team,venue in (("home",str(target["home_team_id"]),True),("away",str(target["away_team_id"]),False)):
        year=target["season_start_year"];allgames=hist.get(team,[]);vengames=[g for g in allgames if g[2]==venue]
        out["num:"+side+"_elo"]=round(rate(team,year),5)
        out["num:"+side+"_elo_games_available"]=len(allgames)
        out["num:"+side+"_games_available"]=len(allgames)
        out["num:"+side+"_prior_seasons_games_available"]=sum(g[1]<year for g in allgames)
        out["num:"+side+"_venue_games_available"]=len(vengames)
        out["miss:"+side+"_days_since_last_kickoff"]=int(not allgames)
        out["num:"+side+"_days_since_last_kickoff"]=round((cutoff-allgames[-1][0]).total_seconds()/86400,4) if allgames else None
        for cat,arr in (("all",allgames),("venue",vengames)):
            for n in (5,10,15):
                sub=arr[-n:];prefix=f"{side}_{cat}_{n}_";count=len(sub)
                out["miss:"+prefix+"history"]=int(count<n)
                out["num:"+prefix+"n"]=count
                for suffix,index in (("gf_avg",3),("ga_avg",4),("points_avg",5),("opponent_elo_avg",6)):
                    out["num:"+prefix+suffix]=round(sum(g[index] for g in sub)/count,6) if count else None
    out["num:elo_home_minus_away"]=round(out["num:home_elo"]-out["num:away_elo"],5)
    return out

def fixture():
    start=datetime(2026,10,1,12,tzinfo=UTC)
    target={"league":"ESP","fixture_id":"target","home_team_id":"A","away_team_id":"B",
            "kickoff_utc":stamp(start+timedelta(days=30)),"season_start_year":2026}
    cutoff=start+timedelta(days=30,hours=-2)
    rows=[]
    for i in range(25):
        ko=start+timedelta(days=i)
        h,a=(("A","C") if i%2==0 else ("D","B"))
        rows.append({"league":"ESP","fixture_id":f"r{i}","home_team_id":h,"away_team_id":a,
          "kickoff_utc":stamp(ko),"season_start_year":2026,"status":"FINISHED",
          "goals_home_90":i%4,"goals_away_90":(i+1)%3,
          "result_receipt":{"source_class":"NETWORK_OBSERVED",
            "observed_completed_at_utc":stamp(ko+timedelta(hours=3,minutes=1)),
            "captured_at_utc":stamp(ko+timedelta(hours=3,minutes=2)),
            "source_sha256":"a"*64}})
    receipt={"source_class":"NETWORK_OBSERVED",
             "observed_completed_at_utc":stamp(cutoff-timedelta(minutes=10)),
             "source_sha256":"b"*64}
    return target,cutoff,rows,receipt

class Retro87Parity(unittest.TestCase):
    def test_all_87_values_identical_or_report_exact_differences(self):
        target,cutoff,rows,receipt=fixture()
        original=build_shared_features(purpose="FORWARD",target=target,cutoff_utc=stamp(cutoff),
            target_receipt=receipt,predecessor_rows=rows)
        retro=baseline(target,cutoff,rows)
        values={"num:"+k:v for k,v in original["features"].items() if "xg" not in k}
        values.update({"miss:"+k:int(v) for k,v in original["missing_flags"].items() if "xg" not in k})
        self.assertEqual(87,len(values))
        self.assertEqual(set(values),set(retro))
        diffs={k:(values[k],retro[k]) for k in sorted(values) if values[k]!=retro[k]}
        print("RETRO87_ORIGINAL_BUILDER_PARITY",len(values),"MATCHED",len(values)-len(diffs),"DIFFERENCES",diffs)
        self.assertFalse(diffs,"Independent retro feature algorithm differs from original shared builder")

if __name__=="__main__":unittest.main()
