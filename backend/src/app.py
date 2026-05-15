import os
import re
import uuid
import asyncio
import socketio

from pathlib import Path

from flask import Flask, jsonify, request
from asgiref.wsgi import WsgiToAsgi

from engine.core import run_performance_test
from engine.injection import InjectionEngine, InjectionError, patch as patch_jmx
from engine.jmeter_runner import RunFailed, run_scenario
from engine.taurus_injection import (
    TaurusInjectionEngine,
    TaurusInjectionError,
    patch as patch_taurus,
)
from engine.taurus_runner import run_taurus_scenario
from url_loader import validate_urls, load_urls_from_json
from config import CONCURRENCY_STEPS, PHASE_LENGTH, REQUEST_TIMEOUT


# -------------------------------------------------
# Scenario storage layout
# -------------------------------------------------

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
SCENARIO_UPLOAD_DIR = DATA_DIR / "scenarios" / "uploads"
SCENARIO_RUNS_DIR = DATA_DIR / "scenarios" / "runs"
SCENARIO_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
SCENARIO_RUNS_DIR.mkdir(parents=True, exist_ok=True)

MAX_JMX_BYTES = 5 * 1024 * 1024  # 5 MB cap on uploaded scenario files
_UUID_RE = re.compile(r"^[0-9a-fA-F-]{36}$")
_JMX_EXTS = (".jmx",)
_YAML_EXTS = (".yaml", ".yml")
_ALLOWED_EXTS = _JMX_EXTS + _YAML_EXTS


def _classify_scenario(filename: str) -> str | None:
    """Return 'jmx' or 'yaml' for accepted extensions, None for everything else."""
    lower = filename.lower()
    if lower.endswith(_JMX_EXTS):
        return "jmx"
    if lower.endswith(_YAML_EXTS):
        return "yaml"
    return None

# -------------------------------------------------
# Flask (HTTP / Health / Metadata)
# -------------------------------------------------

flask_app = Flask(__name__)
flask_app.config["MAX_CONTENT_LENGTH"] = MAX_JMX_BYTES


@flask_app.route("/health", methods=["GET"])
def health_check():
    return jsonify({"status": "healthy"}), 200


@flask_app.route("/", methods=["GET"])
def root():
    return jsonify({
        "status": "running",
        "service": "performance-test-api"
    }), 200


@flask_app.route("/scenario/upload", methods=["POST"])
def scenario_upload():
    """Accept a .jmx (JMeter) or .yaml/.yml (Taurus / BlazeMeter) scenario file.
    Validate parse + sanitize, store, and return a file_id the client passes
    to `start_scenario`."""
    if "file" not in request.files:
        return jsonify({"error": "no file field"}), 400

    upload = request.files["file"]
    if not upload.filename:
        return jsonify({"error": "missing filename"}), 400

    kind = _classify_scenario(upload.filename)
    if kind is None:
        return jsonify({
            "error": f"expected one of {_ALLOWED_EXTS}; got {upload.filename}",
        }), 400

    payload = upload.read()
    if len(payload) == 0:
        return jsonify({"error": "empty file"}), 400

    # Validate + sanitize per-type. We return 400 with a concrete reason
    # so the frontend can surface it to the user.
    if kind == "jmx":
        try:
            jmx_engine = InjectionEngine(payload)
        except InjectionError as exc:
            return jsonify({"error": f"invalid .jmx: {exc}"}), 400
        unsafe = jmx_engine.detect_unsafe_elements()
        if unsafe:
            return jsonify({
                "error": "scenario contains script-execution elements",
                "elements": unsafe,
            }), 400
    else:  # kind == "yaml"
        try:
            yaml_engine = TaurusInjectionEngine(payload)
        except TaurusInjectionError as exc:
            return jsonify({"error": f"invalid Taurus YAML: {exc}"}), 400
        unsafe = yaml_engine.detect_unsafe_elements()
        if unsafe:
            return jsonify({
                "error": "scenario contains shell-execution services",
                "elements": unsafe,
            }), 400
        unsupported = yaml_engine.detect_unsupported_executors()
        if unsupported:
            return jsonify({
                "error": f"unsupported executors: {unsupported}. Only `jmeter` is allowed (selenium is stripped automatically).",
            }), 400

    file_id = str(uuid.uuid4())
    ext = ".jmx" if kind == "jmx" else ".yaml"
    stored = SCENARIO_UPLOAD_DIR / f"{file_id}{ext}"
    stored.write_bytes(payload)

    return jsonify({
        "file_id": file_id,
        "filename": upload.filename,
        "kind": kind,
        "size_bytes": len(payload),
    }), 201


def _resolve_uploaded_scenario(file_id: str) -> tuple[Path, str] | None:
    """Return (path, kind) for an uploaded scenario file, or None if not found
    or if the id fails validation. Protects against path traversal."""
    if not _UUID_RE.match(file_id):
        return None
    upload_root = SCENARIO_UPLOAD_DIR.resolve()
    for ext, kind in ((".jmx", "jmx"), (".yaml", "yaml"), (".yml", "yaml")):
        candidate = (SCENARIO_UPLOAD_DIR / f"{file_id}{ext}").resolve()
        if not str(candidate).startswith(str(upload_root)):
            continue
        if candidate.exists():
            return candidate, kind
    return None


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
        user_id = data.get("user_id", "unknown_user")
        if not test_id or not user_id:
            await sio.emit(
                "error",
                {"error": "test_id and user_id are required"},
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
                request_timeout=request_timeout,
                user_id=user_id
            )
        )

        await sio.emit(
            "test_started",
            {"message": "Test started", "test_id": test_id},
        )

        print(
            f"[TEST] Started test {test_id} for client {sid} and user {user_id}")

    except Exception as exc:
        print(f"[ERROR] start_test failed: {exc}")
        await sio.emit(
            "error",
            {"error": str(exc)},
        )


# -------------------------------------------------
# Scenario flow (.jmx via JMeter / .yaml via Taurus)
# -------------------------------------------------


@sio.event
async def start_scenario(sid, data):
    """Run an uploaded scenario (.jmx or .yaml) and stream progress back to the client.

    Expected payload:
      {
        "file_id":  "<uuid returned by POST /scenario/upload>",
        "mode":     "functional" | "load",
        "users":    int,   # ignored in functional mode
        "rampup":   int,   # ignored in functional mode
        "duration": int,   # ignored in functional mode
        "test_id":  "<client-supplied id; reused as run_id>",
        "user_id":  "<...>"
      }

    The file kind (jmx vs yaml) is determined server-side from the stored
    upload's extension — the client doesn't need to tell us.

    Emits:
      scenario_started, scenario_progress (periodic), scenario_completed,
      or error.
    """
    try:
        file_id = (data or {}).get("file_id")
        mode = (data or {}).get("mode", "functional")
        test_id = (data or {}).get("test_id") or str(uuid.uuid4())
        user_id = (data or {}).get("user_id", "unknown_user")
        users = int((data or {}).get("users", 5))
        rampup = int((data or {}).get("rampup", 5))
        duration = int((data or {}).get("duration", 60))

        if mode not in ("functional", "load"):
            await sio.emit("error", {"error": f"unknown mode: {mode}"}, to=sid)
            return

        if not file_id:
            await sio.emit("error", {"error": "file_id is required"}, to=sid)
            return

        resolved = _resolve_uploaded_scenario(file_id)
        if resolved is None:
            await sio.emit(
                "error",
                {"error": "uploaded scenario not found", "file_id": file_id},
                to=sid,
            )
            return
        source, kind = resolved

        run_dir = SCENARIO_RUNS_DIR / test_id
        run_dir.mkdir(parents=True, exist_ok=True)

        async def emit_to_client(payload: dict) -> None:
            event_name = payload.pop("type", "scenario_event")
            await sio.emit(event_name, payload, to=sid)

        if kind == "jmx":
            patched_path = run_dir / "patched.jmx"
            jtl_path = run_dir / "result.jtl"
            log_path = run_dir / "jmeter.log"
            try:
                patched_bytes = patch_jmx(
                    source.read_bytes(),
                    mode=mode,
                    jtl_path=str(jtl_path),
                )
            except InjectionError as exc:
                await sio.emit("error", {"error": str(exc)}, to=sid)
                return
            patched_path.write_bytes(patched_bytes)

            asyncio.create_task(_run_jmx_in_background(
                sid=sid,
                run_id=test_id,
                user_id=user_id,
                jmx_path=patched_path,
                jtl_path=jtl_path,
                log_path=log_path,
                mode=mode,
                users=users,
                rampup=rampup,
                duration=duration,
                emit=emit_to_client,
            ))
        else:  # kind == "yaml"
            patched_path = run_dir / "patched.yaml"
            artifacts_dir = run_dir / "bzt"
            try:
                patched_bytes = patch_taurus(
                    source.read_bytes(),
                    mode=mode,
                    users=users,
                    rampup=rampup,
                    duration=duration,
                )
            except TaurusInjectionError as exc:
                await sio.emit("error", {"error": str(exc)}, to=sid)
                return
            patched_path.write_bytes(patched_bytes)

            asyncio.create_task(_run_taurus_in_background(
                sid=sid,
                run_id=test_id,
                user_id=user_id,
                yaml_path=patched_path,
                artifacts_dir=artifacts_dir,
                mode=mode,
                emit=emit_to_client,
            ))

        print(f"[SCENARIO] Started {test_id} for client {sid} (kind={kind}, mode={mode})")

    except Exception as exc:
        print(f"[ERROR] start_scenario failed: {exc}")
        await sio.emit("error", {"error": str(exc)}, to=sid)


async def _run_jmx_in_background(
    *,
    sid,
    run_id,
    user_id,
    jmx_path,
    jtl_path,
    log_path,
    mode,
    users,
    rampup,
    duration,
    emit,
):
    try:
        await run_scenario(
            run_id=run_id,
            jmx_path=jmx_path,
            jtl_path=jtl_path,
            log_path=log_path,
            mode=mode,
            users=users,
            rampup=rampup,
            duration=duration,
            on_event=emit,
        )
        print(f"[SCENARIO] {run_id} (jmx) completed for user {user_id}")
    except RunFailed as exc:
        print(f"[SCENARIO] {run_id} (jmx) failed: {exc}")
    except Exception as exc:
        print(f"[ERROR] scenario {run_id} (jmx) crashed: {exc}")
        await sio.emit("error", {"error": str(exc), "run_id": run_id}, to=sid)


async def _run_taurus_in_background(
    *,
    sid,
    run_id,
    user_id,
    yaml_path,
    artifacts_dir,
    mode,
    emit,
):
    try:
        await run_taurus_scenario(
            run_id=run_id,
            yaml_path=yaml_path,
            artifacts_dir=artifacts_dir,
            mode=mode,
            on_event=emit,
        )
        print(f"[SCENARIO] {run_id} (yaml) completed for user {user_id}")
    except RunFailed as exc:
        print(f"[SCENARIO] {run_id} (yaml) failed: {exc}")
    except Exception as exc:
        print(f"[ERROR] scenario {run_id} (yaml) crashed: {exc}")
        await sio.emit("error", {"error": str(exc), "run_id": run_id}, to=sid)


# -------------------------------------------------
# Background Test Runner
# -------------------------------------------------

async def run_test_in_background(
    sid,
    test_id,
    user_id,
    urls,
    concurrency_steps,
    phase_length,
    request_timeout
):
    try:
        total_phases = len(concurrency_steps)
        phase_summaries = []
        all_url_metrics = {}  # Aggregate URL metrics across all phases

        print(f"[TEST] Running test {test_id} for user {user_id}")

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
                "user_id": user_id,
                "total_phases": total_phases,
                "concurrency": concurrency,
                "requests": requests_count,
                "success_count": summary.get("success_count", 0),
                "error_count": summary.get("error_count", 0),
                "percentiles": summary.get("percentiles", {}),
            }

            phase_summaries.append(phase_summary)

            # Aggregate per_url_metrics across phases
            per_url = summary.get("per_url_metrics", {})
            for url, metrics in per_url.items():
                if url not in all_url_metrics:
                    all_url_metrics[url] = {
                        "total_requests": 0,
                        "successful_requests": 0,
                        "total_time": 0,
                        "success_rate_sum": 0,
                        "phase_count": 0,
                        "errors": {},
                    }
                all_url_metrics[url]["total_requests"] += metrics.get(
                    "total_requests", 0)
                all_url_metrics[url]["successful_requests"] += metrics.get(
                    "successful_requests", 0)
                if metrics.get("average_time"):
                    all_url_metrics[url]["total_time"] += metrics["average_time"] * \
                        metrics.get("successful_requests", 0)
                all_url_metrics[url]["success_rate_sum"] += metrics.get(
                    "success_rate", 0)
                all_url_metrics[url]["phase_count"] += 1

                for err in metrics.get("errors", []):
                    key = (err.get("status_code", "error"),
                           err.get("error") or "Unknown error")
                    all_url_metrics[url]["errors"][key] = (
                        all_url_metrics[url]["errors"].get(key, 0)
                        + err.get("count", 0)
                    )

            await sio.emit(
                "phase_complete",
                phase_summary,
            )

            print(f"[TEST] Phase {index}/{total_phases} complete")

        # Calculate aggregated URL metrics
        per_url_metrics = {}
        for url, aggregated in all_url_metrics.items():
            total_requests = aggregated["total_requests"]
            successful_requests = aggregated["successful_requests"]
            avg_time = aggregated["total_time"] / \
                successful_requests if successful_requests > 0 else 0
            success_rate = (successful_requests /
                            total_requests * 100) if total_requests > 0 else 0

            errors = [
                {"status_code": code, "error": msg, "count": count}
                for (code, msg), count in aggregated["errors"].items()
            ]

            per_url_metrics[url] = {
                "total_requests": total_requests,
                "successful_requests": successful_requests,
                "average_time": avg_time,
                "success_rate": success_rate,
                "errors": errors,
            }

        final_summary = {
            "test_id": test_id,
            "user_id": user_id,
            "phase_summaries": phase_summaries,
            "total_requests": sum(p["requests"] for p in phase_summaries),
            "success_count": sum(p["success_count"] for p in phase_summaries),
            "error_count": sum(p["error_count"] for p in phase_summaries),
            "per_url_metrics": per_url_metrics,
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
