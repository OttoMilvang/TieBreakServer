# -*- coding: utf-8 -*-
"""Tests for the corpus known-failure regenerator and the corpus harness.

The regenerator rewrites a checked-in file in place, which makes it a class of
its own: a bug in it does not fail a test, it changes the thing every other
test is measured against.  A known-failure file regenerated from an eighth of
the corpus looks exactly like one regenerated properly -- smaller, and nothing
says how big it should have been.

Nothing here runs the script's ``main``.  The corpus is faked, the engine is
faked, and every write goes to a temporary path; the checked-in file is only
ever read.
"""
import gzip
import importlib.util
import json
import sys
from pathlib import Path

CORPUS_DIR = Path(__file__).parents[1] / "tests" / "corpus"
if not CORPUS_DIR.is_dir():                       # running from inside tests/
    CORPUS_DIR = Path(__file__).parent / "corpus"


def _load(name, filename):
    """Import one of the regen scripts by path, under its own module name."""
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, CORPUS_DIR / filename)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


regen_known_failures = _load("regen_known_failures", "regen_known_failures.py")
_harness = _load("_harness", "_harness.py")


def test_harness_treats_nonzero_system_exit_as_failure():
    class ExitsNonzero:
        def __init__(self):
            self.resultjson = {"status": {"code": 0}}

        def common_main(self):
            raise SystemExit(2)

    assert _harness._drive(ExitsNonzero, []) == 2


def _fake_corpus(tmp_path, count, skips=None):
    """A corpus of *count* trivial records, in the real file's format."""
    path = tmp_path / "corpus.jsonl.gz"
    with gzip.open(path, "wt", encoding="utf-8") as handle:
        for index in range(count):
            handle.write(json.dumps({
                "name": "ind_%05d" % index,
                "category": "individual",
                "valid": True,
                "skip": bool(skips and index in skips),
                "trf": "012 fake\n",
            }) + "\n")
    return path


def test_known_failure_regeneration_ignores_the_ci_shard_variables(tmp_path,
                                                                   monkeypatch):
    """The regenerator reads the whole corpus even inside a sharded environment.

    ``_harness.load_corpus`` honours ``TIEBREAK_CORPUS_SHARDS`` and
    ``TIEBREAK_CORPUS_SHARD``, which is right for the test suite -- that is how
    CI splits the corpus across eight runners.  The regenerator called the same
    loader, so running it in any shell where those variables were still set
    rewrote the entire checked-in ``known_failures.json`` from one eighth of the
    records.  Every known failure outside that eighth silently disappeared from
    the file, and the test suite then reported the records as unexpected passes
    or, worse, stopped marking real failures at all.  Nothing about the result
    looked wrong; the file is a list of names with no declared length.

    This pins the separation directly: with the variables set to a 1-of-8 split,
    the loader used by the test suite returns an eighth, and the regenerator's
    own loader returns all of it.
    """
    monkeypatch.setattr(_harness, "CORPUS_GZ", _fake_corpus(tmp_path, 16))
    monkeypatch.setenv("TIEBREAK_CORPUS_SHARDS", "8")
    monkeypatch.setenv("TIEBREAK_CORPUS_SHARD", "3")

    # What the test suite sees under those variables: one shard.
    assert len(_harness.load_corpus(full=True)) == 2

    records = regen_known_failures.load_records()

    assert len(records) == 16
    assert [record["name"] for record in records] == \
        ["ind_%05d" % index for index in range(16)]


def test_known_failure_regeneration_skips_records_marked_skip(tmp_path, monkeypatch):
    """Records the corpus marks ``skip`` stay out of the regenerated baseline.

    The loader is new; this keeps the filter that was in ``main`` from being lost
    with the move, since a skipped record is not run by the test either and must
    not be listed as a known failure.
    """
    monkeypatch.setattr(_harness, "CORPUS_GZ", _fake_corpus(tmp_path, 3, skips={1}))
    monkeypatch.delenv("TIEBREAK_CORPUS_SHARDS", raising=False)
    monkeypatch.delenv("TIEBREAK_CORPUS_SHARD", raising=False)

    assert [record["name"] for record in regen_known_failures.load_records()] == \
        ["ind_00000", "ind_00002"]

def test_known_failures_has_no_unclassified_entries():
    """The committed baseline never carries an UNCLASSIFIED reason.

    UNCLASSIFIED means "the engine fails this record and nobody has said why
    yet" -- a placeholder, not a verdict. Committing one lets a failure sit in
    the tree indefinitely with nothing to show it was never triaged. This
    reads the real, checked-in ``known_failures.json`` (not a fake) and
    checks its reasons directly, so a regeneration that slipped one past
    review is caught here rather than only by whoever next reads the diff.
    """
    known_failures = json.loads(
        (CORPUS_DIR / "known_failures.json").read_text(encoding="utf-8")
    )
    assert regen_known_failures.UNCLASSIFIED not in known_failures


def test_has_unclassified_without_permission_refuses_by_default():
    """An UNCLASSIFIED group blocks a write unless explicitly allowed.

    ``main`` used to write ``known_failures.json`` unconditionally and only
    print a reminder when it left an UNCLASSIFIED group behind, so a
    regeneration run without review committed an unreviewed failure exactly
    as easily as a reviewed one. This pins the decision function ``main``
    now consults before writing: with an UNCLASSIFIED group present it
    refuses unless the caller passed permission, and it never refuses when
    there is nothing unclassified to begin with.
    """
    has_unclassified = {"some other reason": ["ind_00001"],
                        regen_known_failures.UNCLASSIFIED: ["ind_00002"]}
    all_classified = {"some other reason": ["ind_00001"]}

    assert regen_known_failures._has_unclassified_without_permission(
        has_unclassified, allow_unclassified=False) is True
    assert regen_known_failures._has_unclassified_without_permission(
        has_unclassified, allow_unclassified=True) is False
    assert regen_known_failures._has_unclassified_without_permission(
        all_classified, allow_unclassified=False) is False
    assert regen_known_failures._has_unclassified_without_permission(
        all_classified, allow_unclassified=True) is False


def test_allow_unclassified_flag_defaults_to_false():
    assert regen_known_failures.parse_args([]).allow_unclassified is False
    assert regen_known_failures.parse_args(["--allow-unclassified"]).allow_unclassified is True
