import sys
import unittest
from io import BytesIO
from pathlib import Path

from lxml import etree

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from engine.injection import InjectionEngine, InjectionError, patch  # noqa: E402


SAMPLE = ROOT / "data" / "sample_scenario.jmx"
UNSAFE = ROOT / "data" / "sample_scenario_unsafe.jmx"


def _load(path: Path) -> bytes:
    return path.read_bytes()


def _parse(xml_bytes: bytes) -> etree._ElementTree:
    return etree.parse(BytesIO(xml_bytes))


class LoadAndValidate(unittest.TestCase):
    def test_accepts_clean_scenario(self):
        InjectionEngine(_load(SAMPLE))

    def test_rejects_non_jmx_xml(self):
        with self.assertRaises(InjectionError):
            InjectionEngine(b"<?xml version='1.0'?><root/>")

    def test_rejects_invalid_xml(self):
        with self.assertRaises(InjectionError):
            InjectionEngine(b"not xml at all")


class DetectUnsafe(unittest.TestCase):
    def test_clean_returns_empty(self):
        engine = InjectionEngine(_load(SAMPLE))
        self.assertEqual(engine.detect_unsafe_elements(), [])

    def test_unsafe_finds_jsr223(self):
        engine = InjectionEngine(_load(UNSAFE))
        self.assertIn("JSR223Sampler", engine.detect_unsafe_elements())


class ParameterizeThreadGroup(unittest.TestCase):
    def _thread_group(self, tree):
        return tree.findall(".//ThreadGroup")[0]

    def _prop(self, tg, kind, name):
        return tg.find(f"{kind}[@name='{name}']").text

    def test_functional_sets_single_user(self):
        engine = InjectionEngine(_load(SAMPLE))
        engine.parameterize_thread_group("functional")
        tree = _parse(engine.serialize())
        tg = self._thread_group(tree)
        self.assertEqual(self._prop(tg, "stringProp", "ThreadGroup.num_threads"), "1")
        self.assertEqual(self._prop(tg, "stringProp", "ThreadGroup.ramp_time"), "1")
        self.assertEqual(self._prop(tg, "boolProp", "ThreadGroup.scheduler"), "false")

    def test_load_uses_property_placeholders(self):
        engine = InjectionEngine(_load(SAMPLE))
        engine.parameterize_thread_group("load")
        tree = _parse(engine.serialize())
        tg = self._thread_group(tree)
        self.assertEqual(
            self._prop(tg, "stringProp", "ThreadGroup.num_threads"),
            "${__P(users,5)}",
        )
        self.assertEqual(
            self._prop(tg, "stringProp", "ThreadGroup.ramp_time"),
            "${__P(rampup,5)}",
        )
        self.assertEqual(self._prop(tg, "boolProp", "ThreadGroup.scheduler"), "true")
        self.assertEqual(
            self._prop(tg, "stringProp", "ThreadGroup.duration"),
            "${__P(duration,60)}",
        )

    def test_load_sets_loops_forever(self):
        engine = InjectionEngine(_load(SAMPLE))
        engine.parameterize_thread_group("load")
        tree = _parse(engine.serialize())
        tg = self._thread_group(tree)
        ctrl = tg.find("elementProp[@name='ThreadGroup.main_controller']")
        self.assertEqual(ctrl.find("stringProp[@name='LoopController.loops']").text, "-1")
        self.assertEqual(
            ctrl.find("boolProp[@name='LoopController.continue_forever']").text,
            "true",
        )

    def test_unknown_mode_raises(self):
        engine = InjectionEngine(_load(SAMPLE))
        with self.assertRaises(InjectionError):
            engine.parameterize_thread_group("turbo")  # type: ignore[arg-type]


class InjectListener(unittest.TestCase):
    def test_adds_simple_data_writer_with_jtl_path(self):
        engine = InjectionEngine(_load(SAMPLE))
        engine.inject_listener("/tmp/run.jtl")
        tree = _parse(engine.serialize())
        collectors = tree.findall(".//ResultCollector")
        self.assertEqual(len(collectors), 1)
        filename = collectors[0].find("stringProp[@name='filename']").text
        self.assertEqual(filename, "/tmp/run.jtl")

    def test_listener_followed_by_hashtree(self):
        engine = InjectionEngine(_load(SAMPLE))
        engine.inject_listener("/tmp/run.jtl")
        tree = _parse(engine.serialize())
        collector = tree.findall(".//ResultCollector")[0]
        sibling = collector.getnext()
        self.assertIsNotNone(sibling)
        self.assertEqual(sibling.tag, "hashTree")


class InjectAssertion(unittest.TestCase):
    def test_injects_when_absent(self):
        engine = InjectionEngine(_load(SAMPLE))
        engine.inject_default_assertion()
        tree = _parse(engine.serialize())
        self.assertEqual(len(tree.findall(".//ResponseAssertion")), 1)

    def test_skips_when_present(self):
        engine = InjectionEngine(_load(SAMPLE))
        engine.inject_default_assertion()  # first
        engine.inject_default_assertion()  # second call should be a no-op
        tree = _parse(engine.serialize())
        self.assertEqual(len(tree.findall(".//ResponseAssertion")), 1)


class PatchPipeline(unittest.TestCase):
    def test_full_pipeline_produces_valid_jmx(self):
        out = patch(_load(SAMPLE), mode="load", jtl_path="/tmp/run.jtl")
        tree = _parse(out)
        # Thread group parameterized
        tg = tree.findall(".//ThreadGroup")[0]
        self.assertEqual(
            tg.find("stringProp[@name='ThreadGroup.num_threads']").text,
            "${__P(users,5)}",
        )
        # Listener present
        collectors = tree.findall(".//ResultCollector")
        self.assertEqual(len(collectors), 1)
        # Assertion present
        self.assertEqual(len(tree.findall(".//ResponseAssertion")), 1)

    def test_refuses_unsafe_scenario(self):
        with self.assertRaises(InjectionError) as ctx:
            patch(_load(UNSAFE), mode="functional", jtl_path="/tmp/run.jtl")
        self.assertIn("JSR223Sampler", str(ctx.exception))

    def test_can_skip_assertion_injection(self):
        out = patch(
            _load(SAMPLE), mode="functional", jtl_path="/tmp/run.jtl",
            inject_assertion=False,
        )
        tree = _parse(out)
        self.assertEqual(len(tree.findall(".//ResponseAssertion")), 0)


class NoThreadGroup(unittest.TestCase):
    NO_TG_JMX = b"""<?xml version="1.0" encoding="UTF-8"?>
<jmeterTestPlan version="1.2" properties="5.0" jmeter="5.6.3">
  <hashTree>
    <TestPlan guiclass="TestPlanGui" testclass="TestPlan" testname="Empty" enabled="true">
      <stringProp name="TestPlan.comments"></stringProp>
    </TestPlan>
    <hashTree/>
  </hashTree>
</jmeterTestPlan>
"""

    def test_raises_when_no_thread_group(self):
        engine = InjectionEngine(self.NO_TG_JMX)
        with self.assertRaises(InjectionError) as ctx:
            engine.parameterize_thread_group("load")
        self.assertIn("Thread Group", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
