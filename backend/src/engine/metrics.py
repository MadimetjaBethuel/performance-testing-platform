

def calculate_metrics(all_results, filter_url=None):

    if filter_url:
        all_results = [r for r in all_results if r.get('url') == filter_url]

    success_results = [r for r in all_results if r.get('success', False)]
    error_results = [r for r in all_results if not r.get('success', False)]

    success_times = [r['latency'] for r in success_results]

    status_codes = {}
    for r in all_results:
        code = r.get('status_code', 'error')
        status_codes[code] = status_codes.get(code, 0) + 1

    percentiles = {}
    if success_times:
        success_times.sort()
        percentiles = {
            "p50": success_times[int(len(success_times) * 0.5)],
            "p90": success_times[int(len(success_times) * 0.9)],
            "p95": success_times[int(len(success_times) * 0.95)],
            "p99": success_times[int(len(success_times) * 0.99)] if len(success_times) >= 100 else success_times[-1]
        }

    return {
        "success_times": success_times,
        "error_results": error_results,
        "status_codes": status_codes,
        "percentiles": percentiles
    }


def calculate_per_url_metrics(all_results):
    unique_urls = list(set(r.get("url") for r in all_results if r.get("url")))
    per_url_metrics = {}

    for url in unique_urls:
        results = [r for r in all_results if r.get("url") == url]
        metrics = calculate_metrics(results, filter_url=url)
        success_times = metrics["success_times"]
        total = len(results)
        success_count = len(success_times)
        avg_time = sum(success_times) / \
            len(success_times) if success_times else None
        success_rate = (success_count/total) * 100 if total else 0

        error_buckets = {}
        for r in metrics["error_results"]:
            key = (r.get("status_code", "error"), r.get("error") or "Unknown error")
            error_buckets[key] = error_buckets.get(key, 0) + 1
        errors = [
            {"status_code": code, "error": msg, "count": count}
            for (code, msg), count in error_buckets.items()
        ]

        per_url_metrics[url] = {
            "total_requests": total,
            "successful_requests": success_count,
            "average_time": avg_time,
            "success_rate": success_rate,
            "percentiles": {k: round(v, 3) for k, v in metrics["percentiles"].items()},
            "status_codes": metrics["status_codes"],
            "errors": errors,
        }
    return per_url_metrics


# ---------------------------------------------------------------------------
# JTL-derived metrics (for the scenario / JMeter flow).
#
# These operate on JtlRow-like objects produced by engine.jmeter_runner. They
# duck-type the attributes (`success`, `elapsed`, `label`, `response_code`,
# `failure_message`, `response_message`, `timestamp`, `url`) so we don't have
# to import the runner here and create a circular dependency.
# ---------------------------------------------------------------------------


def _percentiles_from_sorted(sorted_values):
    if not sorted_values:
        return {}
    n = len(sorted_values)

    def at(p):
        return sorted_values[min(int(n * p), n - 1)]

    return {
        "p50": at(0.50),
        "p90": at(0.90),
        "p95": at(0.95),
        "p99": at(0.99),
    }


def summarize_jtl_rows(rows):
    """Overall scenario metrics across all JTL samples."""
    if not rows:
        return {
            "total_samples": 0,
            "success_count": 0,
            "error_count": 0,
            "error_rate": 0,
            "avg_latency_ms": None,
            "percentiles": {},
            "throughput_per_sec": 0,
            "duration_seconds": 0,
        }
    successes = [r for r in rows if r.success]
    success_lat = sorted(r.elapsed for r in successes)
    timestamps = [r.timestamp for r in rows if r.timestamp]
    span_ms = (max(timestamps) - min(timestamps)) if timestamps else 0
    span_s = (span_ms / 1000.0) if span_ms else 0
    duration_for_rate = span_s if span_s > 0 else 1
    return {
        "total_samples": len(rows),
        "success_count": len(successes),
        "error_count": len(rows) - len(successes),
        "error_rate": (len(rows) - len(successes)) / len(rows),
        "avg_latency_ms": (sum(success_lat) / len(success_lat)) if success_lat else None,
        "percentiles": _percentiles_from_sorted(success_lat),
        "throughput_per_sec": len(rows) / duration_for_rate,
        "duration_seconds": span_s,
    }


def calculate_per_label_metrics(rows):
    """Per-step (per JMeter label) metrics. Parallel to calculate_per_url_metrics."""
    by_label: dict = {}
    for r in rows:
        by_label.setdefault(r.label, []).append(r)

    out = {}
    for label, group in by_label.items():
        successes = [r for r in group if r.success]
        lat = sorted(r.elapsed for r in successes)

        error_buckets: dict = {}
        for r in group:
            if r.success:
                continue
            key = (
                r.response_code or "error",
                r.failure_message or r.response_message or "Unknown error",
            )
            error_buckets[key] = error_buckets.get(key, 0) + 1

        out[label] = {
            "total_requests": len(group),
            "successful_requests": len(successes),
            "average_time": (sum(lat) / len(lat)) if lat else None,
            "success_rate": (len(successes) / len(group)) * 100 if group else 0,
            "percentiles": _percentiles_from_sorted(lat),
            "errors": [
                {"status_code": code, "error": msg, "count": count}
                for (code, msg), count in error_buckets.items()
            ],
            "sample_url": group[0].url if group else "",
        }
    return out
