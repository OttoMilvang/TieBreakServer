# -*- coding: utf-8 -*-
"""Regenerate known_failures.json against the current engine.

Runs every non-skipped corpus record through the same check the test applies and
records the ones that fail -- the tournaments whose combined pairing/standings
identity verdict disagrees with the corpus `valid` label, or that fault the
tie-break path. Those are the
records the test marks ``xfail``.

Reasons are preserved: a record that still fails keeps the reason it already had
in known_failures.json; a record that no longer fails drops out; a record that
fails but was not listed before is added under an "unclassified" reason for a
human to describe.  Run this after changing the engine, review the diff, and
commit it.

Usage (from the repo root, uses all cores):

    python tests/corpus/regen_known_failures.py
"""
import json
import os
import sys
import time
from multiprocessing import Pool

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _harness  # noqa: E402

UNCLASSIFIED = ("unclassified -- the engine fails this record but no reason has been "
                "recorded yet; investigate and describe the bug here")


def _test_fails(record):
    """Mirror the assertions in test_corpus.test_corpus_record."""
    trf = record["trf"]
    tiebreak_status = _harness.tiebreak_status(trf)
    if tiebreak_status == 510:
        return (record["name"], True)
    accepts = _harness.pairing_status(trf) == 0 and tiebreak_status == 0
    return (record["name"], accepts != record["valid"])


def main():
    records = [r for r in _harness.load_corpus(full=True) if not r.get("skip")]
    total = len(records)
    prior = _harness.load_known_failures()
    print("checking %d non-skipped records ..." % total, flush=True)

    failing = []
    done = 0
    t0 = time.time()
    last = 0.0
    with Pool() as pool:
        for name, fails in pool.imap_unordered(_test_fails, records, chunksize=8):
            done += 1
            if fails:
                failing.append(name)
            now = time.time()
            if now - last > 3 or done == total:
                el = now - t0
                rate = done / el if el else 0
                eta = (total - done) / rate if rate else 0
                print("  %5d/%d (%3.0f%%)  %4.0f rec/s  elapsed %4.0fs  ETA %4.0fs"
                      % (done, total, 100 * done / total, rate, el, eta), flush=True)
                last = now

    grouped = {}
    for name in sorted(failing):
        grouped.setdefault(prior.get(name, UNCLASSIFIED), []).append(name)

    with open(_harness.KNOWN_FAILURES, "w") as handle:
        json.dump(grouped, handle, indent=2)
        handle.write("\n")
    print("\nwrote %s\n  %d known failures across %d reason group(s)"
          % (_harness.KNOWN_FAILURES, len(failing), len(grouped)))
    if UNCLASSIFIED in grouped:
        print("  %d are UNCLASSIFIED -- give them a reason before committing"
              % len(grouped[UNCLASSIFIED]))


if __name__ == "__main__":
    main()
