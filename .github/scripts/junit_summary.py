# -*- coding: utf-8 -*-
"""Aggregate the per-shard JUnit XML into a GitHub Actions step summary.

The ``tests`` workflow fans out across a matrix of Python versions and corpus
shards; every job writes one JUnit file named ``results-<python>-<shard>.xml``
and uploads it as an artifact.  The ``summary`` job downloads them all into one
directory and runs this script, whose Markdown output is appended to
``$GITHUB_STEP_SUMMARY`` so the run's landing page shows a single aggregated
report instead of requiring a click into each of the sixteen jobs.

Usage::

    python .github/scripts/junit_summary.py <dir-of-junit-xml> >> "$GITHUB_STEP_SUMMARY"

pytest encodes each outcome in JUnit XML as a ``<testcase>`` element:

* pass    -- no child element
* failure -- a ``<failure>`` child  (a *strict* XPASS also lands here)
* error   -- an ``<error>`` child
* xfail   -- a ``<skipped type="pytest.xfail">`` child  (a tolerated known bug)
* skip    -- a ``<skipped type="pytest.skip">`` child

so expected failures and plainly skipped records are told apart by the
``<skipped>`` element's ``type``, rather than lumped together the way the
``<testsuite>`` ``skipped`` attribute would.

The report is grouped two ways -- by *test group* (the individual-pairing corpus
vs. the team corpus vs. the hand-written unit/regression tests) and by *Python
version* -- so the split the corpus already encodes in each record's name is
visible at a glance.  This script only reports; the matrix jobs are what gate the
pull request, so it always exits 0 (an aggregation hiccup must not turn a green
run red).
"""
import collections
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

# File name written by the workflow: results-<python>-<shard>.xml
_FILE_RE = re.compile(r"results-(?P<python>.+)-(?P<shard>[^-]+)\.xml$")
# Parametrised corpus case: test_corpus_record[ind_00123] / [team_00045]
_CORPUS_RE = re.compile(r"test_corpus_record\[(?P<rid>.+)\]$")

# Outcome buckets, in report column order.
_OUTCOMES = ("passed", "failed", "errors", "xfailed", "skipped")

# Test groups, in report row order.
_INDIVIDUAL = "Individual pairing (corpus)"
_TEAM = "Team pairing (corpus)"
_UNIT = "Unit & regression tests"
_GROUP_ORDER = (_INDIVIDUAL, _TEAM, _UNIT)


def _blank():
    return dict.fromkeys(_OUTCOMES, 0)


def _group_of(name):
    """Which test group a ``<testcase name=...>`` belongs to."""
    match = _CORPUS_RE.match(name)
    if not match:
        return _UNIT
    return _TEAM if match.group("rid").startswith("team") else _INDIVIDUAL


def _outcome_of(testcase):
    """Map a ``<testcase>`` element to one of ``_OUTCOMES``."""
    if testcase.find("failure") is not None:
        return "failed"
    if testcase.find("error") is not None:
        return "errors"
    skipped = testcase.find("skipped")
    if skipped is not None:
        return "xfailed" if skipped.get("type") == "pytest.xfail" else "skipped"
    return "passed"


def _case_id(testcase):
    classname = testcase.get("classname", "")
    name = testcase.get("name", "?")
    return "%s::%s" % (classname, name) if classname else name


def _clip(text, limit=200):
    text = " ".join((text or "").split())
    return text[:limit - 3] + "..." if len(text) > limit else text


def _fault_message(testcase, kind):
    """A one-line, trimmed failure/error message for the details list."""
    element = testcase.find(kind)
    if element is None:
        return ""
    return _clip(element.get("message") or (element.text or ""))


def _skip_reason(skipped):
    """The reason a case was skipped or xfailed.

    pytest stores the marker's ``reason=`` in the ``<skipped>`` ``message``
    attribute (the element text repeats it with a file:line prefix), so the
    corpus's own explanation flows through unchanged.
    """
    return _clip(skipped.get("message") or (skipped.text or ""), limit=600) \
        or "(no reason recorded)"


def collect(directory):
    """Parse every ``results-*.xml`` under *directory* into a report dict."""
    by_group = collections.defaultdict(_blank)
    by_python = collections.defaultdict(_blank)
    failures = []                          # (python, case id, message)
    skip_reasons = collections.Counter()   # reason -> count
    xfail_reasons = collections.Counter()  # reason -> count
    pythons = set()
    file_count = 0
    parse_errors = []

    for path in sorted(directory.rglob("results-*.xml")):
        name_match = _FILE_RE.search(path.name)
        python = name_match.group("python") if name_match else "unknown"
        pythons.add(python)
        try:
            root = ET.parse(path).getroot()
        except ET.ParseError as exc:
            parse_errors.append((path.name, str(exc)))
            continue
        file_count += 1
        for testcase in root.iter("testcase"):
            outcome = _outcome_of(testcase)
            by_group[_group_of(testcase.get("name", ""))][outcome] += 1
            by_python[python][outcome] += 1
            if outcome in ("failed", "errors"):
                kind = "failure" if outcome == "failed" else "error"
                failures.append((python, _case_id(testcase), _fault_message(testcase, kind)))
            elif outcome == "xfailed":
                xfail_reasons[_skip_reason(testcase.find("skipped"))] += 1
            elif outcome == "skipped":
                skip_reasons[_skip_reason(testcase.find("skipped"))] += 1

    return {
        "by_group": by_group,
        "by_python": by_python,
        "failures": failures,
        "skip_reasons": skip_reasons,
        "xfail_reasons": xfail_reasons,
        "pythons": pythons,
        "file_count": file_count,
        "parse_errors": parse_errors,
    }


def _row(label, counts):
    total = sum(counts.values())
    return "| %s | %s | %s | %s | %s | %s | %s |" % (
        label,
        format(total, ","),
        format(counts["passed"], ","),
        format(counts["failed"], ","),
        format(counts["errors"], ","),
        format(counts["xfailed"], ","),
        format(counts["skipped"], ","),
    )


def _table(header, rows):
    lines = [
        "| %s | Cases | ✅ Passed | ❌ Failed | \U0001f4a5 Errors "
        "| ⚠️ Known-fail | ⏭️ Skipped |" % header,
        "| --- | --: | --: | --: | --: | --: | --: |",
    ]
    lines.extend(rows)
    return lines


def _reasons_block(title, note, reasons):
    """A section listing the distinct reasons (and their counts) behind a
    skipped/xfailed outcome, taken from the corpus's own marker text."""
    if not reasons:
        return []
    lines = ["### %s" % title, "", "_%s_" % note, ""]
    for reason, count in reasons.most_common():
        lines.append("- **%s×** %s" % (format(count, ","), reason))
    lines.append("")
    return lines


def render(report):
    by_group = report["by_group"]
    by_python = report["by_python"]
    failures = report["failures"]
    pythons = report["pythons"]
    file_count = report["file_count"]
    parse_errors = report["parse_errors"]

    grand = _blank()
    for counts in by_python.values():
        for outcome in _OUTCOMES:
            grand[outcome] += counts[outcome]
    total_cases = sum(grand.values())
    broken = grand["failed"] + grand["errors"] + len(parse_errors)

    out = ["## \U0001f9ea Test results", ""]

    if total_cases == 0:
        out.append("⚠️ No JUnit results were found to summarise.")
        return "\n".join(out) + "\n"

    if broken:
        out.append("**❌ %s failed / errored** — %s cases across %d "
                   "Python version(s), %d shard result file(s)."
                   % (format(broken, ","), format(total_cases, ","),
                      len(pythons), file_count))
    else:
        out.append("**✅ All checks passed** — %s cases across %d "
                   "Python version(s), %d shard result file(s)."
                   % (format(total_cases, ","), len(pythons), file_count))
    out.append("")

    # By test group -- the split the corpus encodes in each record's name.
    out.append("### By test group")
    out.append("")
    rows = [_row(group, by_group[group]) for group in _GROUP_ORDER if group in by_group]
    rows.extend(_row(group, by_group[group])
                for group in sorted(by_group) if group not in _GROUP_ORDER)
    rows.append(_row("**Total**", grand))
    out.extend(_table("Group", rows))
    out.append("")

    # By Python version -- the matrix's other axis.
    out.append("### By Python version")
    out.append("")
    rows = [_row("Python %s" % python, by_python[python])
            for python in sorted(by_python)]
    rows.append(_row("**Total**", grand))
    out.extend(_table("Python", rows))
    out.append("")

    out.append("_Counts sum every matrix job, so each corpus record appears once "
               "per Python version (e.g. 158 known-fail records × 2 = 316)._")
    out.append("")

    # Explain the non-passing outcomes, straight from the markers' own reasons.
    out.extend(_reasons_block(
        "⚠️ Known-fail — why these `xfail`",
        "Records the engine is expected to get wrong today; tracked in "
        "`tests/corpus/known_failures.json`. A fix turns each into an XPASS, "
        "which fails the strict marker and is the signal to drop it.",
        report["xfail_reasons"]))
    out.extend(_reasons_block(
        "⏭️ Skipped — why these do not run",
        "Records the suite collects but does not check, by the `skip` flag in "
        "the corpus data.",
        report["skip_reasons"]))

    if failures:
        out.append("<details><summary>❌ %d failed / errored case(s)</summary>"
                   % len(failures))
        out.append("")
        for python, case_id, message in failures[:100]:
            suffix = " — %s" % message if message else ""
            out.append("- `%s` _(py%s)_%s" % (case_id, python, suffix))
        if len(failures) > 100:
            out.append("- … and %d more" % (len(failures) - 100))
        out.append("")
        out.append("</details>")
        out.append("")

    if parse_errors:
        out.append("<details><summary>⚠️ %d result file(s) could not "
                   "be parsed</summary>" % len(parse_errors))
        out.append("")
        for filename, message in parse_errors:
            out.append("- `%s` — %s" % (filename, message))
        out.append("")
        out.append("</details>")
        out.append("")

    return "\n".join(out) + "\n"


def main(argv):
    directory = Path(argv[1]) if len(argv) > 1 else Path(".")
    sys.stdout.write(render(collect(directory)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
