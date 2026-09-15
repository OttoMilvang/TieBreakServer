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
import importlib.util
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
