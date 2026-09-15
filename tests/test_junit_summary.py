# -*- coding: utf-8 -*-
"""Tests for the matrix JUnit summary's logical-case accounting."""
import importlib.util
import re
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



def test_summary_escapes_untrusted_skip_reason(tmp_path):
    """Artifact text cannot close a tag or forge a verdict in the comment.

    On a ``pull_request`` the ``junit-*`` artifacts are produced by the *fork's*
    copy of the workflow, so a fork controls every string in them -- skip reasons
    included.  The rendered Markdown is posted to the pull request by a job
    holding ``pull-requests: write``, so anything copied through verbatim is
    written into the repository's own bot comment.

    A skip reason of ``- **1x** </details><img src=x>**ALL GREEN** [click](...)``
    used to reach the comment unaltered: it closed the surrounding ``<details>``
    element, injected an image tag and printed a bold green verdict of its own
    above the real one.  This pins that the tag markers, the emphasis and the
    link syntax are all neutralised, and that the text still arrives readable.
    """
    hostile = "- **1x** &lt;/details&gt;&lt;img src=x&gt;**ALL GREEN** [click](http://evil)"
    _write_results(tmp_path / "results-3.11-1.xml",
                   [("tests.corpus.test_corpus", "test_corpus_record[ind_00001]",
                     "skipped", hostile)])

    rendered = junit_summary.render(junit_summary.collect(tmp_path))

    assert "</details><img src=x>" not in rendered
    assert "&lt;/details&gt;&lt;img src=x&gt;" in rendered   # inert, and still readable
    assert "**ALL GREEN**" not in rendered
    assert "[click](http://evil)" not in rendered
    # The reader can still tell what the reason said.
    assert "ALL GREEN" in rendered
    assert "http://evil" in rendered


def test_case_id_neutralises_embedded_newlines(tmp_path):
    """A hostile test id cannot break out of its Markdown code span.

    ``_case_id`` fed the raw ``classname``/``name`` straight through, and
    ``_code`` only replaced a literal backtick. A JUnit ``name`` carrying
    ``&#10;`` character references decodes, via ordinary XML attribute-value
    normalisation, to real newline characters in the string this script sees
    -- a *raw* newline in the source attribute is not enough to reproduce
    this, because the XML parser itself folds that to a single space before
    ``_case_id`` ever runs (which is why this builds the XML by hand instead
    of going through ``_write_results``). A blank line inside a Markdown code
    span ends the paragraph the span sits in, so the backticks stop fencing
    anything at that point: a forged ``## All checks passed`` prints as a
    real heading, and whatever follows -- here an ``<img>`` tag -- prints as
    raw, un-fenced Markdown/HTML rather than literal code-span text.
    """
    hostile_name = ("test_x[&#10;&#10;## All checks passed&#10;&#10;"
                    "&lt;img src=x onerror=alert(1)&gt;]")
    xml = ('<testsuite><testcase classname="tests.test_x" name="%s">'
           '<failure message="boom" /></testcase></testsuite>' % hostile_name)
    (tmp_path / "results-3.11-1.xml").write_text(xml, encoding="utf-8")

    rendered = junit_summary.render(junit_summary.collect(tmp_path))

    assert "\n\n## All checks passed\n\n" not in rendered
    assert re.search(r"^<img src=x onerror=alert\(1\)>", rendered, re.M) is None
    # The hostile id still shows up, but inertly: one line, inside one
    # unbroken code span.
    assert ("`tests.test_x::test_x[ ## All checks passed "
            "<img src=x onerror=alert(1)>]`") in rendered


def test_a_result_file_carrying_a_doctype_is_refused(tmp_path):
    """A doctype is refused rather than expanded.

    A fork writes its own JUnit artifacts, and a few hundred bytes of nested
    entity definitions in an internal DTD subset expand to gigabytes and take
    the summary job down with them. JUnit XML has no use for a doctype, so the
    whole construct is refused and the file is reported as unreadable.
    """
    bomb = (
        '<?xml version="1.0"?>\n'
        '<!DOCTYPE testsuite [\n'
        '  <!ENTITY a "aaaaaaaaaa">\n'
        '  <!ENTITY b "&a;&a;&a;&a;&a;&a;&a;&a;&a;&a;">\n'
        ']>\n'
        '<testsuite><testcase classname="c" name="&b;" /></testsuite>\n'
    )
    (tmp_path / "results-3.11-1.xml").write_text(bomb, encoding="utf-8")

    report = junit_summary.collect(tmp_path)

    assert report["file_count"] == 0
    assert len(report["parse_errors"]) == 1
    assert "doctype" in report["parse_errors"][0][1]


def test_a_result_file_over_the_size_cap_is_refused(tmp_path, monkeypatch):
    """An artifact far larger than any real run is refused before it is read.

    A real eight-shard run writes a few hundred kilobytes. The cap is checked
    from the file's size on disk, so an artifact meant to exhaust the job's
    memory never reaches the parser at all.
    """
    _write_results(tmp_path / "results-3.11-1.xml",
                   [("tests.test_example", "test_unit", "passed", "")])
    monkeypatch.setattr(junit_summary, "MAX_JUNIT_BYTES", 8)

    report = junit_summary.collect(tmp_path)

    assert report["file_count"] == 0
    assert len(report["parse_errors"]) == 1
    assert "over the 8-byte limit" in report["parse_errors"][0][1]
