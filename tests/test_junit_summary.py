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

def test_same_outcome_different_message_across_shards_is_not_an_integrity_error(tmp_path):
    """A failure message differing by shard is not a shard disagreement.

    Every unit test in the matrix runs in all eight corpus shards, under the
    same Python version, so the same case id reaches ``collect`` once per
    shard. ``collect`` used to compare the whole result -- message included --
    across those arrivals, and flagged any difference as a "conflicting
    duplicate result" integrity problem. A failure message can legitimately
    differ between shards that agree the test failed: a captured object's
    repr address, a line number from a shard-specific temp path, a timing
    figure. None of that is a disagreement about the *outcome*.
    """
    first = [("tests.test_example", "test_unit", "failure", "boom at line 12")]
    second = [("tests.test_example", "test_unit", "failure", "boom at line 47")]
    _write_results(tmp_path / "results-3.11-1.xml", first)
    _write_results(tmp_path / "results-3.11-2.xml", second)

    report = junit_summary.collect(tmp_path)

    assert report["parse_errors"] == []
    assert report["by_group"]["Unit & regression tests"]["failed"] == 1


def test_different_outcome_across_shards_is_still_an_integrity_error(tmp_path):
    """Shards that disagree about the outcome itself are still flagged.

    Ignoring the message must not swallow a real disagreement: one shard
    reporting a pass and another a failure for the same case id under the
    same Python version means the shards do not agree what happened, which is
    exactly the kind of problem this integrity check exists to surface.
    """
    passing = [("tests.test_example", "test_unit", "passed", "")]
    failing = [("tests.test_example", "test_unit", "failure", "boom")]
    _write_results(tmp_path / "results-3.11-1.xml", passing)
    _write_results(tmp_path / "results-3.11-2.xml", failing)

    report = junit_summary.collect(tmp_path)

    assert len(report["parse_errors"]) == 1
    assert "conflicting duplicate result" in report["parse_errors"][0][1]

