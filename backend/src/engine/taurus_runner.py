"""Taurus (bzt) scenario runner — sister to jmeter_runner.

Same lifecycle and event shape as the JMeter runner; the only differences are
the binary we invoke and the JTL output path (Taurus writes `kpi.jtl` inside
its artifacts dir).
"""

from __future__ import annotations

import asyncio
import os
from pathlib import Path
from typing import Literal

from .jmeter_runner import (
    EventCallback,
    JtlRow,
    LiveAggregator,
    RunFailed,
    _emit_progress_loop,
    _noop_emit,
    _tail_jtl,
)
from .metrics import calculate_per_label_metrics, summarize_jtl_rows


Mode = Literal["functional", "load"]

BZT_BINARY = "bzt"
# Taurus sometimes nests results under a timestamped subdir. We poll for any
# kpi.jtl beneath the artifacts dir rather than hard-coding the path.
KPI_JTL_NAME = "kpi.jtl"

# Force Taurus to reuse the JMeter we installed in the Dockerfile instead of
# downloading its own (pinned to 5.5) on every cold start. Without this Taurus
# fetches ~90 MB and frequently stalls before the test ever runs.
JMETER_PATH = os.environ.get(
    "JMETER_PATH",
    "/opt/apache-jmeter-5.6.3/bin/jmeter",
)
JMETER_VERSION = os.environ.get("JMETER_VERSION", "5.6.3")


async def _find_kpi_jtl(
    artifacts_dir: Path,
    stop_event: asyncio.Event,
) -> Path | None:
    """Wait for Taurus to create a kpi.jtl somewhere under artifacts_dir."""
    while not stop_event.is_set():
        matches = list(artifacts_dir.rglob(KPI_JTL_NAME))
        if matches:
            return matches[0]
        await asyncio.sleep(0.5)
    return None


async def _tail_when_found(
    artifacts_dir: Path,
    aggregator: LiveAggregator,
    rows_out: list[JtlRow],
    stop_event: asyncio.Event,
) -> None:
    jtl_path = await _find_kpi_jtl(artifacts_dir, stop_event)
    if jtl_path is None:
        return
    await _tail_jtl(jtl_path, aggregator, rows_out, stop_event)


async def run_taurus_scenario(
    *,
    run_id: str,
    yaml_path: Path,
    artifacts_dir: Path,
    mode: Mode,
    on_event: EventCallback | None = None,
) -> dict:
    """Run a patched Taurus YAML and produce final metrics.

    The YAML is expected to already have been patched by
    taurus_injection.patch() (selenium stripped, jmeter executor
    parameterized). We do NOT pass -o overrides for concurrency / ramp /
    duration here because the patched YAML already encodes them.
    """
    emit = on_event or _noop_emit
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    args = [
        BZT_BINARY,
        str(yaml_path),
        "-o", f"settings.artifacts-dir={artifacts_dir}",
        # Pin to our pre-installed JMeter. Without these overrides Taurus
        # downloads its own pinned 5.5 release on every cold start.
        "-o", f"modules.jmeter.path={JMETER_PATH}",
        "-o", f"modules.jmeter.version={JMETER_VERSION}",
        "-o", "modules.jmeter.detect-plugins=false",
        "-q",
    ]

    aggregator = LiveAggregator()
    rows: list[JtlRow] = []
    stop_event = asyncio.Event()

    await emit({
        "type": "scenario_started",
        "run_id": run_id,
        "mode": mode,
        "engine": "taurus",
    })

    proc = await asyncio.create_subprocess_exec(
        *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    # Taurus picks its own kpi.jtl location under artifacts_dir, so we tail
    # whatever it creates rather than hardcoding a path.
    tail_task = asyncio.create_task(
        _tail_when_found(artifacts_dir, aggregator, rows, stop_event)
    )
    progress_task = asyncio.create_task(
        _emit_progress_loop(aggregator, emit, stop_event, run_id)
    )

    _stdout, stderr = await proc.communicate()
    stop_event.set()

    try:
        await asyncio.wait_for(
            asyncio.gather(tail_task, progress_task),
            timeout=5,
        )
    except asyncio.TimeoutError:
        pass

    if proc.returncode != 0:
        stderr_tail = (stderr or b"").decode("utf-8", errors="replace")[-2000:]
        await emit({
            "type": "error",
            "run_id": run_id,
            "reason": f"bzt exited with code {proc.returncode}",
            "stderr_tail": stderr_tail,
        })
        raise RunFailed(f"bzt failed: rc={proc.returncode}")

    summary = summarize_jtl_rows(rows)
    per_label = calculate_per_label_metrics(rows)
    metrics = {
        "run_id": run_id,
        "mode": mode,
        "engine": "taurus",
        "summary": summary,
        "per_label_metrics": per_label,
    }
    await emit({
        "type": "scenario_completed",
        "run_id": run_id,
        **metrics,
    })
    return metrics
