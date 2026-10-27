"""Sidecar C: future schedule target-free snapshots; no sports API or TEST labels."""
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from src.kb3_step14_public_sidecar import (
    clean_future_schedule,store_once,SidecarError,collect,
)

NOW=datetime(2026,10,27,11,0,tzinfo=timezone.utc)


def fake_blob():
    rows=[]
    for i in range(18):
        day=(NOW.date()+timedelta(days=i+1)).isoformat()
        rows.append({"date":day,"time":"15:00",
                     "team1":f"Team H{i}","team2":f"Team A{i}",
                     "score":{"ft":[i%3,0]},"odds":"HIDDEN_TARGET_LEAK"})
    return json.dumps({"name":"public fixture only","matches":rows,
                       "padding":"x"*1050}).encode("utf-8")


class FutureSidecarSafetyTests(unittest.TestCase):
    def test_future_and_projection_strictly_target_free(self):
        rec=clean_future_schedule(fake_blob(),NOW)
        self.assertEqual(rec["matches_future_min_3_calendar_days"],16)
        self.assertTrue(rec["training_allowed"] is False)
        self.assertFalse(rec["test_labels_read"])
        for r in rec["fixtures_target_free_only"]:
            self.assertEqual(set(r),{"date","time_provider_local_unverified",
                "home_team_public_name","away_team_public_name"})
        self.assertNotIn("HIDDEN_TARGET_LEAK",str(rec))

    def test_source_observed_at_is_real_timezone_aware(self):
        with self.assertRaisesRegex(SidecarError,"CLOCK_MUST_BE_UTC"):
            clean_future_schedule(fake_blob(),NOW.replace(tzinfo=None))

    def test_append_only_cannot_overwrite_day(self):
        r=clean_future_schedule(fake_blob(),NOW)
        with TemporaryDirectory() as root:
            first,created=store_once(r,root)
            self.assertTrue(created)
            _,created2=store_once(r,root)
            self.assertFalse(created2)
            v=clean_future_schedule(fake_blob(),NOW+timedelta(seconds=2))
            with self.assertRaisesRegex(SidecarError,"APPEND_ONLY_DATE_ALREADY_CAPTURED"):
                store_once(v,root)
            self.assertTrue(Path(first).exists())

    def test_receipt_hash_tamper_denied(self):
        rec=clean_future_schedule(fake_blob(),NOW)
        rec["training_allowed"]=True
        with TemporaryDirectory() as work:
            with self.assertRaisesRegex(SidecarError,"RECEIPT_TAMPERED"):
                store_once(rec,work)

    def test_one_get_no_paid_provider(self):
        urls=[]
        def fetcher(url):
            urls.append(url)
            return fake_blob()
        r=collect(blob_reader=fetcher,now=NOW)
        self.assertEqual(len(urls),1)
        self.assertEqual(r["source"],urls[0])
        self.assertTrue(urls[0].startswith("https://raw.githubusercontent.com/openfootball/"))
        self.assertFalse(r["model_features_included"])
        self.assertFalse(r["historical_pit_certified"])


if __name__=="__main__":
    unittest.main()
