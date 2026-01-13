# api_socket_single_client.py
from flask import Flask
from flask_socketio import SocketIO, emit
from engine.core import run_performance_test
from url_loader import validate_urls, load_urls_from_json
from config import CONCURRENCY_STEPS, PHASE_LENGTH, REQUEST_TIMEOUT
import os

app = Flask(__name__)

# Get port from environment (App Runner provides PORT env var)
port = int(os.environ.get('PORT', 5001))

# Configure SocketIO with proper async mode and CORS
socketio = SocketIO(
    app,
    cors_allowed_origins="*",  # In production, use your Next.js domain
    async_mode='eventlet',
    logger=True,
    engineio_logger=True,
    ping_timeout=60,
    ping_interval=25
)

# ------------------------
# HTTP Endpoint: Health Check
# ------------------------


@app.route("/health", methods=["GET"])
def health_check():
    return {"status": "healthy"}, 200


@app.route("/", methods=["GET"])
def root():
    return {"status": "running", "service": "performance-test-api"}, 200


# ------------------------
# WebSocket: Client connects
# ------------------------
@socketio.on("connect")
def handle_connect():
    print("Client connected")
    emit("connected", {"message": "WebSocket connected"})


@socketio.on("disconnect")
def handle_disconnect():
    print("Client disconnected")


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
    try:
        # ------------------------
        # Load & validate URLs
        # ------------------------
        urls = data.get("urls", []) or load_urls_from_json()
        urls = validate_urls(urls)
        if not urls:
            emit("error", {"error": "No valid URLs provided"})
            return

        concurrency_steps = data.get("concurrency", CONCURRENCY_STEPS)
        phase_length = data.get("phase_length", PHASE_LENGTH)
        request_timeout = data.get("request_timeout", REQUEST_TIMEOUT)
        test_id = data.get("test_id")

        if not test_id:
            emit("error", {"error": "test_id is required to start the test"})
            return

        total_phases = len(concurrency_steps)
        phase_summaries = []

        socketio.emit("test_started", {
                      "message": "Test started", "test_id": test_id})
        print(f"Starting performance test {test_id}...")

        # ------------------------
        # Run phases synchronously (single client)
        # ------------------------
        for idx, concurrency in enumerate(concurrency_steps):
            # Run one phase using the stateless engine
            phase_results_summary, detailed = run_performance_test(
                urls=urls,
                concurrency_steps=[concurrency],
                phase_length=phase_length,
                request_timeout=request_timeout,
                save_to_s3=False,
                send_email=False
            )

            requests_for_phase = len(detailed.get("all_requests", []))
            phase_summary = {
                "phase": idx + 1,
                "test_id": test_id,
                "total_phases": total_phases,
                "concurrency": concurrency,
                "requests": requests_for_phase,
                "success_count": phase_results_summary.get("success_count", 0),
                "error_count": phase_results_summary.get("error_count", 0),
                "percentiles": phase_results_summary.get("percentiles", {}),
            }
            phase_summaries.append(phase_summary)

            # Emit phase completion event to the client
            socketio.emit("phase_complete", phase_summary)
            print(f'Phase {idx + 1} completed')

        # ------------------------
        # Emit final test summary
        # ------------------------
        final_summary = {
            "test_id": test_id,
            "phase_summaries": phase_summaries,
            "total_requests": sum(p["requests"] for p in phase_summaries),
            "success_count": sum(p["success_count"] for p in phase_summaries),
            "error_count": sum(p["error_count"] for p in phase_summaries),
        }

        socketio.emit("test_completed", final_summary)
        print(f'Test {test_id} completed')

    except Exception as e:
        print(f"Error during test: {str(e)}")
        emit("error", {"error": str(e)})


# ------------------------
# Run Flask-SocketIO server
# ------------------------
if __name__ == "__main__":
    print(f"Starting server on port {port}")
    socketio.run(
        app,
        host="0.0.0.0",
        port=port,
        debug=False,
        use_reloader=False
    )
