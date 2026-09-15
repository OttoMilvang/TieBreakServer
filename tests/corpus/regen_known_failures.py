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

The whole corpus is always used: the CI shard variables are stripped before the
records are read, because a baseline regenerated from one shard silently drops
every known failure outside it.  See ``load_records``.

An UNCLASSIFIED entry is a placeholder, not a verdict -- it means a record fails
today and nobody has said why yet.  Writing one to the checked-in file lets it
sit there indefinitely with no human having looked at it, which is exactly the
gap the "unclassified" reason exists to flag rather than hide.  So by default
this refuses to write a baseline that would contain one: it exits non-zero and
prints the offending record names instead of committing them silently.  Pass
``--allow-unclassified`` to write anyway (the record still lands in the
UNCLASSIFIED group, still printed as a reminder) when that is genuinely what is
wanted -- for instance, capturing a fresh batch of failures before triaging them
one by one.

Usage (from the repo root, uses all cores):

    python tests/corpus/regen_known_failures.py
    python tests/corpus/regen_known_failures.py --allow-unclassified
"""
import argparse
import json
import os
import sys
import time
from multiprocessing import Pool

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _harness  # noqa: E402

UNCLASSIFIED = ("unclassified -- the engine fails this record but no reason has been "
                "recorded yet; investigate and describe the bug here")

# The variables CI uses to split the corpus across runners.  _harness.load_corpus
# honours them, which is right for the test suite and wrong here.
SHARD_VARS = ("TIEBREAK_CORPUS_SHARDS", "TIEBREAK_CORPUS_SHARD")


def load_records():
    """Every non-skipped corpus record, whatever the environment says.

    ``_harness.load_corpus`` splits the corpus when TIEBREAK_CORPUS_SHARDS and
    TIEBREAK_CORPUS_SHARD are set, which is how the eight CI runners divide the
    work.  This script rewrites the *whole* of known_failures.json, so reading a
    shard would not produce a partial baseline -- it would produce a complete-
    looking one with seven eighths of the failures missing, and nothing in the
    file's shape to show it.  Anyone regenerating in a shell where the variables
    are still exported, or inside a container that inherits the CI environment,
    would commit that.

    So the variables are removed from the environment for the rest of the run,
    and their removal is announced rather than done silently.
    """
    ignored = [name for name in SHARD_VARS if name in os.environ]
    for name in ignored:
        del os.environ[name]
    if ignored:
        print("ignoring %s: this rewrites the whole baseline, so it always reads "
              "the whole corpus" % " and ".join(ignored), flush=True)
    return [r for r in _harness.load_corpus(full=True) if not r.get("skip")]


def _test_fails(record):
    """Mirror the assertions in test_corpus.test_corpus_record."""
    trf = record["trf"]
    tiebreak_status = _harness.tiebreak_status(trf)
    if tiebreak_status == 510:
        return (record["name"], True)
    pairing_status = _harness.pairing_status(trf)
    if record["category"] == "team" and pairing_status == 510:
        return (record["name"], True)
    accepts = pairing_status == 0 and tiebreak_status == 0
    return (record["name"], accepts != record["valid"])


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--allow-unclassified", action="store_true",
        help="write known_failures.json even though it would contain an "
             "UNCLASSIFIED entry, instead of refusing. Without this, a "
             "record that fails today with no reason recorded yet stops "
             "the write so a human describes it first.")
    return parser.parse_args(argv)


def _has_unclassified_without_permission(grouped, allow_unclassified):
    """True if *grouped* would commit an UNCLASSIFIED entry that nobody has
    explicitly allowed. A record landing in this group is not a verdict --
    it is a record whose failure nobody has looked at yet -- so writing it
    to the checked-in baseline by default would let it sit there
    indefinitely with nothing to say it was never triaged."""
    return UNCLASSIFIED in grouped and not allow_unclassified


def main(argv=None):
    args = parse_args(argv)

    records = load_records()
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

    if _has_unclassified_without_permission(grouped, args.allow_unclassified):
        print(
            "\nrefusing to write %s: %d record(s) fail with no reason "
            "recorded yet:" % (_harness.KNOWN_FAILURES, len(grouped[UNCLASSIFIED])),
            file=sys.stderr,
        )
        for name in grouped[UNCLASSIFIED]:
            print("  %s" % name, file=sys.stderr)
        print(
            "Investigate and describe each one under an existing or new "
            "reason, or pass --allow-unclassified to write this baseline "
            "with them left UNCLASSIFIED.",
            file=sys.stderr,
        )
        return 1

    with open(_harness.KNOWN_FAILURES, "w") as handle:
        json.dump(grouped, handle, indent=2)
        handle.write("\n")
    print("\nwrote %s\n  %d known failures across %d reason group(s)"
          % (_harness.KNOWN_FAILURES, len(failing), len(grouped)))
    if UNCLASSIFIED in grouped:
        print("  %d are UNCLASSIFIED -- give them a reason before committing"
              % len(grouped[UNCLASSIFIED]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
