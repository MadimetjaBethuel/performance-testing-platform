# Scenario Testing Plan — JMeter Injection Engine

Living document. Update as decisions are made and work lands.

## Goal

Let users record a real user flow once (via an existing tool — JMeter recorder or BlazeMeter Chrome extension), upload the resulting `.jmx`, and have our platform run it as either:

- **Functional test** — single virtual user, assertions enforced, pass/fail per step.
- **Load test** — N virtual users, configurable ramp/duration, assertions tracked as error rate.

Same uploaded file, same engine, mode selected at run time.

**Results and progress live in the frontend, not in email.** The user kicks off a run from the UI, sees live progress (samples completed, current error rate, current throughput) while it runs, and sees a full result view (pass/fail per step, latency percentiles, assertion failures, response-time graph) when it finishes. No email for this flow.

## Non-goals

- Building our own recorder. Use what exists (JMeter HTTP(S) Test Script Recorder, BlazeMeter extension).
- Selenium / Playwright / browser-driven functional tests. JMeter assertions cover correctness for v1.
- Replacing the existing CSV URL ramp test — it stays as a separate test type for now.
- **Email reporting for scenario runs.** Results are surfaced in the frontend. The existing CSV URL flow can keep its email path; scenarios do not get one.

## Architecture

```
HTTP POST /scenario/upload ──► .jmx stored ──► returns file_id
                                                    │
client emits  start_scenario  ───────────────────► server
   (file_id, mode, users, rampup, duration)              │
                                                         ▼
                                              InjectionEngine
                                              (parameterize / listener / assertion / sanitize)
                                                         │
                                                         ▼
                                                  jmeter CLI
                                                         │
                                                         ▼
                                              .jtl (streaming)
                                                         │
                                   ┌─────────────────────┴─────────────────────┐
                                   ▼                                           ▼
                       live tail (Socket.IO emits)                    final parse
                       scenario_progress events                       scenario_completed event
                                   │                                           │
                                   └───────────► frontend ◄────────────────────┘
                                                  (live view → results view)
```

The project already uses Socket.IO over WebSockets (see [backend/src/app.py](backend/src/app.py)) for its existing URL-ramp flow. We follow the same pattern: file upload via plain HTTP POST (Socket.IO is awkward for large binary payloads), then a `start_scenario` event triggers the run. The server emits `scenario_started`, `scenario_progress` (periodic, tailed from JTL), `scenario_completed`, and `error` events back to the client.

### New modules

- [backend/src/engine/injection.py](backend/src/engine/injection.py) — the `InjectionEngine` (`lxml`).
- [backend/src/engine/jmeter_runner.py](backend/src/engine/jmeter_runner.py) — orchestrates inject → exec → parse.

### Touched modules

- [backend/src/engine/metrics.py](backend/src/engine/metrics.py) — extend to compute final scenario metrics from JTL rows (per-step latency p50/p95/p99, error rate, assertion failures).
- [backend/src/app.py](backend/src/app.py) — extend the existing Flask + Socket.IO app:
  - HTTP `POST /scenario/upload` — accept `.jmx` file, sanitize+validate, store, return `file_id`.
  - Socket.IO event `start_scenario` — `{file_id, mode, users, rampup, duration, test_id, user_id}` kicks off the run.
  - Socket.IO emits: `scenario_started`, `scenario_progress` (periodic, JTL tail), `scenario_completed`, `error`.
- [backend/Dockerfile](backend/Dockerfile) — install JMeter + JRE (~200MB).

### Frontend

- New scenario test type alongside the existing CSV URL flow in [loadforge/](loadforge/).
- Upload widget for `.jmx`, mode toggle (functional / load), load-param inputs.
- Live run view consuming the SSE stream: samples completed, current error rate, throughput, rolling response time.
- Results view: pass/fail summary, per-step latency table, assertion failures, response-time graph (reuse the existing graph component if there is one).

## Decisions made

- **Use JMeter `.jmx` as the canonical scenario format.** No custom recorder, no custom replay engine.
- **Auto-patch uploaded `.jmx` files** (we will not require users to author placeholders). XML rewrite via `lxml`.
- **Sanitize uploads.** Strip / reject `JSR223Sampler`, `BeanShellSampler`, `OS Process Sampler`. Non-negotiable since uploads execute code on our backend.
- **Functional and load run the same `.jmx`** via mode switching in the InjectionEngine.

## Open decisions

- **Default assertion injection:** RESOLVED — always inject when no assertion exists in the recorded `.jmx`. Implemented as the default in `patch_jmx()`. User-recorded assertions are preserved.
- **Coexistence with CSV URL ramp test:** keep both indefinitely, or deprecate the CSV flow once `.jmx` mode covers it. — UNRESOLVED (does not block M5/M6).
- **Recorder we recommend to users in docs:** BlazeMeter Chrome extension (lower friction, may now require free account) vs. JMeter's native recorder (no signup, proxy setup). Document both, default-recommend one. — UNRESOLVED (blocks M6 only).

## Known risks / gotchas

- `.jmx` structure varies across recorder dialects (BlazeMeter vs JMeter-native vs Taurus). Injection engine must be defensive and fail loudly with a useful error rather than silently mangle.
- JMeter on JVM adds ~200MB to the Docker image.
- Security: arbitrary `.jmx` can execute shell on the host via script samplers. Sanitization is load-bearing.

## Milestones

### M0 — Foundation
- [x] Install JMeter in [backend/Dockerfile](backend/Dockerfile) (pinned 5.6.3, JRE installed).
- [ ] Verify `jmeter -v` actually runs in the container (Docker build was kicked off; user said we'll test later).
- [x] Add a sample `.jmx` to [backend/data/sample_scenario.jmx](backend/data/sample_scenario.jmx).
- [x] Add an unsafe-fixture `.jmx` ([backend/data/sample_scenario_unsafe.jmx](backend/data/sample_scenario_unsafe.jmx)) with a `JSR223Sampler`, to exercise the sanitizer.

### M1 — Injection engine (core)
- [x] [backend/src/engine/injection.py](backend/src/engine/injection.py) — parse `.jmx` with `lxml`.
- [x] Parameterize Thread Group differently per mode: functional sets `num_threads=1, scheduler=false, loops=1`; load uses `${__P(users,5)}`, `${__P(rampup,5)}`, `${__P(duration,60)}`, `scheduler=true`, `loops=-1`.
- [x] Inject Simple Data Writer at TestPlan scope, pointed at a known output path.
- [x] `detect_unsafe_elements()` flags JSR223, BeanShell, OS Process samplers; the `patch()` convenience refuses any scenario containing them.
- [x] Fail-loud error when no Thread Group is found.
- [x] Unit tests in [backend/tests/test_injection.py](backend/tests/test_injection.py) — 17/17 passing.

### M2 — Runner + metrics
- [x] [backend/src/engine/jmeter_runner.py](backend/src/engine/jmeter_runner.py) — async `run_scenario()` shells out via `asyncio.create_subprocess_exec`, passes `-Jusers/-Jrampup/-Jduration`, runs concurrent JTL tailer + progress emitter.
- [x] `LiveAggregator` aggregates running counters (samples, errors, error rate, avg latency, rolling p95, throughput).
- [x] [backend/src/engine/metrics.py](backend/src/engine/metrics.py) extended: `summarize_jtl_rows()` + `calculate_per_label_metrics()` produce final scenario metrics (per-label latency p50/p90/p95/p99, error rate, error buckets).
- [x] Unit tests in [backend/tests/test_jmeter_runner.py](backend/tests/test_jmeter_runner.py) — 11/11 passing (parser, aggregator, summary, per-label).

### M3 — API + modes + live progress
- [x] `POST /scenario/upload` (HTTP, [backend/src/app.py](backend/src/app.py)) accepts a `.jmx`, validates parse + sanitize, stores under `backend/data/scenarios/uploads/<file_id>.jmx`, returns `{file_id, filename, size_bytes}`. 5MB cap. Path-traversal-safe resolution via UUID regex.
- [x] Socket.IO `start_scenario` event: `{file_id, mode, users, rampup, duration, test_id, user_id}` → patches the .jmx via the InjectionEngine, kicks off `run_scenario` in an `asyncio.create_task` (matches the existing `start_test` pattern).
- [x] Server emits `scenario_started`, `scenario_progress` (every 2s while running), `scenario_completed`, `error` — all targeted to the originating `sid`.
- [x] Functional mode forces `users=1, rampup=1, duration=0`; the engine's functional patch turns scheduler off so duration is ignored anyway.
- [x] Load mode honors user-supplied params; the engine's load patch sets the ThreadGroup to read them via `__P()`.

### M4 — Assertion injection
- [x] `inject_default_assertion()` adds a global `^[23]\d\d$` Response Assertion when none exists.
- [x] Preserves user-recorded assertions (skips when a `ResponseAssertion` is already present).
- [x] **Policy:** the wired-up flow in `app.py` calls `patch_jmx(..., inject_assertion=True)` — i.e., **always inject when absent**. Matches the recommended default. Can be flipped per-run later by threading a flag through the Socket.IO payload if needed.

### M5 — Frontend
- [x] Drizzle schema extended ([loadforge/src/server/db/schema.ts](loadforge/src/server/db/schema.ts)): `type`, `mode`, `users`, `jmx_filename`, `file_id`, `scenario_metrics`. Migrations 0002 + 0003. URL-flow columns relaxed to nullable for scenarios.
- [x] tRPC: `startScenario` mutation, `getRunningScenarios` query, `getScenarioMetrics` query in [loadforge/src/server/api/routers/test.events.ts](loadforge/src/server/api/routers/test.events.ts).
- [x] [loadforge/src/app/api/scenario/upload/route.ts](loadforge/src/app/api/scenario/upload/route.ts) — auth-checked Next.js API route that proxies multipart to Python `POST /scenario/upload`.
- [x] Socket.IO bridge ([loadforge/src/server/socket/events.bind.ts](loadforge/src/server/socket/events.bind.ts)) relays `scenario_started` / `scenario_progress` / `scenario_completed` into the eventbus.
- [x] [loadforge/src/server/socket/scenario.complete.ts](loadforge/src/server/socket/scenario.complete.ts) persists final metrics to `completeTests.scenario_metrics` on completion; marks status `failed` on error events carrying a `run_id`.
- [x] [loadforge/src/hooks/useLiveScenarioTracking.ts](loadforge/src/hooks/useLiveScenarioTracking.ts) — live hook with DB bootstrap of running scenarios so refresh doesn't lose them.
- [x] [loadforge/src/components/scenario-configuration.tsx](loadforge/src/components/scenario-configuration.tsx) — upload + mode toggle + load params, sanitization rejections surfaced inline.
- [x] [loadforge/src/components/scenario-live-tracking.tsx](loadforge/src/components/scenario-live-tracking.tsx) — live counters (samples, error rate, throughput, rolling p95, avg, success/errors, elapsed) and a final per-step table on completion.
- [x] [loadforge/src/components/scenario-results-view.tsx](loadforge/src/components/scenario-results-view.tsx) + [loadforge/src/app/results/scenario/[testId]/page.tsx](loadforge/src/app/results/scenario/[testId]/page.tsx) — permanent results page that reads from DB.
- [x] Pages `/test/scenario` and `/live/scenario`; nav links added in [loadforge/src/components/dashboard-nav.tsx](loadforge/src/components/dashboard-nav.tsx).
- [x] `pnpm exec tsc --noEmit` clean.

### M6 — Docs
- [ ] How to record with BlazeMeter extension (link + screenshots).
- [ ] How to record with JMeter native recorder (proxy + cert).
- [ ] What gets sanitized and why.

## Changelog

- 2026-05-13 — Plan created. Architecture and milestones drafted. Three decisions outstanding.
- 2026-05-13 — Frontend put on the critical path: results and live progress surface in the UI via SSE. Email reporting explicitly removed from this flow.
- 2026-05-13 — Realigned with existing codebase: switched live channel from SSE to Socket.IO (project already runs Flask + Socket.IO over WebSockets in [backend/src/app.py](backend/src/app.py)). File upload remains plain HTTP `POST /scenario/upload`; run kicked off by `start_scenario` Socket.IO event matching the existing `start_test` pattern.
- 2026-05-13 — M0–M4 backend landed. 28/28 unit tests passing (engine + runner). End-to-end Docker run deferred per user ("we will test later"). Default assertion injection resolved as always-on. Next: M5 frontend.
- 2026-05-13 — M5 frontend complete. Drizzle schema + 2 migrations, tRPC mutation/queries, Next.js upload proxy, Socket.IO bridge + DB persistence handler, live hook with DB bootstrap, three new components, three new pages. `tsc --noEmit` clean. Last open milestone is M6 (docs).
