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

The matrix runs the same logical tests under multiple Python versions, and its
corpus sharding causes the ordinary unit tests to be collected in every shard.
Headline, group and reason counts therefore de-duplicate by test id.  The
per-Python table remains version-specific so an interpreter disagreement stays
visible without multiplying the overall totals.

The report is grouped two ways -- by *test group* (the individual-pairing corpus
vs. the team corpus vs. the hand-written unit/regression tests) and by *Python
version* -- so the split the corpus already encodes in each record's name is
visible at a glance.

**Exit status.** Ordinary test failures are gated by the matrix jobs themselves,
which go red on their own, so this script reports them and still exits 0.  What
the matrix cannot see is a report that is *incomplete*: a shard whose artifact
never arrived, an XML file that would not parse, or a run in which nothing was
collected at all.  Those are invisible to every other check, and a summary that
says "All checks passed" while a quarter of the shards are missing is worse than
no summary, so they exit non-zero.  ``--expect-files`` states how many shard
result files must arrive; the workflow also passes the exact Python and shard
axes. This catches one coordinate being uploaded twice in place of a missing
coordinate even when the file count is right.

Everything read out of a JUnit artifact -- case ids, failure messages, skip
reasons, file names -- is attacker-controlled on a fork pull request, because the
fork's own copy of the workflow produces the artifacts.  The rendered Markdown is
posted as a comment by a privileged job, so every such string is neutralised on
the way into the report, by one of two mechanisms depending on where it lands.
Free text that sits directly in the prose -- failure/error messages, skip and
xfail reasons -- is HTML-entity- and Markdown-metacharacter-escaped by
``_escape``, so it can neither close a tag nor forge Markdown structure of its
own. Identifiers -- case ids, Python versions, shard numbers, file names -- are
instead rendered through ``_code``, an inert Markdown code span: its content is
never HTML-escaped, but a code span cannot itself open a tag, and collapsing
its internal whitespace keeps a blank line in the artifact from ending the
span early and letting whatever follows resume as ordinary, unfenced Markdown.
"""
import argparse
import collections
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

# File name written by the workflow: results-<python>-<shard>.xml
_FILE_RE = re.compile(r"results-(?P<python>.+)-(?P<shard>[^-]+)\.xml$")
# Parametrised corpus case: test_corpus_record[ind_00123] / [team_00045]
_CORPUS_RE = re.compile(r"test_corpus_record\[(?P<rid>.+)\]$")

# How many incompleteness problems to enumerate before summarising the rest.
_MAX_PROBLEMS = 20

# Outcome buckets, in report column order.
_OUTCOMES = ("passed", "failed", "errors", "xfailed", "skipped")

# Test groups, in report row order.
_INDIVIDUAL = "Individual pairing (corpus)"
_TEAM = "Team pairing (corpus)"
_UNIT = "Unit & regression tests"
_GROUP_ORDER = (_INDIVIDUAL, _TEAM, _UNIT)


# Markdown characters that carry structure in the report: emphasis, code spans,
# links, table cells and the backslash that escapes them.  A JUnit artifact is
# untrusted input (see the module docstring), so these are neutralised in every
# string that comes out of one.
_MARKDOWN_SPECIAL = re.compile(r"([\\`*_\[\]|~])")


def _escape(text):
    """Render *text* from an artifact as inert Markdown.

    ``<``, ``>`` and ``&`` become entities, so no tag can be opened or closed --
    a reason ending ``</details><img src=x>`` can neither escape the disclosure
    block it sits in nor load anything.  The structural Markdown characters are
    then backslash-escaped, so ``**ALL GREEN**`` prints its asterisks instead of
    forging a bold verdict and ``[click](http://evil)`` prints as the text it is
    rather than becoming a link.  Both survive legibly: the reader still sees
    what the artifact said, and none of it is markup any more.
    """
    text = (text or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return _MARKDOWN_SPECIAL.sub(r"\\\1", text)


def _code(text):
    """*text* from an artifact as an inert Markdown code span.

    A code span renders its contents literally -- HTML included -- so the only
    way out of one is a backtick of its own, which is what is replaced here.
    A code span also cannot survive a blank line: CommonMark ends the
    enclosing paragraph there, and everything beyond -- a forged heading, raw
    HTML -- resumes as ordinary Markdown outside the backticks. Collapsing
    whitespace closes that: a run of newlines from an artifact can no longer
    open a blank line inside the span.
    """
    text = " ".join((text or "").split())
    return "`%s`" % text.replace("`", "'")


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


# A fork's own workflow writes these files, so they are untrusted input to a job that
# holds pull-requests: write. ElementTree already refuses external entities, which is the
# half of the problem that reads files off the runner; the other half is an internal DTD
# subset, where a few hundred bytes of nested entity definitions expand to gigabytes and
# take the job down with them ("billion laughs"). JUnit XML has no use for a doctype at
# all, so the whole construct is refused rather than bounded, and the file is capped
# before it is read: a real 8-shard run writes a few hundred KB.
MAX_JUNIT_BYTES = 32 * 1024 * 1024


def _parse_junit(path):
    """Parse one JUnit file, refusing the shapes a hostile fork could send."""
    size = path.stat().st_size
    if size > MAX_JUNIT_BYTES:
        raise ValueError(
            "file is %d bytes, over the %d-byte limit" % (size, MAX_JUNIT_BYTES)
        )
    data = path.read_bytes()
    head = data[:4096].lstrip()
    if b"<!DOCTYPE" in head or b"<!ENTITY" in data:
        raise ValueError("file carries a doctype or entity definition, which JUnit XML does not use")
    return ET.fromstring(data)


def _case_id(testcase):
    """The test id shown to the reader, always rendered through ``_code``.

    Whitespace is collapsed here too, not just in ``_code``, so a case id
    built from the classname and name concatenation cannot reintroduce a
    blank line between the two halves.
    """
    classname = " ".join((testcase.get("classname", "") or "").split())
    name = " ".join((testcase.get("name", "?") or "").split())
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
    cases_by_python = collections.defaultdict(dict)
    pythons = set()
    file_count = 0
    parse_errors = []
    coordinates = collections.Counter()

    for path in sorted(directory.rglob("results-*.xml")):
        name_match = _FILE_RE.fullmatch(path.name)
        if name_match is None:
            parse_errors.append((path.name, "filename is not results-<python>-<shard>.xml"))
            python = "unknown"
        else:
            python = name_match.group("python")
            coordinates[(python, name_match.group("shard"))] += 1
        pythons.add(python)
        try:
            root = _parse_junit(path)
        except (ET.ParseError, ValueError) as exc:
            parse_errors.append((path.name, str(exc)))
            continue
        file_count += 1
        for testcase in root.iter("testcase"):
            case_id = _case_id(testcase)
            outcome = _outcome_of(testcase)
            reason = ""
            message = ""
            if outcome in ("failed", "errors"):
                kind = "failure" if outcome == "failed" else "error"
                message = _fault_message(testcase, kind)
            elif outcome in ("xfailed", "skipped"):
                reason = _skip_reason(testcase.find("skipped"))

            result = {
                "group": _group_of(testcase.get("name", "")),
                "outcome": outcome,
                "reason": reason,
                "message": message,
            }
            previous = cases_by_python[python].get(case_id)
            if previous is None:
                cases_by_python[python][case_id] = result
            elif (previous["outcome"], previous["reason"]) != \
                    (result["outcome"], result["reason"]):
                # Every unit test in the matrix runs in all eight corpus
                # shards, so this is the common case, not a rare one. Only the
                # *outcome* (and, for a skip/xfail, its reason) says whether
                # the shards agree about the test -- a failure message can
                # differ harmlessly between shards (a line number, a captured
                # timing, an object's repr address) without the runs actually
                # disagreeing about what happened. Comparing the whole result,
                # message included, turned every one of those into a false
                # integrity error.
                parse_errors.append((
                    path.name,
                    "conflicting duplicate result for %s under Python %s"
                    % (case_id, python),
                ))

    by_group = collections.defaultdict(_blank)
    by_python = collections.defaultdict(_blank)
    failures = []                          # (python, case id, message)
    skip_reasons = collections.Counter()   # reason -> unique logical case count
    xfail_reasons = collections.Counter()  # reason -> unique logical case count

    logical_cases = collections.defaultdict(dict)
    for python, cases in cases_by_python.items():
        for case_id, result in cases.items():
            by_python[python][result["outcome"]] += 1
            logical_cases[case_id][python] = result
            if result["outcome"] in ("failed", "errors"):
                failures.append((python, case_id, result["message"]))

    # One logical case contributes once to the overall report. If interpreters
    # disagree, retain the most severe outcome; the per-Python table below shows
    # exactly which interpreter produced it.
    severity = {"passed": 0, "xfailed": 1, "skipped": 2, "failed": 3, "errors": 4}
    for versions in logical_cases.values():
        result = max(versions.values(), key=lambda item: severity[item["outcome"]])
        by_group[result["group"]][result["outcome"]] += 1
        if result["outcome"] == "xfailed":
            xfail_reasons[result["reason"]] += 1
        elif result["outcome"] == "skipped":
            skip_reasons[result["reason"]] += 1

    return {
        "by_group": by_group,
        "by_python": by_python,
        "failures": failures,
        "skip_reasons": skip_reasons,
        "xfail_reasons": xfail_reasons,
        "pythons": pythons,
        "file_count": file_count,
        "coordinates": coordinates,
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
        # The reason comes out of a JUnit artifact, so it is escaped here rather
        # than in collect(): the counters stay keyed on what the marker actually
        # said, and only the rendered line is made inert.
        lines.append("- **%s×** %s" % (format(count, ","), _escape(reason)))
    lines.append("")
    return lines


def integrity_problems(report, expected_files=None, expected_coordinates=None):
    """Reasons this aggregate cannot be read as a complete picture of the run.

    These are the faults no other check can see.  A shard whose job dies before
    pytest writes its XML uploads nothing at all, and the aggregate over the
    shards that *did* report is then perfectly green; a corrupt or truncated
    artifact drops its whole shard just as quietly; two shards reporting different
    outcomes for one test id make the de-duplicated totals meaningless.  Ordinary
    test failures are deliberately *not* listed here -- the matrix job that
    produced them is already red, and this script need not duplicate that gate.

    Returns a list of rendered Markdown lines; empty means the report covers
    everything it was supposed to cover.
    """
    problems = []
    total_cases = sum(sum(counts.values()) for counts in report["by_group"].values())

    if expected_files:
        shortfall = expected_files - report["file_count"]
        if shortfall > 0:
            problems.append(
                "**%d of %d expected shard result file(s) never arrived.** A shard "
                "whose job fails before pytest writes its JUnit XML uploads nothing, "
                "so its tests are missing from every count below."
                % (shortfall, expected_files))
        elif shortfall < 0:
            problems.append(
                "**%d more shard result file(s) arrived than the %d expected.** The "
                "matrix and `--expect-files` have drifted apart, so the counts below "
                "cover something other than the run that was configured."
                % (-shortfall, expected_files))

    coordinates = report.get("coordinates", {})
    for python, shard in sorted(
            coordinate for coordinate, count in coordinates.items() if count > 1):
        problems.append(
            "Duplicate shard coordinate %s/%s arrived %d times; one or more "
            "different matrix coordinates may be missing."
            % (_code(python), _code(shard), coordinates[(python, shard)]))

    if expected_coordinates is not None:
        expected = set(expected_coordinates)
        observed = set(coordinates)
        for python, shard in sorted(expected - observed):
            problems.append("Missing expected shard coordinate %s/%s."
                            % (_code(python), _code(shard)))
        for python, shard in sorted(observed - expected):
            problems.append("Unexpected shard coordinate %s/%s."
                            % (_code(python), _code(shard)))

    # Unreadable XML, and any pair of shards that reported contradictory results
    # for the same test id: in both cases the totals below cover something other
    # than the run that was asked for.
    for filename, message in report["parse_errors"]:
        problems.append("Result file %s — %s"
                        % (_code(filename), _escape(message)))

    if total_cases == 0:
        problems.append(
            "**No test cases were parsed at all.** Either no artifact reached the "
            "summary job or every one of them was unreadable.")

    return problems


def render(report, expected_files=None, expected_coordinates=None):
    by_group = report["by_group"]
    by_python = report["by_python"]
    failures = report["failures"]
    pythons = report["pythons"]
    file_count = report["file_count"]

    grand = _blank()
    for counts in by_group.values():
        for outcome in _OUTCOMES:
            grand[outcome] += counts[outcome]
    total_cases = sum(grand.values())
    problems = integrity_problems(report, expected_files, expected_coordinates)
    broken = grand["failed"] + grand["errors"]

    out = ["## \U0001f9ea Test results", ""]

    # The incompleteness block comes first and is never skipped: when nothing
    # parsed at all it is the only thing there is to say, and the early return
    # that used to sit above it took the diagnostic down with it.
    if problems:
        out.append("**❌ Incomplete — these results do not cover the whole run "
                   "and must not be read as a pass.**")
        out.append("")
        for problem in problems[:_MAX_PROBLEMS]:
            out.append("- %s" % problem)
        if len(problems) > _MAX_PROBLEMS:
            out.append("- … and %d more" % (len(problems) - _MAX_PROBLEMS))
        out.append("")

    if total_cases == 0:
        return "\n".join(out) + "\n"

    expected_note = ("" if not expected_files
                     else " of %d expected" % expected_files)
    if broken or problems:
        out.append("**❌ %s failed / errored** — %s cases across %d "
                   "Python version(s), %d%s shard result file(s)."
                   % (format(broken, ","), format(total_cases, ","),
                      len(pythons), file_count, expected_note))
    else:
        out.append("**✅ All checks passed** — %s cases across %d "
                   "Python version(s), %d%s shard result file(s)."
                   % (format(total_cases, ","), len(pythons),
                      file_count, expected_note))
    out.append("")

    if not expected_files:
        out.append("_No `--expect-files` was given, so nothing checked that every "
                   "shard reported. The counts below cover the artifacts that "
                   "arrived, whatever was supposed to._")
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
    rows = [_row("Python %s" % _escape(python), by_python[python])
            for python in sorted(by_python)]
    out.extend(_table("Python", rows))
    out.append("")

    out.append("_Headline, group and reason counts show each logical test once. "
               "The rows above remain per Python version so compatibility "
               "differences are visible._")
    out.append("")

    # Explain the non-passing outcomes, straight from the markers' own reasons.
    out.extend(_reasons_block(
        "⚠️ Known-fail — why these `xfail`",
        "Records the engine is expected to get wrong today; tracked in "
        "`tests/corpus/known_failures.json` and feature overlays under "
        "`tests/corpus/known_failure_overlays/`. A fix turns each into an XPASS, "
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
            suffix = " — %s" % _escape(message) if message else ""
            out.append("- %s _(py%s)_%s"
                       % (_code(case_id), _escape(python), suffix))
        if len(failures) > 100:
            out.append("- … and %d more" % (len(failures) - 100))
        out.append("")
        out.append("</details>")
        out.append("")

    return "\n".join(out) + "\n"


def parse_args(argv):
    parser = argparse.ArgumentParser(
        description="Aggregate per-shard JUnit XML into a Markdown summary.")
    parser.add_argument(
        "directory", nargs="?", default=".", type=Path,
        help="directory the results-*.xml artifacts were downloaded into")
    parser.add_argument(
        "--expect-files", type=int, default=None, metavar="N",
        help="how many shard result files must be present. The workflow passes "
             "the size of its own test matrix; a shortfall means a shard "
             "reported nothing and the summary exits non-zero rather than "
             "reporting a pass over what is left.")
    parser.add_argument(
        "--expect-python", action="append", default=[], metavar="VERSION",
        help="Python matrix version expected in every shard coordinate; repeat for each version.")
    parser.add_argument(
        "--expect-shard", action="append", default=[], metavar="NUMBER",
        help="1-based corpus shard expected for every Python version; repeat for each shard.")
    return parser.parse_args(argv)


def main(argv):
    args = parse_args(argv[1:])
    expected_coordinates = None
    if args.expect_python or args.expect_shard:
        if not args.expect_python or not args.expect_shard:
            raise SystemExit("--expect-python and --expect-shard must be used together")
        expected_coordinates = {
            (python, str(shard))
            for python in args.expect_python
            for shard in args.expect_shard
        }
    report = collect(args.directory)
    sys.stdout.write(render(report, args.expect_files, expected_coordinates))
    # Ordinary test failures leave this at 0: the matrix job that produced them
    # is already red. A non-zero status here means the *aggregate itself* cannot
    # be trusted, which nothing else in the run would otherwise notice.
    return 1 if integrity_problems(report, args.expect_files, expected_coordinates) else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
