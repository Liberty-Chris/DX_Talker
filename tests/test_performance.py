"""Performance policy checks use evidence fixtures, not timing-dependent assertions."""
import unittest

from dxtalker.performance import BUDGETS, violations


class PerformanceTests(unittest.TestCase):
    def test_within_budget_passes_and_missing_or_invalid_evidence_fails(self):
        metrics = {key: limit / 2 for key, limit in BUDGETS.items()}
        self.assertEqual(violations(metrics), [])
        for value in (None, float('nan'), float('inf'), -1):
            self.assertTrue(violations(dict(metrics, navigation_median_ms=value)))
        self.assertTrue(violations({}))

    def test_each_budget_can_fail_the_build(self):
        metrics = {key: 0 for key in BUDGETS}
        for key, limit in BUDGETS.items():
            failures = violations({**metrics, key: limit + 1})
            self.assertEqual(len(failures), 1)
            self.assertTrue(failures[0].startswith(key + ':'))

    def test_reproduced_a14_navigation_and_idle_regression_is_rejected(self):
        metrics = dict(ui_startup_ms=1517, navigation_median_ms=173,
                       navigation_p95_ms=620, scroll_median_ms=0,
                       scroll_p95_ms=0, idle_cpu_ratio=0.385 / 3)
        failures = violations(metrics)
        self.assertTrue(any(value.startswith('navigation_median_ms:') for value in failures))
        self.assertTrue(any(value.startswith('idle_cpu_ratio:') for value in failures))
