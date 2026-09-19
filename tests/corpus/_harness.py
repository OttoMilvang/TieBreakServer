# -*- coding: utf-8 -*-
"""Shared machinery for the TRF corpus test.

The corpus (``corpus.jsonl.gz``) is a gzip-compressed JSON-lines file, one
tournament per line::

    {"name": "ind_00000", "category": "individual", "valid": true,
     "skip": false, "skip_reason": null, "trf": "062 45\\n072 45\\n001 ..."}

Each record carries the expected verdict in ``valid``: a well-formed tournament
the engine should accept (``true``) or one it should reject (``false``).  The
test drives the *real* command-line checker over the record's TRF and compares
what the engine decides against ``valid``.

To keep thousands of records affordable the checker is run **in-process**: the
engine modules are imported once per worker (so the interpreter and networkx are
not reloaded per record) and each record is fed through the same
``commonmain.common_main`` pipeline the ``pairingchecker.py`` / ``tiebreakchecker.py``
command-line tools use, so the full read -> prepare -> check -> apply path is
exercised, not a reimplementation of it.  Records are spread across cores with
``pytest-xdist``; each record still rebuilds its own pairing graph, which is the
irreducible cost of checking a distinct tournament.
"""
import contextlib
import gzip
import io
import json
import os
import sys
import tempfile
from pathlib import Path

CORPUS_DIR = Path(__file__).resolve().parent
CORPUS_GZ = CORPUS_DIR / "corpus.jsonl.gz"
KNOWN_FAILURES = CORPUS_DIR / "known_failures.json"
KNOWN_FAILURE_OVERLAYS = CORPUS_DIR / "known_failure_overlays"
REPO_ROOT = CORPUS_DIR.parent.parent

sys.path.insert(0, str(REPO_ROOT))

from gacrux.pairingchecker import pairingchecker  # noqa: E402
from gacrux.tiebreakchecker import tiebreakchecker  # noqa: E402

# Number of records a non-full run samples from the corpus.  A deterministic
# stride is used so every worker (and every run) selects the same subset.
SAMPLE_SIZE = 500

_TMPDIR = tempfile.gettempdir()


def _scratch(suffix):
    # One scratch path per process, so xdist workers / pool workers never
    # clobber each other's input or output file.
    return os.path.join(_TMPDIR, "tiebreak_corpus_%d.%s" % (os.getpid(), suffix))


def _drive(checker_cls, extra_argv):
    """Run one checker over the TRF already written to the scratch input file
    and return its ``status.code`` (0 = check passed, 1 = check failed / declared
    pairing differs, 510 = the engine raised while checking, 4xx/5xx = a read or
    setup error)."""
    obj = checker_cls()
    argv = ["checker", "-i", _scratch("trf"), "-o", _scratch("out"), "-c"] + extra_argv
    saved_argv = sys.argv
    sys.argv = argv
    try:
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            try:
                obj.common_main()
            except SystemExit as exc:
                # A checker may call exit() for a command-line failure. Preserve a
                # numeric exit status when it bypassed the normal result object;
                # swallowing it would turn a broken corpus case into an apparent
                # pass (or an uninformative None).
                if exc.code not in (None, 0):
                    return exc.code if isinstance(exc.code, int) else 510
            except Exception:
                # common_main normally converts engine faults to a 510 status
                # itself; this is only reached if something escapes that net.
                return 510
    finally:
        sys.argv = saved_argv
    return obj.resultjson.get("status", {}).get("code")


def _write_trf(trf_text):
    with open(_scratch("trf"), "w", encoding="latin1") as handle:
        handle.write(trf_text)


def pairing_status(trf_text):
    _write_trf(trf_text)
    return _drive(pairingchecker, [])


def tiebreak_status(trf_text):
    _write_trf(trf_text)
    return _drive(tiebreakchecker, [])


def engine_accepts(trf_text):
    """Return the combined pairing and standings identity verdict."""
    return pairing_status(trf_text) == 0 and tiebreak_status(trf_text) == 0


def want_full():
    """Whether to run the whole corpus (set TIEBREAK_CORPUS_FULL=1) or a fast
    deterministic sample. CI sets the variable and runs the whole corpus; unset,
    the sample is the default, for quick local runs."""
    return os.environ.get("TIEBREAK_CORPUS_FULL", "") not in ("", "0", "false", "no", "off")


def load_corpus(full=None):
    if full is None:
        full = want_full()
    records = []
    with gzip.open(CORPUS_GZ, "rt", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    if full:
        selected = records
    else:
        stride = max(1, len(records) // SAMPLE_SIZE)
        selected = records[::stride]
    return _shard(selected)


def _shard(records):
    """Split the records across parallel CI runners. Set TIEBREAK_CORPUS_SHARDS to
    the number of shards and TIEBREAK_CORPUS_SHARD to this runner's index (0-based);
    a round-robin split keeps each shard's mix of categories even. Unset (the local
    default) means no split."""
    count = os.environ.get("TIEBREAK_CORPUS_SHARDS")
    index = os.environ.get("TIEBREAK_CORPUS_SHARD")
    if not count or index is None:
        return records
    total, this = int(count), int(index)
    if total <= 1:
        return records
    return [record for position, record in enumerate(records) if position % total == this]


def _read_failure_groups(path):
    grouped = json.loads(path.read_text(encoding="utf-8"))
    name_to_reason = {}
    for reason, names in grouped.items():
        for name in names:
            if name in name_to_reason:
                raise ValueError("%s lists %s more than once" % (path, name))
            name_to_reason[name] = reason
    return name_to_reason


def load_known_failures(exclude_overlays=()):
    """Return {record name: reason} for records the current engine is known to
    get wrong. The common baseline is grouped by reason in
    known_failures.json; optional features add independently owned overlays."""
    name_to_reason = _read_failure_groups(KNOWN_FAILURES) if KNOWN_FAILURES.exists() else {}
    excluded = set(exclude_overlays)
    if not KNOWN_FAILURE_OVERLAYS.exists():
        return name_to_reason
    for path in sorted(KNOWN_FAILURE_OVERLAYS.glob("*.json")):
        if path.stem in excluded:
            continue
        overlay = json.loads(path.read_text(encoding="utf-8"))
        for name in overlay.get("remove", []):
            name_to_reason.pop(name, None)
        added = overlay.get("add", {})
        seen = set()
        for reason, names in added.items():
            for name in names:
                if name in seen:
                    raise ValueError("%s adds %s more than once" % (path, name))
                seen.add(name)
                name_to_reason[name] = reason
    return name_to_reason
