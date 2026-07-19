# -*- coding: utf-8 -*-
"""Robustness regression test over the TRF corpus.

For every non-skipped record the engine is run over the tournament and its
verdict is compared against the record's ``valid`` flag: a well-formed
tournament must be accepted, a malformed one must be rejected -- and neither may
crash the engine.  ``valid`` is the golden output; there are no separate golden
files.

Markers are data-driven so a follow-up change retags a record by editing data,
not this module:

* ``skip: true`` records are skipped with their own ``skip_reason``. The current
  corpus has no skipped records.
* records named in ``known_failures.json`` are marked ``xfail`` with the reason
  recorded there -- these are tournaments the current engine gets wrong because
  of a known, not-yet-fixed bug.  ``strict=True`` means that when the bug is
  fixed the record turns into an XPASS and fails the suite, which is the signal
  to remove it from ``known_failures.json``.

By default a fast deterministic sample of the corpus runs, for quick local
feedback; set ``TIEBREAK_CORPUS_FULL=1`` to run all of it, which CI does on every
run.
"""
import pytest

import _harness

_KNOWN_FAILURES = _harness.load_known_failures()


def _parametrize():
    params = []
    for record in _harness.load_corpus():
        marks = []
        if record.get("skip"):
            marks.append(pytest.mark.skip(
                reason=record.get("skip_reason") or "skipped by the corpus"))
        elif record["name"] in _KNOWN_FAILURES:
            marks.append(pytest.mark.xfail(
                reason=_KNOWN_FAILURES[record["name"]], strict=True))
        params.append(pytest.param(record, id=record["name"], marks=marks))
    return params


@pytest.mark.parametrize("record", _parametrize())
def test_corpus_record(record):
    trf = record["trf"]

    # The tie-break path must never fault on any tournament in the corpus; the
    # branch's crash fixes are what make this hold.
    tiebreak_status = _harness.tiebreak_status(trf)
    assert tiebreak_status != 510, \
        "tie-break checker faulted (status 510) on %s" % record["name"]

    # Validity is an identity verdict over both the prescribed pairing and the
    # standings produced by the fixture's declared tie-breaks.
    accepts = _harness.pairing_status(trf) == 0 and tiebreak_status == 0
    assert accepts == record["valid"], (
        "engine %s %s, but the corpus marks it valid=%s"
        % ("accepted" if accepts else "rejected", record["name"], record["valid"]))
