"""Regression tests for isolated chronological KB3 V3-R research."""
import copy
import unittest
from datetime import datetime, timedelta, timezone

from scripts.kb3_v3r_walkforward import (
    chronological_folds, laplace_baseline, keys_for, ResearchSafetyError,
)


def sample(i, *, partition="TRAIN", league="ESP", kickoff=None):
    dt = kickoff or datetime(2023,1,1,tzinfo=timezone.utc)+timedelta(days=i)
    return {"partition":partition, "league":league,
            "fixture_id":"match_%d" % i,
            "kickoff_utc":dt.isoformat().replace("+00:00","Z"),
            "label":("1","X","2")[i%3], "features":{"home_points":i%5}}


def training(n=300):
    return [sample(i,league=("ESP","GER","POL")[i%3]) for i in range(n)]


class V3RChronologyTests(unittest.TestCase):
    def test_two_folds_expanding_training_embargo_and_no_overlap(self):
        rows = training()
        folds = chronological_folds(list(reversed(rows)))
        self.assertEqual(len(folds),2)
        val_keys = set()
        previous_train = set()
        for train, valid, meta in folds:
            self.assertEqual(meta["embargo_days"],7)
            self.assertTrue(all(x["partition"]=="TRAIN" for x in train+valid))
            self.assertGreaterEqual(
                min(datetime.fromisoformat(x["kickoff_utc"].replace("Z","+00:00"))
                    for x in valid) -
                max(datetime.fromisoformat(x["kickoff_utc"].replace("Z","+00:00"))
                    for x in train), timedelta(days=7))
            train_keys = {tuple(k) for k in keys_for(train)}
            valid_keys = {tuple(k) for k in keys_for(valid)}
            self.assertTrue(previous_train <= train_keys)
            previous_train = train_keys
            self.assertFalse(valid_keys & val_keys)
            val_keys |= valid_keys
            self.assertFalse(train_keys & valid_keys)
        self.assertEqual(
            [m for _,_,m in chronological_folds(rows)],
            [m for _,_,m in folds])

    def test_validation_and_protected_english_are_rejected(self):
        for rogue in [sample(301,partition="VALIDATION"),
                      sample(301,league="ENG")]:
            with self.assertRaises(ResearchSafetyError):
                chronological_folds(training()+[rogue])

    def test_duplicate_fixture_is_rejected(self):
        rows = training()
        rows.append(copy.deepcopy(rows[20]))
        with self.assertRaisesRegex(ResearchSafetyError,"DUPLICATE"):
            chronological_folds(rows)

    def test_same_kickoff_stays_in_one_interval(self):
        rows = [sample(i,kickoff=datetime(2023,1,1,tzinfo=timezone.utc)
                       +timedelta(days=i//2)) for i in range(300)]
        folds = chronological_folds(rows)
        for tr,va,_ in folds:
            self.assertFalse(set(x["kickoff_utc"] for x in tr) &
                             set(x["kickoff_utc"] for x in va))

    def test_train_only_laplace_does_not_read_validation_labels(self):
        tr = training(240)
        va = [sample(i,partition="VALIDATION") for i in range(240,260)]
        out = laplace_baseline(tr,va)
        altered=copy.deepcopy(va)
        for row in altered:
            row["label"]="1"
        self.assertEqual(out,laplace_baseline(tr,altered))
        self.assertEqual(len(out),len(va))
        self.assertAlmostEqual(sum(out[0].values()),1)
        self.assertTrue(all(0<x<1 for x in out[0].values()))


if __name__=="__main__":
    unittest.main()
