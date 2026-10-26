"""No network or secrets: strict synthetic tests of 1520-row PitchAPI split."""
import copy
from datetime import datetime, timedelta, timezone
import unittest

from src.kb3_pitch_uefa_evidence import add_observation
from src.kb3_step12_native_index import index_receipts, SEASONS, RES
from src.kb3_split import SplitSafetyError, sha


def fixture(season, index):
    year = int(season[:4])
    if year == 2026:
        finished = index < 80
        base = datetime(2026, 10, 1, tzinfo=timezone.utc) if finished else datetime(
            2026, 11, 1, tzinfo=timezone.utc)
        when = base + timedelta(hours=index * 2)
    else:
        finished = True
        when = datetime(year, 9, 1, tzinfo=timezone.utc) + timedelta(hours=index * 3)
    number = (year - 2023) * 380 + index + 1
    home, away = index % 20, (index + 1) % 20
    return {
        "id": "m_" + str(number).zfill(6),
        "time_utc": when.isoformat().replace("+00:00", "Z"),
        "home_team": {"id": "t_" + str(home + 1).zfill(6), "name": "Club " + str(home)},
        "away_team": {"id": "t_" + str(away + 1).zfill(6), "name": "Club " + str(away)},
        "status": "finished" if finished else "not_started",
        "score_home": 2 if finished else None,
        "score_away": 1 if finished else None,
    }


def receipts():
    out = []
    for step, resource in enumerate(["pitchapi:catalog"] +
                                    [RES.format(season=s) for s in SEASONS]):
        if step == 0:
            payload = {"leagues": [{"id": "league-1", "name": "Premier League",
                                    "country_code": "ENG", "seasons": list(SEASONS)}]}
        else:
            payload = {"matches": [fixture(SEASONS[step-1], i) for i in range(380)]}
        start = f"2026-10-26T14:{step:02d}:00Z"
        end = f"2026-10-26T14:{step:02d}:01Z"
        add_observation(out, resource=resource, payload=payload,
                        started=start, completed=end, origin="SYNTHETIC_TEST")
    return out


class RealIndexContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sample = receipts()

    def test_complete_real_format_1520_and_all_quarantined(self):
        m, proof = index_receipts(copy.deepcopy(self.sample), allow_synthetic=True)
        self.assertEqual(proof["partition_counts"], {
            "TRAIN": 760, "VALIDATION": 380, "TEST": 380})
        self.assertEqual(m["quarantined_count"], 1520)
        self.assertFalse(m["gate12_pass"])
        self.assertFalse(m["training_allowed"])
        self.assertEqual(sum(m["eligible_counts"].values()), 0)
        self.assertEqual(len(set(x["fixture_id"] for x in m["rows"])), 1520)
        self.assertEqual(sum(x["evidence_class"] == "PROSPECTIVE_OBSERVED_AT"
                             for x in m["rows"]), 300)
        self.assertEqual(m["manifest_sha256"], sha(
            {k: v for k, v in m.items() if k != "manifest_sha256"}))

    def test_duplicate_source_match_detected(self):
        data = copy.deepcopy(self.sample)
        data[2]["payload"]["matches"][0]["id"] = data[1]["payload"]["matches"][0]["id"]
        with self.assertRaises(ValueError):
            index_receipts(data, allow_synthetic=True)

    def test_tampering_with_payload_rejected(self):
        data = copy.deepcopy(self.sample)
        data[2]["payload"]["matches"][0]["score_home"] = 15
        with self.assertRaisesRegex(ValueError, "UEFA_TAMPERED_SOURCE_PAYLOAD"):
            index_receipts(data, allow_synthetic=True)

    def test_one_missing_real_receipt_rejected(self):
        with self.assertRaisesRegex(SplitSafetyError, "FIVE_RECEIPTS"):
            index_receipts(copy.deepcopy(self.sample[:-1]), allow_synthetic=True)

    def test_synthetic_not_mistaken_for_network(self):
        with self.assertRaisesRegex(ValueError, "UEFA_NON_REAL_EVIDENCE"):
            index_receipts(copy.deepcopy(self.sample))

    def test_future_is_pending_with_cutoff_but_not_training_approved(self):
        m, _ = index_receipts(copy.deepcopy(self.sample), allow_synthetic=True)
        r = next(x for x in m["rows"] if x["evidence_class"] == "PROSPECTIVE_OBSERVED_AT")
        self.assertEqual(r["reason"], "STEP11_FEATURE_TRAINING_NOT_APPROVED")
        self.assertIsNotNone(r["feature_cutoff_utc"])


if __name__ == "__main__":
    unittest.main()
