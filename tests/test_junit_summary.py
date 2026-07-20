# -*- coding: utf-8 -*-
"""Tests for the matrix JUnit summary's logical-case accounting."""
import importlib.util
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / ".github" / "scripts" / "junit_summary.py"
SPEC = importlib.util.spec_from_file_location("junit_summary", SCRIPT)
junit_summary = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(junit_summary)


def _write_results(path, cases):
    body = []
    for classname, name, outcome, detail in cases:
        child = ""
        if outcome == "xfailed":
            child = '<skipped type="pytest.xfail" message="%s" />' % detail
        elif outcome == "skipped":
            child = '<skipped type="pytest.skip" message="%s" />' % detail
        elif outcome in ("failure", "error"):
            child = '<%s message="%s" />' % (outcome, detail)
        body.append(
            '<testcase classname="%s" name="%s">%s</testcase>'
            % (classname, name, child)
        )
    path.write_text("<testsuite>%s</testsuite>" % "".join(body), encoding="utf-8")


def test_identical_versions_and_repeated_shards_count_logical_cases_once(tmp_path):
    cases = [
        ("tests.corpus.test_corpus", "test_corpus_record[ind_00001]", "passed", ""),
        ("tests.test_example", "test_unit", "passed", ""),
        ("tests.corpus.test_corpus", "test_corpus_record[team_00001]", "xfailed", "known bug"),
    ]
    repeated_unit = [("tests.test_example", "test_unit", "passed", "")]
    for python in ("3.11", "3.14"):
        _write_results(tmp_path / ("results-%s-1.xml" % python), cases)
        _write_results(tmp_path / ("results-%s-2.xml" % python), repeated_unit)

    report = junit_summary.collect(tmp_path)
    rendered = junit_summary.render(report)

    assert report["by_group"]["Individual pairing (corpus)"]["passed"] == 1
    assert report["by_group"]["Team pairing (corpus)"]["xfailed"] == 1
    assert report["by_group"]["Unit & regression tests"]["passed"] == 1
    assert report["by_python"]["3.11"]["passed"] == 2
    assert report["by_python"]["3.14"]["passed"] == 2
    assert report["xfail_reasons"] == {"known bug": 1}
    assert "3 cases across 2 Python version(s)" in rendered
    assert "**1×** known bug" in rendered


def test_python_disagreement_counts_one_logical_failure(tmp_path):
    passed = [("tests.test_example", "test_unit", "passed", "")]
    failed = [("tests.test_example", "test_unit", "failure", "only on 3.14")]
    _write_results(tmp_path / "results-3.11-1.xml", passed)
    _write_results(tmp_path / "results-3.14-1.xml", failed)

    report = junit_summary.collect(tmp_path)
    rendered = junit_summary.render(report)

    assert report["by_group"]["Unit & regression tests"]["failed"] == 1
    assert report["by_python"]["3.11"]["passed"] == 1
    assert report["by_python"]["3.14"]["failed"] == 1
    assert "**❌ 1 failed / errored** — 1 cases" in rendered
