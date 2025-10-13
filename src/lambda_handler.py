import asyncio
import aiohttp
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


def hit_url(url):
    """Perform a single HTTP GET and measure response time."""
    start = time.time()
    try:
        response = requests.get(url, timeout=REQUEST_TIMEOUT)
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


def run_phase(urls, concurrency, duration):
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
                futures = [executor.submit(hit_url, url) for url in batch_urls]

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


def calculate_metrics(all_results):
    """Calculate comprehensive performance metrics."""
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
            "p99": success_times[int(len(success_times) * 0.99)] if len(success_times) >= 100 else success_times[-1]
        }

    return {
        "success_times": success_times,
        "error_results": error_results,
        "status_codes": status_codes,
        "percentiles": percentiles
    }


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


def lambda_handler(event, context):
    """Main Lambda handler function."""
    start_time = time.time()
    timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%S")

    print("Loading URLs from input.json...")
    urls = load_urls_from_json()
    urls = validate_urls(urls)

    if not urls:
        return {
            "statusCode": 400,
            "body": json.dumps({"error": "No valid URLs found"})
        }

    print(f"Starting 10-minute ramp test with {len(urls)} URLs")
    print(f"Concurrency pattern: {CONCURRENCY_STEPS}")

    all_results = []
    phase_summaries = []

    # Initialize cumulative phase duration tracking
    cumulative_phase_duration = 0

    # Run each phase
    for idx, concurrency in enumerate(CONCURRENCY_STEPS):
        phase_start = time.time()

        # Add 25 minutes to the cumulative duration for each phase
        cumulative_phase_duration += (25 * 60)  # Add 25 minutes in seconds

        # Calculate total duration for this phase (base + cumulative)
        total_phase_duration = PHASE_LENGTH + cumulative_phase_duration

        print(f"Phase {idx + 1}/{len(CONCURRENCY_STEPS)}: "
              f"{concurrency} concurrent users")
        print(f"Phase duration: {total_phase_duration / 60:.1f} minutes "
              f"(base: {PHASE_LENGTH / 60:.1f} + cumulative: "
              f"{cumulative_phase_duration / 60:.1f})")

        phase_results = run_phase(urls, concurrency, total_phase_duration)
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
        "concurrency_pattern": CONCURRENCY_STEPS
    }

    # Prepare detailed results
    detailed_results = {
        "summary": summary,
        "all_requests": all_results,
        "phase_details": phase_summaries,
        "test_configuration": {
            "total_duration": TOTAL_DURATION,
            "phase_length": PHASE_LENGTH,
            "concurrency_steps": CONCURRENCY_STEPS,
            "request_timeout": REQUEST_TIMEOUT
        }
    }

    # Save results to S3
    save_results_to_s3(summary, detailed_results, timestamp)

    # Send email report
    try:
        email_sent = send_performance_report(summary, detailed_results)
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

    result = lambda_handler({}, MockContext())
    print(json.dumps(result, indent=2))
