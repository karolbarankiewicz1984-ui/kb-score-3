"""Synthetic-only end-to-end bridge fixtures. Never hit provider APIs."""
import json
import hashlib
import io
import zipfile
from unittest.mock import patch
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from scripts.step14_three_league_pitchapi_actual_audit import CURRENT, PREVIOUS
from src.kb3_v3_native_forward_bridge import produce, BridgeError
from scripts.kb3_v3_verify_hosted_native_bridge import validate
from src.kb3_catboost_research_v3 import verified_view, vector


NOW = datetime(2026, 11, 9, 12, tzinfo=timezone.utc)


def stamp(t):
    return t.isoformat(timespec="seconds").replace("+00:00", "Z")


def match(mid, kickoff, status, home, away, result=None):
    return dict(id=mid, time_utc=stamp(kickoff), status=status,
                home_team=dict(id=home), away_team=dict(id=away),
                score_home=None if result is None else result[0],
                score_away=None if result is None else result[1])


def receipts():
    rows = []
    for country in ("ESP", "ITA", "GER"):
        for season in (CURRENT, PREVIOUS):
            games = [match(country + "_old_" + season, NOW-timedelta(days=7 if season == CURRENT else 370),
                           "finished", country+"_H", country+"_C", (2, 1))]
            if season == CURRENT:
                games += [match(country+"_future", NOW+timedelta(hours=9),
                                "scheduled", country+"_H", country+"_A")]
            rows.append(dict(resource="pitchapi:pilot_daily:"+country+":"+season,
                             origin="NETWORK_OBSERVED",
                             completed_at_utc=stamp(NOW-timedelta(minutes=1)),
                             payload=dict(matches=games)))
    return rows


class NativeV3Bridge(unittest.TestCase):
    def test_real_original_builder_and_all_87_fields(self):
        with tempfile.TemporaryDirectory() as d:
            m = produce(receipts(), Path(d)/"native", created_now=NOW)
            self.assertEqual(m["source_count"], 6)
            self.assertEqual(m["target_count"], 3)
            self.assertFalse(m["training_allowed"])
            self.assertEqual(m["cutoff_utc"], stamp(NOW+timedelta(hours=2)))
            # Synthetic test adapter mimics the GitHub API *only* here.
            class SyntheticHost:
                def read(self, ref):
                    doc = json.loads((Path(d)/"native"/ref["member"]).read_text())
                    return doc, NOW+timedelta(minutes=5)
            store = SyntheticHost()
            for t in m["targets"]:
                inp=json.loads((Path(d)/"native"/t["input_member"]).read_text())
                sha={x["sha256"]:dict(member=x["member"],sha256=x["sha256"])
                     for x in m["source_index"] if x["member"] in t["source_members"]}
                s=dict(input=inp,input_archive=dict(member=t["input_member"],
                       sha256=t["input_sha256"]),source_archives=sha)
                v=verified_view(s,store,"FORWARD")
                self.assertEqual(len(vector(v)),87)
                self.assertEqual(v["accepted_predecessor_count"],2)
                self.assertFalse(v["training_allowed"])


    def test_real_github_host_adapter_uses_original_v3_verified_view(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)/"native"
            produce(receipts(),root,created_now=NOW)
            buf=io.BytesIO()
            with zipfile.ZipFile(buf,"w",zipfile.ZIP_DEFLATED) as z:
                for path in root.rglob("*"):
                    if path.is_file():
                        z.write(path,arcname="2026-11-09/"+str(path.relative_to(root)))
            raw=buf.getvalue()
            aid=999
            url="https://api.github.com/repos/karolbarankiewicz1984-ui/kb-score-3/actions/artifacts/999"
            meta=dict(id=aid,expired=False,
                      name="KB3_V3_NATIVE_87_FORWARD_SOURCE_UNENCRYPTED_PRIVATE",
                      created_at=stamp(NOW+timedelta(minutes=5)),
                      archive_download_url=url+"/zip",
                      digest="sha256:"+hashlib.sha256(raw).hexdigest())
            with patch("scripts.kb3_v3_verify_hosted_native_bridge._gh_json",
                       return_value=meta), patch(
                       "scripts.kb3_v3_verify_hosted_native_bridge._gh_artifact_zip",
                       return_value=raw), patch(
                       "src.kb3_step16_m0_720_calibration._gh_json",
                       return_value=meta), patch(
                       "src.kb3_step16_m0_720_calibration._gh_artifact_zip",
                       return_value=raw):
                report=validate(aid,"synthetic-test-token")
            self.assertEqual(report["original_87_vector_verified"],3)
            self.assertTrue(report["hosted_before_exact_feature_cutoff"])
            self.assertFalse(report["eligible_for_training"])
            self.assertFalse(report["production_approved"])

    def test_real_pit_utc_z_string_can_drive_native_87_bridge(self):
        # Regression: utc_now() is a string. Earlier code called .utcoffset()
        # directly on that string, failing real scheduled capture at runtime.
        with tempfile.TemporaryDirectory() as d:
            m = produce(receipts(), Path(d)/"native", created_now=stamp(NOW))
            self.assertEqual(m["source_count"], 6)
            self.assertEqual(m["target_count"], 3)
            self.assertFalse(m["training_allowed"])

    def test_invalid_native_clock_type_fails_closed(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaisesRegex(BridgeError, "UTC_REQUIRED"):
                produce(receipts(), Path(d)/"native", created_now=123)
            self.assertFalse((Path(d)/"native").exists())

    def test_missing_native_source_rejected(self):
        rows=receipts()[:-1]
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaisesRegex(BridgeError,"MISSING_REAL_NATIVE"):
                produce(rows,Path(d)/"native",created_now=NOW)
            self.assertFalse((Path(d)/"native").exists())

    def test_near_kickoff_never_included(self):
        rows=receipts()
        for r in rows:
            if r["resource"].endswith(CURRENT):
                r["payload"]["matches"][-1]["time_utc"]=stamp(NOW+timedelta(hours=2))
        with tempfile.TemporaryDirectory() as d:
            m=produce(rows,Path(d)/"native",created_now=NOW)
            self.assertEqual(m["target_count"],0)

    def test_no_future_score_export(self):
        rows=receipts()
        for r in rows:
            if r["resource"].endswith(CURRENT):
                r["payload"]["matches"][-1]["score_home"]=1
        with tempfile.TemporaryDirectory() as d:
            m=produce(rows,Path(d)/"native",created_now=NOW)
            self.assertEqual(m["target_count"],0)


if __name__=="__main__":
    unittest.main()
