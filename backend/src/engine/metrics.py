

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
        per_url_metrics[url] = {
            "total_requests": total,
            "successful_requests": success_count,
            "average_time": avg_time,
            "success_rate": success_rate,
            "percentiles": {k: round(v, 3) for k, v in metrics["percentiles"].items()},
            "status_codes": metrics["status_codes"]
        }
    return per_url_metrics
