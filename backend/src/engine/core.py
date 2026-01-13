from datetime import datetime
from .runner import run_phase
from .metrics import calculate_metrics, calculate_per_url_metrics
from .upload import save_results_locally
# import uuid
import traceback


def run_performance_test(urls, concurrency_steps, phase_length, request_timeout,
                         save_to_s3=True, send_email=True):

    try:
        all_results = []
        phase_summaries = []

        for idx, concurrency in enumerate(concurrency_steps):
            phase_results = run_phase(
                urls=urls,
                concurrency=concurrency,
                duration=phase_length,
                request_timeout=request_timeout
            )
            all_results.extend(phase_results)
            metrics = calculate_metrics(all_results=phase_results)
            phase_summaries.append({
                "phase": idx + 1,
                "concurrency": concurrency,
                "requests": len(phase_results),
                "successful_requests": len(metrics["success_times"]),
                "error_requests": len(metrics["error_results"]),
                "avg_res_time": sum(metrics["success_times"]) / len(metrics["success_times"]) if metrics["success_times"] else None
            })
        overall_metrics = calculate_metrics(all_results=all_results)
        per_url_metrics = calculate_per_url_metrics(all_results=all_results)

        timestamp = datetime.now().strftime("%Y%m%dT%H%M%S")
        summary = {
            "timestamp": datetime.utcnow().isoformat(),
            "total_requests": len(all_results),
            "success_count": len(overall_metrics["success_times"]),
            "error_count": len(overall_metrics["error_results"]),
            "success_rate_percent": round((len(overall_metrics["success_times"])/len(all_results))*100, 2) if all_results else None,
            "avg_time": sum(overall_metrics["success_times"])/len(overall_metrics["success_times"]) if overall_metrics["success_times"] else None,
            "percentiles": overall_metrics["percentiles"],
            "phase_summaries": phase_summaries,
            "per_url_metrics": per_url_metrics
        }
        detailed = {
            "summary": summary,
            "all_requests": all_results,
            "phase_details": phase_summaries,
            "per_url_results": per_url_metrics
        }
        save_results_locally(
            summary=summary, detailed=detailed, timestamp=timestamp
        )

        return summary, detailed

    except Exception as e:
        print(f"Error during performance test: {e}")
        traceback.print_exc()
        summary = {
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e)
        }
        detailed = {
            "summary": summary,
            "all_requests": [],
            "phase_details": [],
            "per_url_results": {}
        }
        return summary, detailed
