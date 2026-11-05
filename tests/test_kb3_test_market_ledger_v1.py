"""Isolated Step TEST market freeze/settle controls: no provider, no backdating."""
from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
import io
import json
import sqlite3
import tempfile
import unittest
import zipfile
import urllib.request

from src.kb3_pit_ledger import canonical
from src.kb3_step15_goal_markets import markets_from_lambdas
from src.kb3_test_readonly_markets import digest
from src.kb3_test_market_ledger_v1 import (
    MarketLedgerError, make_market_freeze, verify_market_freeze,
    market_label, score_market_row, settle_market_freeze)
from scripts.kb3_test_market_ledger_runner import (
    ARTIFACT_NAME, capture_new_market_freezes, github_artifact_attest,
    verify_host_proof, settle_existing, _StripAuthOnOffsiteRedirect,
)

CUTOFF="2026-11-05T08:18:40Z"
PARENT_HOST="2026-11-05T08:20:19Z"
CAPTURE="2026-11-05T16:30:00Z"
HOST="2026-11-05T16:30:06Z"
KICKOFF="2026-11-08T16:00:00Z"
PARENT_PROOF="GITHUB_SERVER_ACTIONS_ARTIFACT_PLUS_EXACT_DB_BYTES"


def parent():
    markets=markets_from_lambdas(1.68,1.10)
    base={
        "model_version":"M0_ELO_POISSON_RESEARCH_720TRAIN_V1",
        "league_country":"ESP",
        "provider_match_id":"m_SYNTHETIC_MATCH",
        "feature_cutoff_utc":CUTOFF,
        "generated_at_utc":CUTOFF,
        "kickoff_utc":KICKOFF,
        "phase":"EARLY",
        "status":"RESEARCH_TRAIN720_UNCALIBRATED",
        "expected_goals":{"home":1.68,"away":1.10},
        "p_1x2":markets["p_1x2"],
        "p_over":markets["p_over"],
        "p_btts_yes":markets["p_btts"]["yes"],
        "source_chain_sha256":"a"*64,
        "feature_sha256":"b"*64,
        "params_sha256":"c"*64,
        "manifest_sha256":"d"*64,
        "original_provider_first_published_at_proven":False,
        "training_allowed":False,
        "production_approved":False,
    }
    return {**base,"forecast_sha256":digest(base)}


def snapshot():
    p=parent()
    return make_market_freeze(p, original_id=p["forecast_sha256"],
                              parent_host_utc=PARENT_HOST,
                              parent_host_source=PARENT_PROOF,
                              captured_at_utc=CAPTURE)


def result_row(p, gh=1, ga=1):
    outcome="1" if gh>ga else "2" if gh<ga else "X"
    from src.kb3_step14_m1_math_calibration import score_one
    ll,brier=score_one(p["p_1x2"],outcome)
    base={
        "forecast_id":p["forecast_sha256"],
        "league":p["league_country"],
        "native_match_id":p["provider_match_id"],
        "score_home":gh,
        "score_away":ga,
        "outcome":outcome,
        "observed_utc":"2026-11-08T20:05:00Z",
        "source_chain_sha256":"e"*64,
        "log_loss":ll,
        "brier_sum3":brier,
    }
    return {"settlement_sha256":digest(base),
            **{k:base[k] for k in ("forecast_id","league","native_match_id",
                                   "score_home","score_away","outcome","observed_utc")},
            "settled_utc":base["observed_utc"],
            "provider_source_chain_sha256":base["source_chain_sha256"],
            "log_loss":ll,"brier_sum3":brier}


def sql(path,p):
    with sqlite3.connect(path) as db:
        db.executescript("""
          CREATE TABLE forecasts(
            id TEXT PRIMARY KEY, payload_json TEXT NOT NULL,
            kickoff_utc TEXT NOT NULL, captured_at_utc TEXT NOT NULL);
          CREATE TABLE m0720_github_push_proofs(
            forecast_id TEXT UNIQUE, github_server_event_utc TEXT, source TEXT);
          CREATE TABLE settlements(
            settlement_sha256 TEXT, forecast_id TEXT UNIQUE, league TEXT,
            native_match_id TEXT, score_home INTEGER, score_away INTEGER,
            outcome TEXT,observed_utc TEXT,settled_utc TEXT,
            provider_source_chain_sha256 TEXT,log_loss REAL,brier_sum3 REAL);
        """)
        db.execute("INSERT INTO forecasts VALUES(?,?,?,?)",
                   (p["forecast_sha256"],json.dumps(p),p["kickoff_utc"],
                    p["generated_at_utc"]))
        db.execute("INSERT INTO m0720_github_push_proofs VALUES(?,?,?)",
                   (p["forecast_sha256"],PARENT_HOST,PARENT_PROOF))


def fake_github(staging, *, created=HOST, mutate=False):
    payload={}
    for path in sorted(Path(staging).glob("*.json")):
        raw=path.read_bytes()
        payload[path.name] = raw+b"tamper" if mutate else raw
    binary=io.BytesIO()
    with zipfile.ZipFile(binary,"w",compression=zipfile.ZIP_DEFLATED) as z:
        for name,raw in payload.items():
            z.writestr(name,raw)
    archive=binary.getvalue()
    artifact={
        "id":999,
        "name":ARTIFACT_NAME,
        "expired":False,
        "created_at":created,
        "digest":"sha256:"+sha256(archive).hexdigest(),
        "workflow_run":{"id":12345},
    }
    return ((lambda url,token:{"artifacts":[artifact]}),
            (lambda url,token:archive))


class IndependentMarketSafety(unittest.TestCase):
    def test_exact_market_selection_groups_and_atomic_hash(self):
        p=parent()
        snap=snapshot()
        self.assertEqual(snap["market_row_count"],28)
        self.assertTrue(verify_market_freeze(
            snap,parent=p,parent_id=p["forecast_sha256"],
            host_utc=PARENT_HOST,host_source=PARENT_PROOF))
        pairs={(m["family"],m["side"],m["line"],m["selection"])
               for m in snap["market_rows"]}
        self.assertEqual(len(pairs),28)
        self.assertFalse(snap["production_approved"])
        self.assertEqual(snap["official_fit_increment"],0)
        pushes=[m for m in snap["market_rows"]
                if m["family"]=="FT_TOTAL_GOALS_INTEGER_OU"]
        self.assertEqual(len(pushes),2)
        self.assertAlmostEqual(pushes[0]["p_push"],pushes[1]["p_push"])
        self.assertAlmostEqual(pushes[0]["p_win"]+
                               pushes[1]["p_win"]+pushes[0]["p_push"],1)
        for m in snap["market_rows"]:
            self.assertAlmostEqual(
                m["p_win"]+m["p_push"]+(1-m["p_win"]-m["p_push"]),1)

    def test_push_void_and_detailed_result_math(self):
        snaps=snapshot()["market_rows"]
        integer=next(m for m in snaps
                     if m["family"]=="FT_TOTAL_GOALS_INTEGER_OU"
                     and m["selection"]=="OVER")
        self.assertEqual(market_label(integer,1,1),"PUSH")
        self.assertEqual(market_label(integer,1,1,confirmed_void=True),"VOID")
        self.assertIsNone(score_market_row(integer,"PUSH")["binary_brier"])
        self.assertIsNone(score_market_row(integer,"VOID")["binary_log_loss"])
        self.assertEqual(market_label(integer,2,1),"WIN")
        self.assertEqual(market_label(integer,1,0),"LOSS")
        self.assertGreater(score_market_row(integer,"LOSS")["binary_log_loss"],0)
        btts=next(m for m in snaps if m["family"]=="FT_BTTS"
                  and m["selection"]=="YES")
        self.assertEqual(market_label(btts,1,1),"WIN")
        self.assertEqual(market_label(btts,2,0),"LOSS")
        double=next(m for m in snaps if m["family"]=="FT_DOUBLE_CHANCE"
                    and m["selection"]=="1X")
        self.assertEqual(market_label(double,1,1),"WIN")
        self.assertEqual(market_label(double,0,2),"LOSS")

    def test_refuses_late_capture_and_parent_or_market_tamper(self):
        p=parent()
        with self.assertRaisesRegex(MarketLedgerError,"CAPTURE_TOO_LATE"):
            make_market_freeze(
                p, original_id=p["forecast_sha256"],
                parent_host_utc=PARENT_HOST,parent_host_source=PARENT_PROOF,
                captured_at_utc="2026-11-08T14:29:59Z")
        snap=snapshot()
        snap["market_rows"][0]["p_win"]=0.8
        with self.assertRaisesRegex(MarketLedgerError,"MUTATED_MARKET"):
            verify_market_freeze(snap,parent=p,parent_id=p["forecast_sha256"],
                                 host_utc=PARENT_HOST,host_source=PARENT_PROOF)

    def test_real_source_copy_safety_and_retry_idempotence(self):
        p=parent()
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            db=root/"original.sqlite"
            sql(db,p)
            before=sha256(db.read_bytes()).hexdigest()
            stage=root/"stage"
            ledger=root/"ledger"
            count=capture_new_market_freezes(
                original_db=db,ledger_root=ledger,staging=stage,now_utc=CAPTURE)
            self.assertEqual(count,1)
            self.assertEqual(sha256(db.read_bytes()).hexdigest(),before)
            self.assertFalse((ledger/"freezes").exists())
            get,download=fake_github(stage)
            out=github_artifact_attest(
                staging=stage,ledger_root=ledger,token="synthetic-token",
                run_id=12345,http_json=get,http_zip=download)
            self.assertEqual(out["new_host_attested"],1)
            snap=ledger/"freezes"/(p["forecast_sha256"]+".json")
            proof=ledger/"host_proofs"/snap.name
            self.assertTrue(verify_host_proof(
                json.loads(snap.read_text()),json.loads(proof.read_text()),snap.read_bytes()))
            next_stage=root/"another-stage"
            self.assertEqual(capture_new_market_freezes(
                original_db=db,ledger_root=ledger,staging=next_stage,
                now_utc=CAPTURE),0)
            self.assertEqual(settle_existing(original_db=db,ledger_root=ledger)
                             ["pending"],1)
            self.assertEqual(sha256(db.read_bytes()).hexdigest(),before)
            sr=result_row(p)
            with sqlite3.connect(db) as cn:
                cn.execute("INSERT INTO settlements VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
                           tuple(sr[k] for k in (
                               "settlement_sha256","forecast_id","league","native_match_id",
                               "score_home","score_away","outcome","observed_utc",
                               "settled_utc","provider_source_chain_sha256",
                               "log_loss","brier_sum3")))
            first=settle_existing(original_db=db,ledger_root=ledger)
            self.assertEqual(first["created"],1)
            second=settle_existing(original_db=db,ledger_root=ledger)
            self.assertEqual(second["existing"],1)
            settlement_file=ledger/"settlements"/snap.name
            report=json.loads(settlement_file.read_text())
            self.assertEqual(report["market_count"],28)
            self.assertEqual(sum(x["settlement"]=="PUSH"
                                 for x in report["market_rows"]),2)
            self.assertEqual(report["official_fit_increment"],0)

    def test_no_github_bearer_header_on_redirected_signed_artifact(self):
        req=urllib.request.Request(
            "https://api.github.com/repos/owner/repo/actions/artifacts/123/zip",
            headers={"Authorization":"Bearer SENSITIVE_TOKEN",
                     "X-GitHub-Api-Version":"2022-11-28"})
        handler=_StripAuthOnOffsiteRedirect()
        cdn=handler.redirect_request(
            req,None,302,"Found",{},
            "https://results-receiver.actions.githubusercontent.com/signed_artifact.zip")
        self.assertIsNotNone(cdn)
        self.assertFalse(cdn.has_header("Authorization"))
        self.assertFalse(cdn.has_header("X-GitHub-Api-Version"))
        self.assertFalse(any("SENSITIVE_TOKEN" in str(v)
                             for v in cdn.headers.values()))
        # API-internal redirects can retain an authenticated identity.
        same=handler.redirect_request(
            req,None,302,"Found",{},
            "https://api.github.com/repos/owner/repo/actions/artifacts/124/zip")
        self.assertEqual(same.get_header("Authorization"),"Bearer SENSITIVE_TOKEN")

    def test_reject_github_late_or_mismatched_original_archive(self):
        for late,mutate in ((True,False),(False,True)):
            with self.subTest(late=late,mutate=mutate):
                with tempfile.TemporaryDirectory() as tmp:
                    root=Path(tmp)
                    stage=root/"staging"
                    stage.mkdir()
                    p=parent()
                    (stage/(p["forecast_sha256"]+".json")).write_bytes(
                        canonical(snapshot()))
                    get,download=fake_github(
                        stage,created="2026-11-08T15:00:01Z"
                        if late else HOST,mutate=mutate)
                    with self.assertRaisesRegex(MarketLedgerError,
                                                 "ZIP|TOO_LATE|BYTES_MISMATCH"):
                        github_artifact_attest(
                            staging=stage,ledger_root=root/"ledger",
                            token="synthetic-token",run_id=12345,
                            http_json=get,http_zip=download)
                    self.assertFalse((root/"ledger"/"freezes").exists())

    def test_refuses_tampered_score_or_missing_github_proof(self):
        p=parent()
        snap=snapshot()
        good=result_row(p)
        bad=dict(good)
        bad["score_home"]=5
        with self.assertRaisesRegex(MarketLedgerError,"MISMATCH"):
            settle_market_freeze(
                snap,bad,original_parent=p,parent_host_utc=PARENT_HOST,
                parent_host_source=PARENT_PROOF)
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            db=root/"input.sqlite"
            sql(db,p)
            frozen=root/"ledger"/"freezes"/(p["forecast_sha256"]+".json")
            frozen.parent.mkdir(parents=True)
            frozen.write_bytes(canonical(snap))
            with self.assertRaisesRegex(MarketLedgerError,"UNATTESTED"):
                settle_existing(original_db=db,ledger_root=root/"ledger")


if __name__=="__main__":
    unittest.main()
