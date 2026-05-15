"""Patches an uploaded Taurus YAML (from BlazeMeter's Chrome extension) so our
runner can drive it.

Operations:
- detect_unsafe_elements()           — find shell-exec services and unsupported executors
- strip_selenium()                   — remove `executor: selenium` blocks (we don't run browsers)
- parameterize(mode, ...)            — set concurrency / ramp-up / hold-for on jmeter executors
- serialize()                        — dump back to YAML bytes

`patch(...)` is the convenience entry point used by the runner. Refuses any YAML
containing shell-exec services or executors we don't whitelist.
"""

from __future__ import annotations

from typing import Literal

import yaml


Mode = Literal["functional", "load"]


class TaurusInjectionError(Exception):
    pass


# Executor types we'll actually run. Taurus supports many (gatling, locust,
# selenium, ab, siege, ...) but our backend container only ships JMeter and
# we explicitly decided against running browsers server-side.
_ALLOWED_EXECUTORS: frozenset[str] = frozenset({"jmeter"})

# Taurus services that can run arbitrary shell commands during the test
# lifecycle. Any of these in an uploaded YAML is a refuse-outright signal.
_DANGEROUS_SERVICE_MODULES: frozenset[str] = frozenset({
    "shellexec",
    "passfail",  # pass/fail criteria can include shell-exec; conservative reject
})


class TaurusInjectionEngine:
    def __init__(self, yaml_bytes: bytes):
        try:
            doc = yaml.safe_load(yaml_bytes)
        except yaml.YAMLError as exc:
            raise TaurusInjectionError(f"Not valid YAML: {exc}") from exc

        if not isinstance(doc, dict):
            raise TaurusInjectionError("YAML root must be a mapping")
        if "execution" not in doc:
            raise TaurusInjectionError(
                "Not a Taurus scenario: missing `execution:` block",
            )
        self._doc = doc

    # ----- detection -----

    def detect_unsafe_elements(self) -> list[str]:
        found: list[str] = []
        services = self._doc.get("services") or []
        if isinstance(services, list):
            for svc in services:
                if isinstance(svc, dict):
                    mod = svc.get("module")
                    if mod in _DANGEROUS_SERVICE_MODULES:
                        found.append(f"services.{mod}")

        # Detect any executor we won't run — flag for transparency, not for
        # outright rejection (selenium gets stripped, not refused).
        return sorted(set(found))

    def detect_unsupported_executors(self) -> list[str]:
        executions = self._doc.get("execution") or []
        if not isinstance(executions, list):
            return []
        bad: list[str] = []
        for exe in executions:
            if not isinstance(exe, dict):
                continue
            kind = exe.get("executor")
            if kind not in _ALLOWED_EXECUTORS and kind != "selenium":
                bad.append(str(kind))
        return sorted(set(bad))

    # ----- transform -----

    def strip_selenium(self) -> int:
        """Remove selenium executor blocks and their orphaned scenarios.
        Returns the count of removed executor blocks."""
        executions = self._doc.get("execution") or []
        if not isinstance(executions, list):
            return 0

        kept: list[dict] = []
        dropped_scenarios: set[str] = set()
        for exe in executions:
            if isinstance(exe, dict) and exe.get("executor") == "selenium":
                scenario = exe.get("scenario")
                if isinstance(scenario, str):
                    dropped_scenarios.add(scenario)
                continue
            kept.append(exe)

        self._doc["execution"] = kept

        # Remove the scenarios that no remaining executor references.
        scenarios = self._doc.get("scenarios")
        if isinstance(scenarios, dict) and dropped_scenarios:
            still_used: set[str] = set()
            for exe in kept:
                if isinstance(exe, dict):
                    s = exe.get("scenario")
                    if isinstance(s, str):
                        still_used.add(s)
            for name in list(dropped_scenarios):
                if name not in still_used and name in scenarios:
                    scenarios.pop(name, None)

        return len(executions) - len(kept)

    def parameterize(
        self,
        mode: Mode,
        *,
        users: int = 5,
        rampup: int = 5,
        duration: int = 60,
    ) -> None:
        """Set concurrency / ramp-up / hold-for on every remaining jmeter executor."""
        executions = self._doc.get("execution") or []
        if not isinstance(executions, list):
            raise TaurusInjectionError("execution block must be a list")

        jmeter_count = 0
        for exe in executions:
            if not isinstance(exe, dict):
                continue
            if exe.get("executor") != "jmeter":
                continue
            jmeter_count += 1
            if mode == "functional":
                exe["concurrency"] = 1
                exe["iterations"] = 1
                exe["ramp-up"] = "0s"
                exe["hold-for"] = "0s"
            elif mode == "load":
                exe["concurrency"] = users
                exe["ramp-up"] = f"{rampup}s"
                exe["hold-for"] = f"{duration}s"
                exe.pop("iterations", None)
            else:
                raise TaurusInjectionError(f"Unknown mode: {mode}")

        if jmeter_count == 0:
            raise TaurusInjectionError(
                "No jmeter executor found after stripping selenium. "
                "Re-record with HTTP capture enabled in the BlazeMeter extension.",
            )

    # ----- serialize -----

    def serialize(self) -> bytes:
        return yaml.safe_dump(self._doc, sort_keys=False).encode("utf-8")


def patch(
    yaml_bytes: bytes,
    *,
    mode: Mode,
    users: int = 5,
    rampup: int = 5,
    duration: int = 60,
) -> bytes:
    """Run the full pipeline. Raises TaurusInjectionError on unsafe content."""
    engine = TaurusInjectionEngine(yaml_bytes)

    unsafe = engine.detect_unsafe_elements()
    if unsafe:
        raise TaurusInjectionError(
            f"Refused: scenario contains shell-execution services: {unsafe}. "
            "These can run arbitrary code on the server and are not allowed.",
        )

    unsupported = engine.detect_unsupported_executors()
    if unsupported:
        raise TaurusInjectionError(
            f"Refused: scenario uses executors we don't support: {unsupported}. "
            "Only `jmeter` is allowed (selenium is stripped automatically).",
        )

    engine.strip_selenium()
    engine.parameterize(mode, users=users, rampup=rampup, duration=duration)
    return engine.serialize()
