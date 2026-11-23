"""`scripts/verapdf`'s reading of veraPDF's XML report (Story 13.7). CI runs the script itself on
the e2e's sample Student report."""

import importlib.machinery
import importlib.util
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "verapdf"


def load():
    loader = importlib.machinery.SourceFileLoader("verapdf", str(SCRIPT))
    spec = importlib.util.spec_from_loader("verapdf", loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


REPORT = """<?xml version="1.0" encoding="utf-8"?>
<report><jobs><job><validationReport profileName="PDF/UA-1" isCompliant="{compliant}">
<details passedRules="100" failedRules="1">
<rule specification="ISO 14289-1:2014" clause="7.18.1" testNumber="2" status="failed"
 failedChecks="3"><description>Every annotation shall be tagged</description></rule>
<rule specification="ISO 14289-1:2014" clause="7.1" testNumber="1" status="passed"
 passedChecks="9"><description>Fine</description></rule>
</details></validationReport></job></jobs></report>"""


def test_a_compliant_report_passes_and_a_failed_rule_is_named():
    verapdf = load()
    assert verapdf.failures(REPORT.format(compliant="true"))[0] is True
    compliant, rules = verapdf.failures(REPORT.format(compliant="false"))
    assert compliant is False
    assert rules == ["7.18.1-2: Every annotation shall be tagged (3)"]


def test_no_verdict_is_no_pass():
    assert load().failures("<report><jobs/></report>") == (None, [])
