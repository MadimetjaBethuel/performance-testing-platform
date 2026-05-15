import sys
import unittest
from io import BytesIO
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from engine.taurus_injection import (  # noqa: E402
    TaurusInjectionEngine,
    TaurusInjectionError,
    patch,
)


SAMPLE = ROOT / "data" / "sample_scenario_blazemeter.yaml"


def _load(path: Path) -> bytes:
    return path.read_bytes()


def _parse(yaml_bytes: bytes) -> dict:
    return yaml.safe_load(yaml_bytes)


class LoadAndValidate(unittest.TestCase):
    def test_accepts_blazemeter_export(self):
        TaurusInjectionEngine(_load(SAMPLE))

    def test_rejects_non_taurus_yaml(self):
        with self.assertRaises(TaurusInjectionError):
            TaurusInjectionEngine(b"name: hi\nvalue: 1\n")

    def test_rejects_invalid_yaml(self):
        with self.assertRaises(TaurusInjectionError):
            TaurusInjectionEngine(b": invalid:\n  yaml")

    def test_rejects_non_mapping_root(self):
        with self.assertRaises(TaurusInjectionError):
            TaurusInjectionEngine(b"- one\n- two\n")


class StripSelenium(unittest.TestCase):
    def test_removes_selenium_executor(self):
        engine = TaurusInjectionEngine(_load(SAMPLE))
        removed = engine.strip_selenium()
        self.assertEqual(removed, 1)
        doc = _parse(engine.serialize())
        executors = [e.get("executor") for e in doc["execution"]]
        self.assertEqual(executors, ["jmeter"])

    def test_removes_orphaned_selenium_scenario(self):
        engine = TaurusInjectionEngine(_load(SAMPLE))
        engine.strip_selenium()
        doc = _parse(engine.serialize())
        # Selenium scenario name from fixture
        self.assertNotIn("RECORD 05-13-26 8.24.22 PM-Selenium", doc["scenarios"])
        # JMeter scenario survives
        self.assertIn("RECORD 05-13-26 8.24.22 PM-Http", doc["scenarios"])

    def test_strip_is_idempotent_when_no_selenium(self):
        engine = TaurusInjectionEngine(_load(SAMPLE))
        engine.strip_selenium()
        self.assertEqual(engine.strip_selenium(), 0)


class Parameterize(unittest.TestCase):
    def test_functional_sets_single_iteration(self):
        engine = TaurusInjectionEngine(_load(SAMPLE))
        engine.strip_selenium()
        engine.parameterize("functional")
        jmeter_exe = _parse(engine.serialize())["execution"][0]
        self.assertEqual(jmeter_exe["concurrency"], 1)
        self.assertEqual(jmeter_exe["iterations"], 1)
        self.assertEqual(jmeter_exe["ramp-up"], "0s")
        self.assertEqual(jmeter_exe["hold-for"], "0s")

    def test_load_uses_user_params(self):
        engine = TaurusInjectionEngine(_load(SAMPLE))
        engine.strip_selenium()
        engine.parameterize("load", users=50, rampup=30, duration=120)
        jmeter_exe = _parse(engine.serialize())["execution"][0]
        self.assertEqual(jmeter_exe["concurrency"], 50)
        self.assertEqual(jmeter_exe["ramp-up"], "30s")
        self.assertEqual(jmeter_exe["hold-for"], "120s")
        self.assertNotIn("iterations", jmeter_exe)

    def test_load_overrides_recorded_values(self):
        # The fixture has concurrency=20, ramp-up=1m, hold-for=19m baked in.
        # After parameterize, our values must replace those.
        engine = TaurusInjectionEngine(_load(SAMPLE))
        engine.strip_selenium()
        engine.parameterize("load", users=7, rampup=3, duration=15)
        jmeter_exe = _parse(engine.serialize())["execution"][0]
        self.assertEqual(jmeter_exe["concurrency"], 7)
        self.assertEqual(jmeter_exe["ramp-up"], "3s")
        self.assertEqual(jmeter_exe["hold-for"], "15s")

    def test_parameterize_fails_when_no_jmeter_executor(self):
        # Selenium-only YAML — after stripping, nothing left.
        only_selenium = b"""
execution:
- executor: selenium
  scenario: only-selenium
scenarios:
  only-selenium:
    requests: []
"""
        engine = TaurusInjectionEngine(only_selenium)
        engine.strip_selenium()
        with self.assertRaises(TaurusInjectionError) as ctx:
            engine.parameterize("load")
        self.assertIn("jmeter", str(ctx.exception))

    def test_unknown_mode_raises(self):
        engine = TaurusInjectionEngine(_load(SAMPLE))
        with self.assertRaises(TaurusInjectionError):
            engine.parameterize("turbo")  # type: ignore[arg-type]


class DetectUnsafe(unittest.TestCase):
    def test_clean_returns_empty(self):
        engine = TaurusInjectionEngine(_load(SAMPLE))
        self.assertEqual(engine.detect_unsafe_elements(), [])

    def test_finds_shellexec(self):
        with_shell = b"""
execution:
- executor: jmeter
  scenario: x
services:
- module: shellexec
  prepare:
  - rm -rf /
scenarios:
  x:
    requests: []
"""
        engine = TaurusInjectionEngine(with_shell)
        unsafe = engine.detect_unsafe_elements()
        self.assertIn("services.shellexec", unsafe)

    def test_finds_unsupported_executor(self):
        with_gatling = b"""
execution:
- executor: gatling
  scenario: x
scenarios:
  x:
    requests: []
"""
        engine = TaurusInjectionEngine(with_gatling)
        self.assertEqual(engine.detect_unsupported_executors(), ["gatling"])


class PatchPipeline(unittest.TestCase):
    def test_full_pipeline_on_blazemeter_export(self):
        out = patch(_load(SAMPLE), mode="load", users=10, rampup=5, duration=60)
        doc = _parse(out)
        # Selenium gone, only jmeter left
        executors = [e["executor"] for e in doc["execution"]]
        self.assertEqual(executors, ["jmeter"])
        # Parameterized
        jmeter_exe = doc["execution"][0]
        self.assertEqual(jmeter_exe["concurrency"], 10)
        self.assertEqual(jmeter_exe["ramp-up"], "5s")
        self.assertEqual(jmeter_exe["hold-for"], "60s")
        # Scenarios cleaned up
        self.assertNotIn("RECORD 05-13-26 8.24.22 PM-Selenium", doc["scenarios"])
        self.assertIn("RECORD 05-13-26 8.24.22 PM-Http", doc["scenarios"])

    def test_refuses_shellexec(self):
        bad = b"""
execution:
- executor: jmeter
  scenario: x
services:
- module: shellexec
  prepare: ["id"]
scenarios:
  x:
    requests: []
"""
        with self.assertRaises(TaurusInjectionError) as ctx:
            patch(bad, mode="functional")
        self.assertIn("shellexec", str(ctx.exception))

    def test_refuses_unsupported_executor(self):
        bad = b"""
execution:
- executor: gatling
  scenario: x
scenarios:
  x:
    requests: []
"""
        with self.assertRaises(TaurusInjectionError) as ctx:
            patch(bad, mode="functional")
        self.assertIn("gatling", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
