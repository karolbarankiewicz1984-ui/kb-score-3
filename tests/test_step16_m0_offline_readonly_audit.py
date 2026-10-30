"""Read-only M0 score tests; no provider access and no calibrator fitting."""
import math
import unittest
from scripts.step16_m0_offline_readonly_audit import metrics, ReadOnlyM0Error


class M0ReadOnlyTests(unittest.TestCase):
    def sample(self):
        p={"1":0.5,"X":0.25,"2":0.25}
        y="1"
        ll=-math.log(p[y])
        brier=(.5-1)**2+.25**2+.25**2
        return {"p":p,"y":y,"ll":ll,"bs":brier}

    def test_empty_returns_no_quality_claim(self):
        self.assertIsNone(metrics([]))

    def test_recomputed_loss_brier_and_hit(self):
        r=metrics([self.sample()])
        self.assertEqual(r["n"],1)
        self.assertAlmostEqual(r["brier_sum3"],.375)
        self.assertAlmostEqual(r["log_loss"],math.log(2))
        self.assertEqual(r["top1_accuracy"],1.0)

    def test_disagreeing_persisted_score_fails_closed(self):
        bad=self.sample()
        bad["ll"]+=0.01
        with self.assertRaisesRegex(ReadOnlyM0Error,"PERSISTED_SCORE"):
            metrics([bad])

    def test_invalid_probability_fails_closed(self):
        bad=self.sample()
        bad["p"]={"1":0.8,"X":0.4,"2":-0.2}
        with self.assertRaises(ReadOnlyM0Error):
            metrics([bad])


if __name__=="__main__":
    unittest.main()
