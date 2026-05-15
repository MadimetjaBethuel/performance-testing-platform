"""JMeter scenario runner.

Drives an already-patched .jmx through the JMeter CLI, tails the JTL file as
it's written, emits live progress events, and returns final metrics on exit.

Lifecycle (the API layer is responsible for tracking it):

    PENDING -> RUNNING -> COMPLETED   (or FAILED)

Events emitted via the on_event callback (always async):

    scenario_started    once, when JMeter is spawned
    scenario_progress   every PROGRESS_INTERVAL_SECONDS while running
    scenario_completed  once, on clean exit (carries final metrics)
    error               on JMeter non-zero exit
"""

from __future__ import annotations

import asyncio
import csv
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from .metrics import calculate_per_label_metrics, summarize_jtl_rows


Mode = Literal["functional", "load"]
EventCallback = Callable[[dict], Awaitable[None]]

PROGRESS_INTERVAL_SECONDS = 2.0
JMETER_BINARY = "jmeter"


class RunFailed(Exception):
    pass


@dataclass
class JtlRow:
    timestamp: int
    elapsed: int
    label: str
    response_code: str
    response_message: str
    thread_name: str
    success: bool
    failure_message: str
    bytes_count: int
    url: str
    latency: int
    connect: int


@dataclass
class LiveAggregator:
    samples: int = 0
    success: int = 0
    errors: int = 0
    sum_latency: int = 0
    started_at: float = field(default_factory=time.monotonic)
    _recent: list[int] = field(default_factory=list)
    _recent_max: int = 1000

    def feed(self, row: JtlRow) -> None:
        self.samples += 1
        if row.success:
            self.success += 1
        else:
            self.errors += 1
        self.sum_latency += row.elapsed
        self._recent.append(row.elapsed)
        if len(self._recent) > self._recent_max:
            self._recent = self._recent[-self._recent_max:]

    def snapshot(self) -> dict:
        elapsed = max(time.monotonic() - self.started_at, 0.001)
        sorted_recent = sorted(self._recent)
        p95 = (
            sorted_recent[min(int(len(sorted_recent) * 0.95), len(sorted_recent) - 1)]
            if sorted_recent else None
        )
        return {
            "samples": self.samples,
            "success": self.success,
            "errors": self.errors,
            "error_rate": (self.errors / self.samples) if self.samples else 0.0,
            "avg_latency_ms": (self.sum_latency / self.samples) if self.samples else None,
            "p95_latency_ms_rolling": p95,
            "throughput_per_sec": self.samples / elapsed,
            "elapsed_seconds": elapsed,
        }


def parse_jtl_row(header: list[str], values: list[str]) -> JtlRow | None:
    """Map a JTL CSV row (header + values) into a JtlRow. Returns None on shape mismatch."""
    if len(values) != len(header):
        return None
    row = dict(zip(header, values))
    try:
        return JtlRow(
            timestamp=int(row.get("timeStamp") or 0),
            elapsed=int(row.get("elapsed") or 0),
            label=row.get("label") or "",
            response_code=row.get("responseCode") or "",
            response_message=row.get("responseMessage") or "",
            thread_name=row.get("threadName") or "",
            success=(row.get("success", "").lower() == "true"),
            failure_message=row.get("failureMessage") or "",
            bytes_count=int(row.get("bytes") or 0),
            url=row.get("URL") or row.get("url") or "",
            latency=int(row.get("Latency") or 0),
            connect=int(row.get("Connect") or 0),
        )
    except (ValueError, TypeError):
        return None


async def _tail_jtl(
    jtl_path: Path,
    aggregator: LiveAggregator,
    rows_out: list[JtlRow],
    stop_event: asyncio.Event,
) -> None:
    header: list[str] | None = None
    buffer = ""

    while not jtl_path.exists():
        if stop_event.is_set():
            return
        await asyncio.sleep(0.2)

    with jtl_path.open("r", newline="") as fp:
        while True:
            chunk = fp.read()
            if chunk:
                buffer += chunk
                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    line = line.rstrip("\r")
                    if not line:
                        continue
                    try:
                        cells = next(csv.reader([line]))
                    except (csv.Error, StopIteration):
                        continue
                    if header is None:
                        header = cells
                        continue
                    row = parse_jtl_row(header, cells)
                    if row is not None:
                        aggregator.feed(row)
                        rows_out.append(row)
            else:
                if stop_event.is_set():
                    break
                await asyncio.sleep(0.1)


async def _emit_progress_loop(
    aggregator: LiveAggregator,
    on_event: EventCallback,
    stop_event: asyncio.Event,
    run_id: str,
) -> None:
    while not stop_event.is_set():
        try:
            await on_event({
                "type": "scenario_progress",
                "run_id": run_id,
                **aggregator.snapshot(),
            })
        except Exception as exc:
            print(f"[jmeter_runner] progress emit failed: {exc}")
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=PROGRESS_INTERVAL_SECONDS)
        except asyncio.TimeoutError:
            pass


async def _noop_emit(_payload: dict) -> None:
    return None


async def run_scenario(
    *,
    run_id: str,
    jmx_path: Path,
    jtl_path: Path,
    log_path: Path,
    mode: Mode,
    users: int = 1,
    rampup: int = 1,
    duration: int = 60,
    on_event: EventCallback | None = None,
) -> dict:
    """Run JMeter on a patched .jmx and produce final metrics.

    The .jmx is expected to already have been patched by InjectionEngine.patch().
    """
    emit = on_event or _noop_emit

    if mode == "functional":
        users = 1
        rampup = 1
        duration = 0

    if jtl_path.exists():
        jtl_path.unlink()

    args = [
        JMETER_BINARY, "-n",
        "-t", str(jmx_path),
        "-l", str(jtl_path),
        "-j", str(log_path),
        f"-Jusers={users}",
        f"-Jrampup={rampup}",
        f"-Jduration={duration}",
    ]

    aggregator = LiveAggregator()
    rows: list[JtlRow] = []
    stop_event = asyncio.Event()

    await emit({
        "type": "scenario_started",
        "run_id": run_id,
        "mode": mode,
        "users": users,
        "rampup": rampup,
        "duration": duration,
    })

    proc = await asyncio.create_subprocess_exec(
        *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    tail_task = asyncio.create_task(_tail_jtl(jtl_path, aggregator, rows, stop_event))
    progress_task = asyncio.create_task(_emit_progress_loop(aggregator, emit, stop_event, run_id))

    _stdout, stderr = await proc.communicate()
    stop_event.set()

    try:
        await asyncio.wait_for(asyncio.gather(tail_task, progress_task), timeout=5)
    except asyncio.TimeoutError:
        pass

    if proc.returncode != 0:
        stderr_tail = (stderr or b"").decode("utf-8", errors="replace")[-2000:]
        await emit({
            "type": "error",
            "run_id": run_id,
            "reason": f"jmeter exited with code {proc.returncode}",
            "stderr_tail": stderr_tail,
        })
        raise RunFailed(f"jmeter failed: rc={proc.returncode}")

    summary = summarize_jtl_rows(rows)
    per_label = calculate_per_label_metrics(rows)
    metrics = {
        "run_id": run_id,
        "mode": mode,
        "summary": summary,
        "per_label_metrics": per_label,
    }
    await emit({
        "type": "scenario_completed",
        "run_id": run_id,
        **metrics,
    })
    return metrics
