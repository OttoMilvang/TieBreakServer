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

import pytest

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


def _fixture_overlay(tmp_path, filename, records):
    """A fixture overlay beside the fake corpus, in the snapshot's format."""
    directory = tmp_path / "fixture_overlays"
    directory.mkdir(exist_ok=True)
    with gzip.open(directory / filename, "wt", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record) + "\n")


def _replacement(index, trf):
    return {"name": "ind_%05d" % index, "category": "individual", "valid": False,
            "skip": False, "trf": trf}


def test_fixture_overlays_replace_snapshot_records_in_filename_order(tmp_path,
                                                                     monkeypatch):
    """A feature changes fixtures through its own overlay, not the snapshot.

    ``corpus.jsonl.gz`` is compressed, so git cannot merge two branches that
    each rewrite it: whichever merges second conflicts. Each feature ships its
    changed records in ``fixture_overlays/<feature>.jsonl.gz`` instead. A record
    replaces the snapshot record of the same name in place, the others are
    untouched, and where two overlays replace the same record the one later in
    filename order wins, as with the known-failure overlays.
    """
    monkeypatch.setattr(_harness, "CORPUS_GZ", _fake_corpus(tmp_path, 4))
    monkeypatch.delenv("TIEBREAK_CORPUS_SHARDS", raising=False)
    monkeypatch.delenv("TIEBREAK_CORPUS_SHARD", raising=False)
    _fixture_overlay(tmp_path, "05-later.jsonl.gz", [_replacement(2, "later\n")])
    _fixture_overlay(tmp_path, "02-earlier.jsonl.gz",
                     [_replacement(1, "earlier\n"), _replacement(2, "earlier\n")])

    records = _harness.load_corpus(full=True)

    assert [record["name"] for record in records] == \
        ["ind_%05d" % index for index in range(4)]
    assert [record["trf"] for record in records] == \
        ["012 fake\n", "earlier\n", "later\n", "012 fake\n"]
    assert [record["valid"] for record in records] == [True, False, False, True]


def test_fixture_overlay_must_name_snapshot_records_once(tmp_path, monkeypatch):
    """An overlay only replaces: a name the snapshot lacks, or one listed twice
    in the same overlay, is an error rather than a silent addition or a silent
    choice between two versions."""
    monkeypatch.setattr(_harness, "CORPUS_GZ", _fake_corpus(tmp_path, 2))
    _fixture_overlay(tmp_path, "feature.jsonl.gz", [_replacement(7, "new\n")])
    with pytest.raises(ValueError, match="not in the corpus"):
        _harness.load_corpus(full=True)

    _fixture_overlay(tmp_path, "feature.jsonl.gz",
                     [_replacement(1, "one\n"), _replacement(1, "two\n")])
    with pytest.raises(ValueError, match="more than once"):
        _harness.load_corpus(full=True)
