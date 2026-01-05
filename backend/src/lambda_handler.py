import requests
import time
import random
import json
from datetime import datetime
import boto3
import concurrent.futures
from url_loader import load_urls_from_json, validate_urls
from email_sender import send_performance_report
from config import (
    TOTAL_DURATION, PHASE_LENGTH, CONCURRENCY_STEPS,
    OUTPUT_BUCKET, OUTPUT_PREFIX, REQUEST_TIMEOUT,
    BATCH_SLEEP_MIN, BATCH_SLEEP_MAX, MAX_THREAD_POOL_SIZE
)

# Initialize AWS clients
s3 = boto3.client("s3")


async def hit_url_async(session, url):
    start = time.time()
    try:
        async with session.get(url, timeout=REQUEST_TIMEOUT) as response:
            return {
                "url": url,
                "status": response.status,
                "time": time.time() - start,
                "success": response.status < 400
            }
    except Exception as e:
        return {"url": url, "error": str(e), "time": time.time() - start, "success": False}


def hit_url(url, request_timeout=REQUEST_TIMEOUT):
    """Perform a single HTTP GET and measure response time."""
    start = time.time()
    try:
        response = requests.get(url, timeout=request_timeout)
        return {
            "url": url,
            "status": response.status_code,
            "time": time.time() - start,
            "success": response.status_code < 400
        }
    except Exception as e:
        return {
            "url": url,
            "error": str(e),
            "time": time.time() - start,
            "success": False
        }


def run_phase(urls, concurrency, duration, request_timeout=REQUEST_TIMEOUT):
    """Run one ramp phase with given concurrency and duration."""
    print(f"Running phase with concurrency={concurrency} for {duration}s")
    end_time = time.time() + duration
    results = []

    # Limit max threads to a reasonable number (configurable)
    max_threads = min(concurrency, MAX_THREAD_POOL_SIZE)
    # Calculate how many batches we need to achieve target concurrency
    batches_needed = max(1, concurrency // max_threads)

    print(f"Using {max_threads} threads with {batches_needed} "
          f"batches per cycle")

    while time.time() < end_time:
        # Run multiple batches to simulate higher concurrency
        for batch_num in range(batches_needed):
            if time.time() >= end_time:
                break

            # Launch a batch of concurrent requests
            with concurrent.futures.ThreadPoolExecutor(
                max_workers=max_threads
            ) as executor:
                # Select random URLs for this batch
                batch_urls = [random.choice(urls) for _ in range(max_threads)]
                futures = [executor.submit(
                    hit_url, url, request_timeout) for url in batch_urls]

                for future in concurrent.futures.as_completed(futures):
                    results.append(future.result())

        # Small pause between batch cycles to prevent overwhelming
        remaining_time = end_time - time.time()
        if remaining_time > 0:
            sleep_time = min(
                random.uniform(BATCH_SLEEP_MIN, BATCH_SLEEP_MAX),
                remaining_time
            )
            time.sleep(sleep_time)

    return results


def calculate_metrics(all_results, filter_url=None):
    """Calculate comprehensive performance metrics."""
    # Filter by URL if specified
    if filter_url:
        all_results = [r for r in all_results if r.get("url") == filter_url]

    success_results = [r for r in all_results if r.get("success", False)]
    error_results = [r for r in all_results if not r.get("success", False)]

    success_times = [r["time"] for r in success_results]

    # Status code breakdown
    status_codes = {}
    for result in all_results:
        status = result.get("status", "error")
        status_codes[status] = status_codes.get(status, 0) + 1

    # Response time percentiles
    percentiles = {}
    if success_times:
        success_times.sort()
        percentiles = {
            "p50": success_times[int(len(success_times) * 0.5)],
            "p90": success_times[int(len(success_times) * 0.9)],
            "p95": success_times[int(len(success_times) * 0.95)],
            "p99": (success_times[int(len(success_times) * 0.99)]
                    if len(success_times) >= 100 else success_times[-1])
        }

    return {
        "success_times": success_times,
        "error_results": error_results,
        "status_codes": status_codes,
        "percentiles": percentiles
    }


def calculate_per_url_metrics(all_results):
    """Calculate metrics broken down by individual URL."""
    # Get unique URLs from results
    unique_urls = list(set([r.get("url") for r in all_results
                            if r.get("url")]))

    per_url_metrics = {}

    for url in unique_urls:
        url_results = [r for r in all_results if r.get("url") == url]
        url_metrics = calculate_metrics(url_results)

        success_count = len(url_metrics["success_times"])
        total_count = len(url_results)
        success_times = url_metrics["success_times"]

        # Calculate success rate
        success_rate = ((success_count / total_count) * 100
                        if total_count > 0 else 0)

        # Calculate average response time
        avg_time = (sum(success_times) / len(success_times)
                    if success_times else None)

        per_url_metrics[url] = {
            "total_requests": total_count,
            "success_count": success_count,
            "error_count": len(url_metrics["error_results"]),
            "success_rate_percent": round(success_rate, 2),
            "avg_response_time": (round(avg_time, 3)
                                  if avg_time is not None else None),
            "min_response_time": (round(min(success_times), 3)
                                  if success_times else None),
            "max_response_time": (round(max(success_times), 3)
                                  if success_times else None),
            "percentiles": {k: round(v, 3)
                            for k, v in url_metrics["percentiles"].items()},
            "status_codes": url_metrics["status_codes"],
            "errors": [{"error": r.get("error", "Unknown error"),
                        "time": r.get("time", 0)}
                       for r in url_metrics["error_results"]]
        }

    return per_url_metrics


def save_results_locally(summary, detailed_results, timestamp):
    """Save detailed results to local JSON files."""
    try:
        import os
        # Create results directory if it doesn't exist
        results_dir = "results"
        os.makedirs(results_dir, exist_ok=True)

        # Save summary
        summary_file = f"{results_dir}/summary_{timestamp}.json"
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)

        # Save detailed results
        detailed_file = f"{results_dir}/detailed_{timestamp}.json"
        with open(detailed_file, 'w') as f:
            json.dump(detailed_results, f, indent=2)

        print("Results saved locally:")
        print(f"  Summary: {summary_file}")
        print(f"  Detailed: {detailed_file}")
        return True

    except Exception as e:
        print(f"Failed to save results locally: {e}")
        return False


def save_results_to_s3(summary, detailed_results, timestamp):
    """Save detailed results to S3."""
    try:
        # Save summary
        s3.put_object(
            Bucket=OUTPUT_BUCKET,
            Key=f"{OUTPUT_PREFIX}summary_{timestamp}.json",
            Body=json.dumps(summary, indent=2).encode("utf-8"),
            ContentType="application/json"
        )

        # Save detailed results
        s3.put_object(
            Bucket=OUTPUT_BUCKET,
            Key=f"{OUTPUT_PREFIX}detailed_{timestamp}.json",
            Body=json.dumps(detailed_results, indent=2).encode("utf-8"),
            ContentType="application/json"
        )

        print(f"Results saved to S3: {OUTPUT_BUCKET}/{OUTPUT_PREFIX}")
        return True

    except Exception as e:
        print(f"Failed to save results to S3: {e}")
        return False


def process(event, context):
    """Main Lambda handler function."""
    start_time = time.time()
    timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%S")

    print("Loading URLs from input.json...")
    # Support event overrides when called via FastAPI
    if event and isinstance(event, dict) and event.get("urls"):
        urls = event.get("urls")
        urls = validate_urls(urls)
    else:
        urls = load_urls_from_json()
        urls = validate_urls(urls)

    if not urls:
        return {
            "statusCode": 400,
            "body": json.dumps({"error": "No valid URLs found"})
        }

    print(f"Starting ramp test with {len(urls)} URLs")
    # Allow overriding concurrency/phase length/request timeout from the event
    concurrency_steps = event.get("concurrency_steps") if event and isinstance(
        event, dict) and event.get("concurrency_steps") else CONCURRENCY_STEPS
    phase_length = event.get("phase_length") if event and isinstance(
        event, dict) and event.get("phase_length") else PHASE_LENGTH
    request_timeout = event.get("request_timeout") if event and isinstance(
        event, dict) and event.get("request_timeout") else REQUEST_TIMEOUT
    print(f"Concurrency pattern: {concurrency_steps}")

    all_results = []
    phase_summaries = []

    # Run each phase
    for idx, concurrency in enumerate(concurrency_steps):
        phase_start = time.time()

        print(f"Phase {idx + 1}/{len(CONCURRENCY_STEPS)}: "
              f"{concurrency} concurrent users")
        print(f"Phase duration: {phase_length / 60:.1f} minutes")

        phase_results = run_phase(
            urls, concurrency, phase_length, request_timeout=request_timeout)
        all_results.extend(phase_results)

        # Calculate phase metrics
        phase_metrics = calculate_metrics(phase_results)
        phase_summary = {
            "phase": idx + 1,
            "concurrency": concurrency,
            "duration": time.time() - phase_start,
            "requests": len(phase_results),
            "success_count": len([r for r in phase_results if r.get("success", False)]),
            "error_count": len([r for r in phase_results if not r.get("success", False)]),
            "avg_response_time": sum(phase_metrics["success_times"]) / len(phase_metrics["success_times"]) if phase_metrics["success_times"] else 0
        }
        phase_summaries.append(phase_summary)
        print(
            f"Phase {idx + 1} completed: {phase_summary['success_count']}/{phase_summary['requests']} successful")

    # Calculate overall metrics
    overall_metrics = calculate_metrics(all_results)

    # Calculate per-URL metrics
    per_url_metrics = calculate_per_url_metrics(all_results)

    # Create comprehensive summary
    summary = {
        "timestamp": datetime.utcnow().isoformat(),
        "test_duration_sec": round(time.time() - start_time, 2),
        "total_requests": len(all_results),
        "success_count": len(overall_metrics["success_times"]),
        "error_count": len(overall_metrics["error_results"]),
        "success_rate_percent": round((len(overall_metrics["success_times"]) / len(all_results)) * 100, 2) if all_results else 0,
        "avg_time": round(sum(overall_metrics["success_times"]) / len(overall_metrics["success_times"]), 3) if overall_metrics["success_times"] else None,
        "min_time": round(min(overall_metrics["success_times"]), 3) if overall_metrics["success_times"] else None,
        "max_time": round(max(overall_metrics["success_times"]), 3) if overall_metrics["success_times"] else None,
        "percentiles": {k: round(v, 3) for k, v in overall_metrics["percentiles"].items()},
        "status_codes": overall_metrics["status_codes"],
        "phase_summaries": phase_summaries,
        "urls_tested": len(urls),
        "concurrency_pattern": concurrency_steps,
        "per_url_metrics": per_url_metrics
    }

    # Prepare detailed results
    detailed_results = {
        "summary": summary,
        "all_requests": all_results,
        "phase_details": phase_summaries,
        "per_url_results": per_url_metrics,
        "test_configuration": {
            "total_duration": event.get("total_duration", TOTAL_DURATION) if event and isinstance(event, dict) else TOTAL_DURATION,
            "phase_length": phase_length,
            "concurrency_steps": concurrency_steps,
            "request_timeout": request_timeout
        }
    }

    # Save results locally
    save_results_locally(summary, detailed_results, timestamp)

    # Save results to S3 (if running in AWS) unless explicitly disabled in the event
    if not (event and isinstance(event, dict) and event.get("save_to_s3") is False):
        try:
            save_results_to_s3(summary, detailed_results, timestamp)
        except Exception as e:
            print(f"S3 save failed (expected for local testing): {e}")

    # Send email report unless explicitly disabled in the event
    try:
        if not (event and isinstance(event, dict) and event.get("send_email") is False):
            email_sent = send_performance_report(summary, detailed_results)
        else:
            email_sent = False
        summary["email_sent"] = email_sent
    except Exception as e:
        print(f"Failed to send email: {e}")
        summary["email_sent"] = False
        summary["email_error"] = str(e)

    print("Performance test completed successfully!")
    print("Summary:", json.dumps(summary, indent=2))

    return {
        "statusCode": 200,
        "body": json.dumps({
            "message": "Performance test completed successfully",
            "summary": summary
        })
    }


# For local testing
if __name__ == "__main__":
    # Mock context for local testing
    class MockContext:
        def __init__(self):
            self.function_name = "performance-test-local"
            self.memory_limit_in_mb = 512
            self.invoked_function_arn = "local"

    result = process({}, MockContext())
    print(json.dumps(result, indent=2))
