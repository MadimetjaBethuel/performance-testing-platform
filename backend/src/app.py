# api_socket_single_client.py

from flask import Flask
from flask_socketio import SocketIO, emit
from engine.core import run_performance_test
from url_loader import validate_urls, load_urls_from_json
from config import CONCURRENCY_STEPS, PHASE_LENGTH, REQUEST_TIMEOUT

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")  # allow Next.js

# ------------------------
# HTTP Endpoint: Health Check
# ------------------------


@app.route("/health", methods=["GET"])
def health_check():
    return {"status": "healthy"}, 200


# ------------------------
# WebSocket: Client connects
# ------------------------
@socketio.on("connect")
def handle_connect():
    emit("connected", {"message": "WebSocket connected"})


# ------------------------
# WebSocket: Start performance test
# ------------------------
@socketio.on("start_test")
def handle_start_test(data):
    """
    Stateless performance test.
    Emits:
        - "phase_complete" after each phase
        - "test_completed" after all phases
    """
    # ------------------------
    # Load & validate URLs
    # ------------------------
    urls = data.get("urls", []) or load_urls_from_json()
    urls = validate_urls(urls)
    if not urls:
        emit("error", {"error": "No valid URLs provided"})
        return

    concurrency_steps = data.get("concurrency_steps", CONCURRENCY_STEPS)
    phase_length = data.get("phase_length", PHASE_LENGTH)
    request_timeout = data.get("request_timeout", REQUEST_TIMEOUT)

    total_phases = len(concurrency_steps)
    phase_summaries = []

    emit("test_started", {"message": "Test started"})

    # ------------------------
    # Run phases synchronously (single client)
    # ------------------------
    for idx, concurrency in enumerate(concurrency_steps):
        # Run one phase using the stateless engine
        phase_results_summary, all_requests = run_performance_test(
            urls=urls,
            concurrency_steps=[concurrency],
            phase_length=phase_length,
            request_timeout=request_timeout,
            save_to_s3=False,
            send_email=False
        )

        phase_summary = {
            "phase": idx + 1,
            "total_phases": total_phases,
            "concurrency": concurrency,
            "requests": len(all_requests),
            "success_count": phase_results_summary["success_count"],
            "error_count": phase_results_summary["error_count"],
            "percentiles": phase_results_summary.get("percentiles", {}),
        }

        print(phase_summary)

        phase_summaries.append(phase_summary)

        # Emit phase completion event to the client
        emit("phase_complete", phase_summary)

    # ------------------------
    # Emit final test summary
    # ------------------------
    final_summary = {
        "phase_summaries": phase_summaries,
        "total_requests": sum(p["requests"] for p in phase_summaries),
        "success_count": sum(p["success_count"] for p in phase_summaries),
        "error_count": sum(p["error_count"] for p in phase_summaries),
    }
    emit("test_completed", final_summary)


# ------------------------
# Run Flask-SocketIO server
# ------------------------
if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5001)
