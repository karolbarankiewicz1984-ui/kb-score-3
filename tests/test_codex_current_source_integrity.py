"""Independent current-main regressions; not the missing historical R5 suite."""
import copy
import json
import sqlite3
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from pitch_pair_fixtures import stats
from scripts.pitchapi_step06_audit import parse_shots, to_plain
from scripts.kb3_historical_pitchapi_backfill import native_xg_verified
from src.kb3_pit_ledger import canonical, hexdigest
from src.kb3_pitch_native import verify_native_shots
from src.kb3_pitch_native_ledger import record, verify, shots_asof
from src.kb3_pitch_source_pair import validate_pair, validate_receipts
from src.kb3_pitch_uefa_evidence import add_observation
from src.kb3_step17_xg_capture import parse_pair, store_samples, connect
from test_step11_pitch_native_ledger import season

MID="m_000000"; HOME="t_000000"; AWAY="t_000001"

def shot_feed():
    return {"data":{"match_id":MID,"periods":[{"period":"All","shots":[
        {"id":"s_1","team_id":HOME,"expected_goals":.4},
        {"id":"s_2","team_id":AWAY,"expected_goals":.7}]}]}}

def stat_feed():
    return stats(MID,HOME,AWAY,.4,.7)

def clock(seconds):
    return (datetime.now(timezone.utc)+timedelta(seconds=seconds)).isoformat().replace("+00:00","Z")

def receipts(shots,stat):
    out=[]
    for kind,payload,start,end in (("shots",shots,-12,-11),("stats",stat,-10,-9)):
        add_observation(out,resource="pitchapi:step17xg:"+kind+":"+MID,
                        payload=payload,started=clock(start),completed=clock(end))
    return out

def resign(receipt):
    receipt["chain_sha256"]=hexdigest(canonical({k:v for k,v in receipt.items() if k!="chain_sha256"}))

class SourcePairTests(unittest.TestCase):
    def validate(self,shot=None,stat=None):
        return validate_pair(shot if shot is not None else shot_feed(),
                             stat if stat is not None else stat_feed(),MID,HOME,AWAY)

    def test_sdk_typed_stats_preserve_string_counts(self):
        from pitchapi.models.stats import MatchStats,MatchStatPeriod,MatchStatGroup,MatchStatItem
        from pitchapi.models.common import TeamRef
        value=MatchStats(MID,TeamRef(HOME,"H"),TeamRef(AWAY,"A"),[
            MatchStatPeriod("All",[
                MatchStatGroup("Expected goals (xG)",[
                    MatchStatItem("xG","expected_goals","0.4","0.7","double")]),
                MatchStatGroup("Shots",[
                    MatchStatItem("Shots","total_shots","1","1","integer")])])])
        self.assertEqual(self.validate(stat=to_plain(value)),(.4,.7,1,1,.4,.7))

    def test_missing_total_shots_cannot_certify_nonempty_feed(self):
        s=stat_feed();s["data"]["periods"][0]["groups"].pop()
        with self.assertRaisesRegex(ValueError,"TOTAL_SHOTS"):
            self.validate(stat=s)
        parsed=parse_shots(shot_feed(),HOME,AWAY,stats_payload=s)
        self.assertEqual(parsed["state"],"UNVERIFIED_SHOT_XG")
        self.assertIsNone(parsed["home_xg_sum"])

    def test_no_independent_stats_never_complete(self):
        result=verify_native_shots(season()[0],shot_feed(),observed_at_utc=clock(-1))
        self.assertEqual(result["shot_state"],"UNVERIFIED_SHOT_XG")
        self.assertIsNone(result["xg_home"])

    def test_independent_count_mismatch_blocks_even_matching_xg(self):
        s=stat_feed();s["data"]["periods"][0]["groups"][1]["items"][0]["home"]="2"
        with self.assertRaisesRegex(ValueError,"COUNT_DISAGREEMENT"):
            self.validate(stat=s)

    def test_duplicate_count_even_if_equal_is_ambiguous(self):
        s=stat_feed();g=s["data"]["periods"][0]["groups"][1]
        g["items"].append(copy.deepcopy(g["items"][0]))
        with self.assertRaisesRegex(ValueError,"NOT_UNIQUE"):
            self.validate(stat=s)

    def test_invalid_and_missing_count_types_fail(self):
        for value in (None,True,False,-1,1.5,"1.0"," 1","NaN",{},[]):
            with self.subTest(value=value):
                s=stat_feed();s["data"]["periods"][0]["groups"][1]["items"][0]["home"]=value
                with self.assertRaises(ValueError):self.validate(stat=s)

    def test_genuine_both_sides_zero_requires_explicit_counts_and_zero_xg(self):
        s=shot_feed();s["data"]["periods"][0]["shots"]=[]
        self.assertEqual(self.validate(s,stats(MID,HOME,AWAY,0,0,0,0)),(0,0,0,0,0,0))
        with self.assertRaisesRegex(ValueError,"EMPTY_SIDE"):
            self.validate(s,stats(MID,HOME,AWAY,.01,0,0,0))

    def test_one_side_zero_is_valid_and_distinct_from_missing(self):
        s=shot_feed();s["data"]["periods"][0]["shots"].pop()
        self.assertEqual(self.validate(s,stats(MID,HOME,AWAY,.4,0,1,0)),(.4,0,1,0,.4,0))

    def test_shot_and_stats_fixture_or_team_mismatch_block(self):
        for field in ("shot_match","stats_match","stats_side","shot_side"):
            with self.subTest(field=field):
                sh,st=shot_feed(),stat_feed()
                if field=="shot_match":sh["data"]["match_id"]="m_999999"
                if field=="stats_match":st["data"]["match_id"]="m_999999"
                if field=="stats_side":st["data"]["away_team"]["id"]=HOME
                if field=="shot_side":sh["data"]["periods"][0]["shots"][1]["team_id"]="t_999999"
                with self.assertRaises(ValueError):self.validate(sh,st)

    def test_missing_unknown_duplicate_and_mixed_shot_periods_block(self):
        for labels in ([],["First"],[None],["Extra"],["All","First"],["All","All"],["First","First"]):
            with self.subTest(labels=labels):
                sh=shot_feed();period=sh["data"]["periods"][0]
                sh["data"]["periods"]=[dict(copy.deepcopy(period),period=x) for x in labels]
                with self.assertRaises(ValueError):self.validate(sh)

    def test_two_halves_are_one_full_feed(self):
        sh=shot_feed();rows=sh["data"]["periods"][0]["shots"]
        sh["data"]["periods"]=[{"period":"First","shots":rows[:1]},
                                 {"period":"Second","shots":rows[1:]}]
        self.assertEqual(self.validate(sh),(.4,.7,1,1,.4,.7))

    def test_shot_id_required_unique_across_halves(self):
        for val in (None,"","s_1"):
            sh=shot_feed();sh["data"]["periods"][0]["shots"][1]["id"]=val
            with self.assertRaisesRegex(ValueError,"NATIVE_SHOT"):self.validate(sh)

    def test_stats_first_half_duplicate_all_and_nonfinite_values_block(self):
        for action in ("half","duplicate","nan","bool"):
            st=stat_feed();p=st["data"]["periods"][0]
            if action=="half":p["period"]="First"
            if action=="duplicate":st["data"]["periods"].append(copy.deepcopy(p))
            if action=="nan":p["groups"][0]["items"][0]["home"]="NaN"
            if action=="bool":p["groups"][0]["items"][0]["home"]=True
            with self.assertRaises(ValueError):self.validate(stat=st)

    def test_stats_xg_in_tolerance_without_count_is_still_rejected(self):
        st=stat_feed();st["data"]["periods"][0]["groups"].pop()
        st["data"]["periods"][0]["groups"][0]["items"][0]["home"]="0.45"
        self.assertNotEqual(native_xg_verified(st,shot_feed(),season()[0])[0],"VERIFIED")

    def test_receipts_authenticate_original_payload_and_both_clocks(self):
        sh,st=shot_feed(),stat_feed();sr,tr=receipts(sh,st)
        sample=parse_pair(sh,st,match=season()[0],country="ESP",shot_receipt=sr,stat_receipt=tr)
        self.assertEqual(sample["source_shots_sha256"],hexdigest(canonical(sh)))
        self.assertEqual(sample["source_stats_sha256"],hexdigest(canonical(st)))
        self.assertEqual(sample["observed_utc"],tr["completed_at_utc"])

    def test_receipt_payload_hash_chain_and_resource_mismatch_block(self):
        for action in ("hash","chain","resource","payload"):
            sh,st=shot_feed(),stat_feed();sr,tr=receipts(sh,st)
            if action=="hash":tr["payload_sha256"]="0"*64
            if action=="chain":tr["chain_sha256"]="0"*64
            if action=="resource":tr["resource"]="pitchapi:step17xg:stats:m_999999"
            if action=="payload":tr["payload"]={}
            with self.assertRaises(ValueError):
                parse_pair(sh,st,match=season()[0],country="ESP",shot_receipt=sr,stat_receipt=tr)

    def test_receipt_window_overlap_before_match_and_synthetic_origin_block(self):
        for action in ("window","overlap","early","synthetic","not_finished","future"):
            sh,st=shot_feed(),stat_feed();sr,tr=receipts(sh,st);m=season()[0]
            if action=="window":
                sr["started_at_utc"]=clock(-500);sr["completed_at_utc"]=clock(-499)
            if action=="overlap":tr["started_at_utc"]=sr["started_at_utc"]
            if action=="early":m["time_utc"]=clock(-100)
            if action=="synthetic":sr["origin"]=tr["origin"]="SYNTHETIC_TEST"
            if action=="not_finished":m["status"]="scheduled"
            if action=="future":tr["completed_at_utc"]=clock(100)
            resign(sr);tr["previous_sha256"]=sr["chain_sha256"];resign(tr)
            with self.assertRaises(ValueError):validate_receipts(sh,st,m,sr,tr)

    def test_staged_store_revalidates_sources_and_rolls_back_entire_batch(self):
        sh,st=shot_feed(),stat_feed();sr,tr=receipts(sh,st)
        row=parse_pair(sh,st,match=season()[0],country="ESP",shot_receipt=sr,stat_receipt=tr)
        with tempfile.TemporaryDirectory() as td:
            db=Path(td)/"xg.sqlite"
            bad=copy.deepcopy(row);bad["shots_home"]=2
            with self.assertRaisesRegex(ValueError,"SOURCE_DRIFT"):store_samples(db,[row,bad])
            with connect(db) as con:self.assertEqual(con.execute("SELECT COUNT(*) FROM observed_native_xg").fetchone()[0],0)
            self.assertEqual(store_samples(db,[row]),1)
            with self.assertRaises(sqlite3.IntegrityError):store_samples(db,[row])

class NativeLedgerPairTests(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(":memory:");self.addCleanup(self.db.close)
        record(self.db,"matches",season(),started_at_utc=clock(-30),completed_at_utc=clock(-29),origin="NETWORK_OBSERVED")

    def append(self,stat=None):
        self.shot_start,self.shot_end=clock(-12),clock(-11)
        self.stat_start,self.stat_end=clock(-10),clock(-9)
        return record(self.db,"shots",shot_feed(),started_at_utc=self.shot_start,
            completed_at_utc=self.shot_end,stats_payload=stat if stat is not None else stat_feed(),
            stats_started_at_utc=self.stat_start,stats_completed_at_utc=self.stat_end,origin="NETWORK_OBSERVED")

    def test_e2e_asof_requires_completion_of_both_sources(self):
        self.append()
        self.assertIsNone(shots_asof(self.db,MID,self.stat_start))
        result=shots_asof(self.db,MID,self.stat_end)
        self.assertEqual(result["xg_home"],.4)
        self.assertEqual(result["captured_at_utc"],self.stat_end)
        self.assertFalse(result["training_allowed"])
        self.assertIsNone(result["source_provider_published_at_utc"])
        self.assertEqual(verify(self.db)["shot_captures"],1)

    def test_unpaired_capture_is_retained_but_never_certified(self):
        record(self.db,"shots",shot_feed(),started_at_utc=clock(-12),completed_at_utc=clock(-11),origin="NETWORK_OBSERVED")
        self.assertEqual(verify(self.db)["shot_captures"],1)
        self.assertIsNone(shots_asof(self.db,MID,clock(-1)))

    def test_stats_validation_failure_leaves_no_half_pair(self):
        s=stat_feed();s["data"]["match_id"]="m_999999"
        with self.assertRaisesRegex(ValueError,"PAIR_INCOMPLETE"):self.append(s)
        self.assertEqual(verify(self.db)["captures"],1)
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM pitch_source_pairs").fetchone()[0],0)

    def test_failure_after_shot_insert_rolls_back_capture_records_and_pair(self):
        self.db.execute("CREATE TRIGGER reject_pair BEFORE INSERT ON pitch_source_pairs BEGIN SELECT RAISE(ABORT,'INJECTED'); END")
        with self.assertRaisesRegex(sqlite3.IntegrityError,"INJECTED"):self.append()
        self.assertEqual(verify(self.db)["captures"],1)
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM pitch_records").fetchone()[0],380)
        self.assertFalse(self.db.in_transaction)

    def test_immutable_stats_and_tamper_detected_by_verify_and_asof(self):
        self.append()
        for sql in ("DELETE FROM pitch_source_pairs","UPDATE pitch_source_pairs SET stats_json='{}'"):
            with self.assertRaisesRegex(sqlite3.IntegrityError,"IMMUTABLE"):self.db.execute(sql)
            self.db.rollback()
        self.db.execute("DROP TRIGGER pitch_pair_no_update")
        self.db.execute("UPDATE pitch_source_pairs SET stats_sha256='broken'")
        for action in (lambda:verify(self.db),lambda:shots_asof(self.db,MID,clock(-1))):
            with self.assertRaisesRegex(ValueError,"TAMPERED"):action()

    def test_caller_transaction_is_never_implicitly_committed(self):
        self.db.execute("CREATE TABLE caller_work (n INTEGER)")
        self.db.execute("INSERT INTO caller_work VALUES (1)")
        with self.assertRaisesRegex(ValueError,"CALLER_TRANSACTION"):self.append()
        self.db.rollback()
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM caller_work").fetchone()[0],0)

    def test_rehashed_stats_still_must_match_original_capture_anchor(self):
        self.append()
        self.db.execute("DROP TRIGGER pitch_pair_no_update")
        raw,a,b=self.db.execute("SELECT stats_json,stats_started_at_utc,stats_completed_at_utc FROM pitch_source_pairs").fetchone()
        altered=json.loads(raw);altered["data"]["periods"][0]["groups"][0]["items"][0]["home"]="0.41"
        from src.kb3_pitch_native_ledger import _pair_statement
        pair=_pair_statement(shot_feed(),altered,self.shot_start,self.shot_end,a,b,"NETWORK_OBSERVED")
        self.db.execute("UPDATE pitch_source_pairs SET stats_json=?,stats_sha256=?,pair_sha256=?",
                        (canonical(altered).decode(),pair["stats_sha256"],hexdigest(canonical(pair))))
        with self.assertRaisesRegex(ValueError,"ANCHOR_CHANGED"):shots_asof(self.db,MID,clock(-1))

    def test_following_capture_cannot_overlap_stats_clock(self):
        self.append()
        with self.assertRaisesRegex(ValueError,"NON_MONOTONE"):
            record(self.db,"matches",season(),started_at_utc=self.stat_start,completed_at_utc=self.stat_end,origin="NETWORK_OBSERVED")

    def test_replay_does_not_duplicate_pair(self):
        self.append()
        with self.assertRaisesRegex(ValueError,"NON_MONOTONE"):self.append()
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM pitch_source_pairs").fetchone()[0],1)

    def test_verify_of_pair_is_read_only(self):
        self.append()
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/"copy.sqlite"
            with sqlite3.connect(p) as dest:self.db.backup(dest)
            with sqlite3.connect(p.as_uri()+"?mode=ro",uri=True) as reader:
                self.assertEqual(verify(reader)["captures"],2)

    def test_actual_collector_passes_both_sources_under_original_budget(self):
        from scripts.step11_pitch_native_capture_once import capture, MAX_REQUESTS
        from src.kb3_pitch_native_archive import restore
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric import rsa
        class Leagues:
            def list(self):return {"leagues":[{"id":"l_000000","name":"Premier League","country_code":"ENG","seasons":["2026/2027"]}]}
            def matches(self,*args,**kwargs):return {"matches":season()}
        class Matches:
            def shots(self,mid):
                i=int(mid[2:]);out=shot_feed();out["data"]["match_id"]=mid
                out["data"]["periods"][0]["shots"][0]["team_id"]=f"t_{i*2:06d}"
                out["data"]["periods"][0]["shots"][1]["team_id"]=f"t_{i*2+1:06d}"
                return out
            def stats(self,mid):
                i=int(mid[2:]);return stats(mid,f"t_{i*2:06d}",f"t_{i*2+1:06d}",.4,.7)
        class Client:
            leagues=Leagues();matches=Matches()
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);key=rsa.generate_private_key(public_exponent=65537,key_size=3072)
            pub=root/"public.pem";private=root/"private.pem"
            pub.write_bytes(key.public_key().public_bytes(serialization.Encoding.PEM,serialization.PublicFormat.SubjectPublicKeyInfo))
            private.write_bytes(key.private_bytes(serialization.Encoding.PEM,serialization.PrivateFormat.PKCS8,serialization.NoEncryption()))
            with patch("pitchapi.PitchAPI",return_value=Client()),patch.dict("os.environ",{"PITCHAPI_API_KEY":"SYNTHETIC_ONLY"}):
                report=capture(root/"capture",pub)
            self.assertEqual(report["shot_states"],{"COMPLETE_SHOT_XG":2})
            self.assertEqual(report["paired_stats_receipts"],2)
            self.assertLessEqual(report["provider_requests"],MAX_REQUESTS)
            restored=root/"restored.sqlite"
            restore(root/"capture/KB3_PITCH_NATIVE_2026-27_PIT.enc",root/"capture/KB3_PITCH_NATIVE_2026-27_PIT.manifest.json",private,restored)
            with sqlite3.connect(restored) as reader:
                self.assertEqual(reader.execute("SELECT COUNT(*) FROM pitch_source_pairs").fetchone()[0],2)

if __name__=="__main__":unittest.main()
