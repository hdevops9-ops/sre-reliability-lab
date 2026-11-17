import unittest
from decimal import Decimal
from io import StringIO

from evaluate import Minute, evaluate, read_samples, scenario


class EvaluateTests(unittest.TestCase):
    def test_demo_scenarios(self):
        cases = {
            "healthy": "MONITOR",
            "incident": "PAGE",
            "telemetry-gap": "INVESTIGATE_TELEMETRY",
            "no-traffic": "INSUFFICIENT_TRAFFIC",
        }
        for name, expected in cases.items():
            with self.subTest(name=name):
                self.assertEqual(evaluate(scenario(name), 60)[0], expected)

    def test_short_spike_alone_does_not_page(self):
        samples = scenario("healthy")
        samples[59] = Minute(1000, 100)
        decision, short, long = evaluate(samples, 60)
        self.assertEqual(decision, "MONITOR")
        self.assertEqual(short.burn, Decimal("20.8"))
        self.assertEqual(long.burn, Decimal("2.65"))

    def test_missing_minute_disables_burn_estimate(self):
        _, short, long = evaluate(scenario("telemetry-gap"), 60)
        for window in (short, long):
            self.assertEqual(window.missing, 1)
            self.assertIsNone(window.burn)

    def test_rejects_impossible_counts(self):
        with self.assertRaises(ValueError):
            Minute(2, 3)


class CsvReplayTests(unittest.TestCase):
    def test_replay_keeps_expected_end_when_latest_minute_is_missing(self):
        text = "minute,requests,errors\n" + "".join(
            f"{minute},1000,0\n" for minute in range(59)
        )
        decision, short, _ = evaluate(read_samples(StringIO(text)), 60)
        self.assertEqual(decision, "INVESTIGATE_TELEMETRY")
        self.assertEqual(short.missing, 1)

    def test_duplicate_minutes_are_rejected(self):
        data = StringIO("minute,requests,errors\n0,10,0\n0,10,0\n")
        with self.assertRaisesRegex(ValueError, "Duplicate minute 0"):
            read_samples(data)
