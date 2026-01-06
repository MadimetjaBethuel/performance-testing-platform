import time
import random
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from config import REQUEST_TIMEOUT, MAX_THREAD_POOL_SIZE, BATCH_SLEEP_MIN, BATCH_SLEEP_MAX


def hit_url(url, request_timeout=REQUEST_TIMEOUT):
    start = time.time()
    try:
        response = requests.get(url, timeout=request_timeout)
        latency = time.time() - start
        return {
            "url": url,
            "status_code": response.status_code,
            "latency": latency,
            "success": True,
            "error": None
        }
    except requests.RequestException as e:
        latency = time.time() - start
        return {
            "url": url,
            "status_code": "error",
            "latency": latency,
            "success": False,
            "error": str(e)
        }


def run_phase(urls, concurrency, duration, request_timeout=REQUEST_TIMEOUT):
    end_time = time.time() + duration
    results = []

    max_threads = min(concurrency, MAX_THREAD_POOL_SIZE)
    batches_needed = max(1, concurrency // max_threads)

    while time.time() < end_time:
        for _ in range(batches_needed):
            if time.time() >= end_time:
                break

            batch_urls = [random.choice(urls) for _ in range(max_threads)]
            with ThreadPoolExecutor(max_workers=max_threads) as executor:
                future_to_url = {executor.submit(
                    hit_url, url, request_timeout): url for url in batch_urls}
                for future in as_completed(future_to_url):
                    result = future.result()
                    results.append(result)

                remaining_time = end_time - time.time()
                if remaining_time > 0:
                    time.sleep(
                        min(random.uniform(BATCH_SLEEP_MIN, BATCH_SLEEP_MAX), remaining_time))

    return results
