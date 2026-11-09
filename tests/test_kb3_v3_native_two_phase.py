"""Fully offline tests of the actual original 87-feature verified_view bridge."""
from datetime import datetime, timedelta, timezone
from pathlib import Path
import hashlib
import io
import json
import tempfile
import unittest
import zipfile

from scripts.kb3_v3_native_two_phase import (
    build_bundle, verify_artifact, sha, canonical,
    SCHEMA, LEAGUES,
)

CAPTURE = "2026-11-09T08:00:00Z"
CUTOFF = "2026-11-09T08:06:00Z"
HOST = "2026-11-09T08:02:00Z"
FREEZE = "2026-11-09T08:07:00Z"


def match(key, year, home, away, day, *, status="finished", goals=(1, 0)):
    return {
        "id": key, "time_utc": f"{year}-{day}T18:00:00Z",
        "home_team": {"id": home}, "away_team": {"id": away},
        "status": status,
        "score_home": goals[0] if status == "finished" else None,
        "score_away": goals[1] if status == "finished" else None,
    }


def sources():
    data = {}
    for country in LEAGUES:
        old = [
            match(country + "_2025a", 2025, country + "_A", country + "_C", "10-03"),
            match(country + "_2025b", 2025, country + "_D", country + "_B", "10-04", goals=(0, 2)),
        ]
        current = [
            match(country + "_2026a", 2026, country + "_A", country + "_C", "10-18", goals=(1, 1)),
            match(country + "_2026b", 2026, country + "_D", country + "_B", "10-19", goals=(2, 1)),
            match(country + "_next", 2026, country + "_A", country + "_B", "11-12",
                  status="scheduled"),
        ]
        for year, vals in ((2025, old), (2026, current)):
            data[(country, year)] = {
                "payload": {"matches": vals},
                "completed_at_utc": CAPTURE,
            }
    return data


def zip_dir(root):
    b = io.BytesIO()
    with zipfile.ZipFile(b, "w", zipfile.ZIP_DEFLATED) as z:
        for path in sorted(root.rglob("*")):
            if path.is_file():
                z.writestr(str(path.relative_to(root)).replace("\\", "/"), path.read_bytes())
    return b.getvalue()


def make_zip():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "input_archive"
        response = build_bundle(sources(), captured_at=CAPTURE,
                                cutoff_at=CUTOFF, outdir=root)
        archive = zip_dir(root)
    return archive, response


def verify(blob, *, host=HOST, now=FREEZE):
    return verify_artifact(
        blob, artifact_id=999, created_at=host,
        digest_sha256="sha256:" + sha(blob), at_utc=now,
    )


class TwoPhaseNativeSourceArchive(unittest.TestCase):
    def test_real_original_verified_view_builds_all_87_from_exact_archived_bytes(self):
        blob, summary = make_zip()
        self.assertEqual(summary["sources_written"], 6)
        self.assertEqual(summary["inputs_written"], 3)
        report = verify(blob)
        self.assertEqual(report["verified_v3_input_vectors"], 3)
        self.assertTrue(report["independently_archived_before_exact_cutoff"])
        self.assertEqual(report["native_sources_verified"], 6)
        self.assertEqual(report["formal_v3_training_admitted"], 0)
        self.assertEqual(report["new_catboost_models_trained"], 0)
        self.assertFalse(report["production_approved"])
        self.assertTrue(all(x["feature_count"] == 87 for x in report["frozen_candidates"]))
        self.assertTrue(all(len(x["values"]) == 87 for x in report["frozen_candidates"]))
        self.assertTrue(all(x["formal_training_allowed"] is False for x in report["frozen_candidates"]))

    def test_late_host_receipt_rejected_even_when_raw_provider_clocks_are_early(self):
        blob, _ = make_zip()
        with self.assertRaisesRegex(Exception, "HOST_ARCHIVE_AFTER_EXACT_CUTOFF"):
            verify(blob, host="2026-11-09T08:06:01Z")

    def test_archive_byte_tamper_refused(self):
        blob, _ = make_zip()
        with self.assertRaisesRegex(Exception, "HOSTED_ARCHIVE_SHA256_MISMATCH"):
            verify_artifact(blob, artifact_id=999, created_at=HOST,
                            digest_sha256="sha256:"+"a"*64, at_utc=FREEZE)

    def test_native_response_member_tamper_refused_with_new_outer_zip_digest(self):
        blob, _ = make_zip()
        inp = io.BytesIO()
        with zipfile.ZipFile(io.BytesIO(blob)) as old, zipfile.ZipFile(inp, "w") as new:
            for name in old.namelist():
                data = old.read(name)
                if name == "sources/ESP_2025.json":
                    data += b"\n"
                new.writestr(name, data)
        with self.assertRaisesRegex(Exception, "NATIVE_MEMBER_SHA256_MISMATCH"):
            verify(inp.getvalue())

    def test_fake_future_cutoff_fails_without_host(self):
        blob, _ = make_zip()
        with self.assertRaisesRegex(Exception, "FREEZE_OUTSIDE_REAL_CUTOFF_WINDOW"):
            verify(blob, now="2026-11-09T08:05:00Z")

    def test_betting_or_champion_never_touched(self):
        blob, _ = make_zip()
        report = verify(blob)
        self.assertTrue(report["m0_champion_test_untouched"])
        self.assertEqual(report["formal_v3_training_admitted"], 0)
        self.assertEqual(report["source_artifact_created_at_utc"], HOST)


if __name__ == "__main__":
    unittest.main()
