# -*- coding: utf-8 -*-
"""
Guard against debug ``breakpoint()`` calls surviving in the engine's source.

pairing.py, pairingdutch.py and crosstabledutch.py used to carry several reachable
``breakpoint()`` statements -- development artifacts left in the pairing path. In a
non-interactive/server context ``breakpoint()`` drops the process into pdb on stdin
and hangs; there is no terminal to debug from and nothing left to serve the request
that triggered it.

This is not a behavioural regression a tournament fixture can exercise -- the fix is
a pure removal, and the failure mode is "the process never returns", which a normal
test can't observe without literally hanging the test run. The faithful test is a
static guard instead: walk every module the engine ships and fail if a
``breakpoint()`` call is still reachable anywhere in it. This is deliberately broader
than the files that first carried one -- the point of the guard is that a
breakpoint() reintroduced anywhere in the engine is caught.

The engine's modules live in the ``gacrux`` package. The list is built by walking
that package, and the walk is asserted to be non-empty: a guard that silently
scans nothing passes while reporting that it checked everything, which is worse
than having no guard at all.
"""
import ast
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PACKAGE = os.path.join(ROOT, "gacrux")

# Every module the engine ships, as paths relative to the repository root.
ENGINE_MODULES = sorted(
    os.path.relpath(os.path.join(dirpath, name), ROOT)
    for dirpath, _, filenames in os.walk(PACKAGE)
    for name in filenames
    if name.endswith(".py")
)


class BreakpointVisitor(ast.NodeVisitor):
    """Collect the line numbers of every reachable call to breakpoint()."""

    def __init__(self):
        self.hits = []

    def visit_Call(self, node):
        func = node.func
        if isinstance(func, ast.Name):
            name = func.id
        elif isinstance(func, ast.Attribute):
            name = func.attr
        else:
            name = None
        if name == "breakpoint":
            self.hits.append(node.lineno)
        self.generic_visit(node)


def _parse(filename):
    path = os.path.join(ROOT, filename)
    # utf-8-sig, because some of the engine's modules are saved with a
    # byte-order mark and ast.parse refuses one as a non-printable character.
    with open(path, encoding="utf-8-sig") as handle:
        source = handle.read()
    return ast.parse(source, filename=filename)


def test_the_guard_actually_finds_the_engine():
    """The module list is not empty.

    It used to be built from the ``*.py`` files directly inside the repository
    root. Once the engine moved into the ``gacrux`` package that list became
    empty, and this guard passed while scanning no source at all.
    """
    assert ENGINE_MODULES, "no engine modules found under %s" % PACKAGE
    assert os.path.join("gacrux", "trf2json.py") in ENGINE_MODULES


def test_no_breakpoint_calls_survive_anywhere_in_the_engine():
    offenders = {}
    for filename in ENGINE_MODULES:
        visitor = BreakpointVisitor()
        visitor.visit(_parse(filename))
        if visitor.hits:
            offenders[filename] = visitor.hits

    assert offenders == {}, (
        "breakpoint() is still reachable in: "
        + ", ".join(f"{name} (line {lines})" for name, lines in offenders.items())
        + " -- this hangs a non-interactive process on stdin"
    )
