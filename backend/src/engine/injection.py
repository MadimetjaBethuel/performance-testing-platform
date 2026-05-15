"""InjectionEngine — patches an uploaded JMeter .jmx so our runner can drive it.

Operations:

- detect_unsafe_elements()              find JSR223 / BeanShell / OS Process samplers
- parameterize_thread_group(mode)       rewrite ThreadGroup for functional or load mode
- inject_listener(jtl_path)             add a Simple Data Writer at TestPlan scope
- inject_default_assertion()            add a global 2xx/3xx Response Assertion if none exists

`patch(...)` is the convenience entry point used by the runner. It refuses any .jmx
containing script-execution elements — those would run arbitrary code on our host.
"""

from __future__ import annotations

from io import BytesIO
from typing import Literal

from lxml import etree


Mode = Literal["functional", "load"]


class InjectionError(Exception):
    pass


# JMeter elements that execute arbitrary user-supplied code on the host. Any
# uploaded .jmx containing one of these is refused outright.
_DANGEROUS_TAGS: frozenset[str] = frozenset({
    "JSR223Sampler",
    "JSR223PreProcessor",
    "JSR223PostProcessor",
    "JSR223Listener",
    "JSR223Assertion",
    "JSR223Timer",
    "BeanShellSampler",
    "BeanShellPreProcessor",
    "BeanShellPostProcessor",
    "BeanShellListener",
    "BeanShellAssertion",
    "BeanShellTimer",
    "SystemSampler",
})

# Element tags we recognize as a Thread Group. Standard recorders emit
# ThreadGroup; some setups use Setup/Post variants; BlazeMeter plugin users
# may use ConcurrencyThreadGroup but that's out of scope for v1.
_THREAD_GROUP_TAGS: tuple[str, ...] = (
    "ThreadGroup",
    "SetupThreadGroup",
    "PostThreadGroup",
)


_SIMPLE_DATA_WRITER_XML = """\
<ResultCollector guiclass="SimpleDataWriter" testclass="ResultCollector" testname="Injected Data Writer" enabled="true">
  <boolProp name="ResultCollector.error_logging">false</boolProp>
  <objProp>
    <name>saveConfig</name>
    <value class="SampleSaveConfiguration">
      <time>true</time>
      <latency>true</latency>
      <timestamp>true</timestamp>
      <success>true</success>
      <label>true</label>
      <code>true</code>
      <message>true</message>
      <threadName>true</threadName>
      <dataType>true</dataType>
      <encoding>false</encoding>
      <assertions>true</assertions>
      <subresults>true</subresults>
      <responseData>false</responseData>
      <samplerData>false</samplerData>
      <xml>false</xml>
      <fieldNames>true</fieldNames>
      <responseHeaders>false</responseHeaders>
      <requestHeaders>false</requestHeaders>
      <responseDataOnError>false</responseDataOnError>
      <saveAssertionResultsFailureMessage>true</saveAssertionResultsFailureMessage>
      <assertionsResultsToSave>0</assertionsResultsToSave>
      <bytes>true</bytes>
      <sentBytes>true</sentBytes>
      <url>true</url>
      <threadCounts>true</threadCounts>
      <idleTime>true</idleTime>
      <connectTime>true</connectTime>
    </value>
  </objProp>
  <stringProp name="filename"></stringProp>
</ResultCollector>
"""


_DEFAULT_ASSERTION_XML = """\
<ResponseAssertion guiclass="AssertionGui" testclass="ResponseAssertion" testname="Injected 2xx/3xx Assertion" enabled="true">
  <collectionProp name="Asserion.test_strings">
    <stringProp name="default2xx3xx">^[23]\\d\\d$</stringProp>
  </collectionProp>
  <stringProp name="Assertion.custom_message">Response code is not 2xx/3xx</stringProp>
  <stringProp name="Assertion.test_field">Assertion.response_code</stringProp>
  <boolProp name="Assertion.assume_success">false</boolProp>
  <intProp name="Assertion.test_type">1</intProp>
</ResponseAssertion>
"""


class InjectionEngine:
    def __init__(self, jmx_bytes: bytes):
        try:
            self._tree = etree.parse(BytesIO(jmx_bytes))
        except etree.XMLSyntaxError as exc:
            raise InjectionError(f"Not valid XML: {exc}") from exc

        root = self._tree.getroot()
        if root.tag != "jmeterTestPlan":
            raise InjectionError(
                f"Not a JMeter test plan (root is <{root.tag}>, expected <jmeterTestPlan>)"
            )

    def detect_unsafe_elements(self) -> list[str]:
        found: list[str] = []
        for tag in _DANGEROUS_TAGS:
            if any(True for _ in self._tree.iter(tag)):
                found.append(tag)
        return sorted(found)

    def parameterize_thread_group(self, mode: Mode) -> None:
        thread_groups = self._find_thread_groups()
        if not thread_groups:
            raise InjectionError(
                "No Thread Group found in the test plan. Is this a recorded JMeter scenario?"
            )

        for tg in thread_groups:
            if mode == "functional":
                self._set_string_prop(tg, "ThreadGroup.num_threads", "1")
                self._set_string_prop(tg, "ThreadGroup.ramp_time", "1")
                self._set_bool_prop(tg, "ThreadGroup.scheduler", "false")
                self._set_string_prop(tg, "ThreadGroup.duration", "")
                self._set_loops(tg, "1")
            elif mode == "load":
                self._set_string_prop(tg, "ThreadGroup.num_threads", "${__P(users,5)}")
                self._set_string_prop(tg, "ThreadGroup.ramp_time", "${__P(rampup,5)}")
                self._set_bool_prop(tg, "ThreadGroup.scheduler", "true")
                self._set_string_prop(tg, "ThreadGroup.duration", "${__P(duration,60)}")
                self._set_loops(tg, "-1")
            else:
                raise InjectionError(f"Unknown mode: {mode}")

    def inject_listener(self, jtl_path: str) -> None:
        test_plan_hashtree = self._test_plan_hashtree()
        collector = etree.fromstring(_SIMPLE_DATA_WRITER_XML)
        filename_prop = collector.find("stringProp[@name='filename']")
        filename_prop.text = jtl_path
        test_plan_hashtree.append(collector)
        test_plan_hashtree.append(etree.Element("hashTree"))

    def inject_default_assertion(self) -> None:
        if any(True for _ in self._tree.iter("ResponseAssertion")):
            return
        test_plan_hashtree = self._test_plan_hashtree()
        assertion = etree.fromstring(_DEFAULT_ASSERTION_XML)
        test_plan_hashtree.append(assertion)
        test_plan_hashtree.append(etree.Element("hashTree"))

    def serialize(self) -> bytes:
        return etree.tostring(
            self._tree, pretty_print=False, xml_declaration=True, encoding="UTF-8"
        )

    def _find_thread_groups(self) -> list[etree._Element]:
        out: list[etree._Element] = []
        for tag in _THREAD_GROUP_TAGS:
            out.extend(self._tree.iter(tag))
        return out

    def _test_plan_hashtree(self) -> etree._Element:
        root = self._tree.getroot()
        outer = root.find("hashTree")
        if outer is None:
            raise InjectionError("Malformed .jmx: no outer hashTree under jmeterTestPlan")
        test_plan = outer.find("TestPlan")
        if test_plan is None:
            raise InjectionError("Malformed .jmx: no TestPlan element")
        inner = test_plan.getnext()
        if inner is None or inner.tag != "hashTree":
            raise InjectionError("Malformed .jmx: TestPlan is not followed by a hashTree")
        return inner

    @staticmethod
    def _set_string_prop(parent: etree._Element, name: str, value: str) -> None:
        prop = parent.find(f"stringProp[@name='{name}']")
        if prop is None:
            prop = etree.SubElement(parent, "stringProp", {"name": name})
        prop.text = value

    @staticmethod
    def _set_bool_prop(parent: etree._Element, name: str, value: str) -> None:
        prop = parent.find(f"boolProp[@name='{name}']")
        if prop is None:
            prop = etree.SubElement(parent, "boolProp", {"name": name})
        prop.text = value

    @staticmethod
    def _set_loops(thread_group: etree._Element, loops: str) -> None:
        ctrl = thread_group.find("elementProp[@name='ThreadGroup.main_controller']")
        if ctrl is None:
            return
        prop = ctrl.find("stringProp[@name='LoopController.loops']")
        if prop is None:
            prop = etree.SubElement(ctrl, "stringProp", {"name": "LoopController.loops"})
        prop.text = loops
        forever = ctrl.find("boolProp[@name='LoopController.continue_forever']")
        if forever is not None:
            forever.text = "true" if loops == "-1" else "false"


def patch(
    jmx_bytes: bytes,
    *,
    mode: Mode,
    jtl_path: str,
    inject_assertion: bool = True,
) -> bytes:
    """Run the full pipeline. Raises InjectionError on unsafe content or malformed input."""
    engine = InjectionEngine(jmx_bytes)
    unsafe = engine.detect_unsafe_elements()
    if unsafe:
        raise InjectionError(
            f"Refused: scenario contains script-execution elements: {unsafe}. "
            "These can run arbitrary code on the server and are not allowed."
        )
    engine.parameterize_thread_group(mode)
    engine.inject_listener(jtl_path)
    if inject_assertion:
        engine.inject_default_assertion()
    return engine.serialize()
