"""Unit tests for JTL row parsing, LiveAggregator, and JTL-side metrics.

The async run_scenario() is not tested here — it requires a real JMeter binary.
That gets exercised end-to-end inside the Docker container.
"""

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from engine.jmeter_runner import JtlRow, LiveAggregator, parse_jtl_row  # noqa: E402
from engine.metrics import (  # noqa: E402
    calculate_per_label_metrics,
    summarize_jtl_rows,
)


def _row(
    *,
    label: str = "GET /",
    elapsed: int = 100,
    success: bool = True,
    response_code: str = "200",
    failure_message: str = "",
    response_message: str = "OK",
    timestamp: int = 1_000_000_000_000,
    url: str = "https://example.com/",
) -> JtlRow:
    return JtlRow(
        timestamp=timestamp,
        elapsed=elapsed,
        label=label,
        response_code=response_code,
        response_message=response_message,
        thread_name="t1",
        success=success,
        failure_message=failure_message,
        bytes_count=0,
        url=url,
        latency=elapsed,
        connect=0,
    )


class ParseJtlRow(unittest.TestCase):
    HEADER = [
        "timeStamp", "elapsed", "label", "responseCode", "responseMessage",
        "threadName", "dataType", "success", "failureMessage", "bytes",
        "sentBytes", "grpThreads", "allThreads", "URL", "Latency",
        "IdleTime", "Connect",
    ]

    def _values(self, **overrides):
        defaults = {
            "timeStamp": "1700000000000",
            "elapsed": "123",
            "label": "GET /get",
            "responseCode": "200",
            "responseMessage": "OK",
            "threadName": "Users 1-1",
            "dataType": "text",
            "success": "true",
            "failureMessage": "",
            "bytes": "100",
            "sentBytes": "50",
            "grpThreads": "1",
            "allThreads": "1",
            "URL": "https://httpbin.org/get",
            "Latency": "120",
            "IdleTime": "0",
            "Connect": "10",
        }
        defaults.update(overrides)
        return [defaults[col] for col in self.HEADER]

    def test_parses_valid_row(self):
        row = parse_jtl_row(self.HEADER, self._values())
        self.assertIsNotNone(row)
        assert row is not None  # for type checkers
        self.assertEqual(row.label, "GET /get")
        self.assertEqual(row.elapsed, 123)
        self.assertTrue(row.success)
        self.assertEqual(row.response_code, "200")
        self.assertEqual(row.url, "https://httpbin.org/get")

    def test_failed_row(self):
        row = parse_jtl_row(self.HEADER, self._values(success="false", responseCode="500", failureMessage="boom"))
        assert row is not None
        self.assertFalse(row.success)
        self.assertEqual(row.failure_message, "boom")

    def test_mismatched_columns_returns_none(self):
        self.assertIsNone(parse_jtl_row(self.HEADER, ["just", "two"]))

    def test_unparseable_numerics_returns_none(self):
        self.assertIsNone(parse_jtl_row(self.HEADER, self._values(elapsed="not-a-number")))


class Aggregator(unittest.TestCase):
    def test_counts_successes_and_errors(self):
        agg = LiveAggregator()
        agg.feed(_row(elapsed=100, success=True))
        agg.feed(_row(elapsed=200, success=False))
        agg.feed(_row(elapsed=300, success=True))
        snap = agg.snapshot()
        self.assertEqual(snap["samples"], 3)
        self.assertEqual(snap["success"], 2)
        self.assertEqual(snap["errors"], 1)
        self.assertAlmostEqual(snap["error_rate"], 1 / 3)
        self.assertEqual(snap["avg_latency_ms"], (100 + 200 + 300) / 3)

    def test_empty_snapshot_safe(self):
        snap = LiveAggregator().snapshot()
        self.assertEqual(snap["samples"], 0)
        self.assertIsNone(snap["avg_latency_ms"])
        self.assertIsNone(snap["p95_latency_ms_rolling"])

    def test_rolling_window_caps(self):
        agg = LiveAggregator()
        agg._recent_max = 5
        for i in range(20):
            agg.feed(_row(elapsed=i))
        # Internal: only last 5 should be retained for rolling p95
        self.assertEqual(len(agg._recent), 5)
        self.assertEqual(agg._recent, [15, 16, 17, 18, 19])


class SummarizeJtl(unittest.TestCase):
    def test_empty(self):
        s = summarize_jtl_rows([])
        self.assertEqual(s["total_samples"], 0)
        self.assertEqual(s["error_rate"], 0)
        self.assertIsNone(s["avg_latency_ms"])

    def test_all_success(self):
        rows = [_row(elapsed=t, timestamp=1700000000000 + t) for t in (10, 20, 30, 40, 50)]
        s = summarize_jtl_rows(rows)
        self.assertEqual(s["total_samples"], 5)
        self.assertEqual(s["success_count"], 5)
        self.assertEqual(s["error_count"], 0)
        self.assertEqual(s["error_rate"], 0)
        self.assertEqual(s["avg_latency_ms"], 30)
        self.assertEqual(s["percentiles"]["p50"], 30)

    def test_mixed(self):
        rows = [
            _row(elapsed=100, success=True, timestamp=1_000),
            _row(elapsed=200, success=False, timestamp=1_500),
            _row(elapsed=150, success=True, timestamp=2_000),
        ]
        s = summarize_jtl_rows(rows)
        self.assertEqual(s["total_samples"], 3)
        self.assertEqual(s["success_count"], 2)
        self.assertEqual(s["error_count"], 1)
        self.assertAlmostEqual(s["error_rate"], 1 / 3)


class PerLabelMetrics(unittest.TestCase):
    def test_groups_by_label(self):
        rows = [
            _row(label="GET /a", elapsed=100, success=True),
            _row(label="GET /a", elapsed=200, success=True),
            _row(label="GET /b", elapsed=50, success=False, response_code="500", failure_message="boom"),
        ]
        out = calculate_per_label_metrics(rows)
        self.assertIn("GET /a", out)
        self.assertIn("GET /b", out)
        self.assertEqual(out["GET /a"]["total_requests"], 2)
        self.assertEqual(out["GET /a"]["successful_requests"], 2)
        self.assertEqual(out["GET /a"]["average_time"], 150)
        self.assertEqual(out["GET /b"]["total_requests"], 1)
        self.assertEqual(out["GET /b"]["successful_requests"], 0)
        self.assertEqual(len(out["GET /b"]["errors"]), 1)
        self.assertEqual(out["GET /b"]["errors"][0]["status_code"], "500")
        self.assertEqual(out["GET /b"]["errors"][0]["error"], "boom")


if __name__ == "__main__":
    unittest.main()
