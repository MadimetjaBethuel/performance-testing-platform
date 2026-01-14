import os
import asyncio
import socketio

from flask import Flask, jsonify
from asgiref.wsgi import WsgiToAsgi

from engine.core import run_performance_test
from url_loader import validate_urls, load_urls_from_json
from config import CONCURRENCY_STEPS, PHASE_LENGTH, REQUEST_TIMEOUT

# -------------------------------------------------
# Flask (HTTP / Health / Metadata)
# -------------------------------------------------

flask_app = Flask(__name__)


@flask_app.route("/health", methods=["GET"])
def health_check():
    return jsonify({"status": "healthy"}), 200


@flask_app.route("/", methods=["GET"])
def root():
    return jsonify({
        "status": "running",
        "service": "performance-test-api"
    }), 200


# -------------------------------------------------
# Socket.IO (ASGI / WebSocket)
# -------------------------------------------------

sio = socketio.AsyncServer(
    async_mode="asgi",
    cors_allowed_origins="*"
)

# Wrap Flask WSGI app so it can live inside ASGI
flask_asgi_app = WsgiToAsgi(flask_app)

# Final ASGI application
asgi_app = socketio.ASGIApp(
    sio,
    other_asgi_app=flask_asgi_app
)

# -------------------------------------------------
# Socket.IO Events
# -------------------------------------------------


@sio.event
async def connect(sid, environ):
    print(f"[SOCKET] Client connected: {sid}")
    await sio.emit(
        "connected",
        {"message": "WebSocket connected"},
    )


@sio.event
async def disconnect(sid):
    print(f"[SOCKET] Client disconnected: {sid}")


@sio.event
async def start_test(sid, data):
    """
    Starts a stateless performance test in the background.
    Emits:
      - test_started
      - phase_complete (per phase)
      - test_completed
    """
    try:
        urls = data.get("urls") or load_urls_from_json()
        urls = validate_urls(urls)

        if not urls:
            await sio.emit(
                "error",
                {"error": "No valid URLs provided"},
            )
            return

        test_id = data.get("test_id")
        if not test_id:
            await sio.emit(
                "error",
                {"error": "test_id is required"},
            )
            return

        concurrency_steps = data.get("concurrency", CONCURRENCY_STEPS)
        phase_length = data.get("phase_length", PHASE_LENGTH)
        request_timeout = data.get("request_timeout", REQUEST_TIMEOUT)

        asyncio.create_task(
            run_test_in_background(
                sid=sid,
                test_id=test_id,
                urls=urls,
                concurrency_steps=concurrency_steps,
                phase_length=phase_length,
                request_timeout=request_timeout
            )
        )

        await sio.emit(
            "test_started",
            {"message": "Test started", "test_id": test_id},
        )

        print(f"[TEST] Started test {test_id} for client {sid}")

    except Exception as exc:
        print(f"[ERROR] start_test failed: {exc}")
        await sio.emit(
            "error",
            {"error": str(exc)},
        )


# -------------------------------------------------
# Background Test Runner
# -------------------------------------------------

async def run_test_in_background(
    sid,
    test_id,
    urls,
    concurrency_steps,
    phase_length,
    request_timeout
):
    try:
        total_phases = len(concurrency_steps)
        phase_summaries = []

        print(f"[TEST] Running test {test_id}")

        for index, concurrency in enumerate(concurrency_steps, start=1):
            summary, detailed = await asyncio.to_thread(
                run_performance_test,
                urls=urls,
                concurrency_steps=[
                    concurrency],
                phase_length=phase_length,
                request_timeout=request_timeout,
                save_to_s3=False,
                send_email=False
            )

            requests_count = len(detailed.get("all_requests", []))

            phase_summary = {
                "phase": index,
                "test_id": test_id,
                "total_phases": total_phases,
                "concurrency": concurrency,
                "requests": requests_count,
                "success_count": summary.get("success_count", 0),
                "error_count": summary.get("error_count", 0),
                "percentiles": summary.get("percentiles", {}),
            }

            phase_summaries.append(phase_summary)

            await sio.emit(
                "phase_complete",
                phase_summary,
            )

            print(f"[TEST] Phase {index}/{total_phases} complete")

        final_summary = {
            "test_id": test_id,
            "phase_summaries": phase_summaries,
            "total_requests": sum(p["requests"] for p in phase_summaries),
            "success_count": sum(p["success_count"] for p in phase_summaries),
            "error_count": sum(p["error_count"] for p in phase_summaries),
        }

        await sio.emit(
            "test_completed",
            final_summary,
        )

        print(f"[TEST] Test {test_id} completed")

    except Exception as exc:
        print(f"[ERROR] Test {test_id} failed: {exc}")
        await sio.emit(
            "error",
            {"error": str(exc)},
        )


# -------------------------------------------------
# Local Entry Point (Development Only)
# -------------------------------------------------

if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", 5001))

    uvicorn.run(
        "app:asgi_app",
        host="0.0.0.0",
        port=port,
        ws="websockets",
        log_level="info"
    )
