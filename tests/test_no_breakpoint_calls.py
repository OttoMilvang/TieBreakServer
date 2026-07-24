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
than the three files this commit touched -- the point of the guard is that a
breakpoint() reintroduced anywhere in the engine, not just these files, is caught.
"""
import ast
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Every module the engine ships at the repository root (excluding this test suite,
# the checked-in virtualenv, and bytecode caches -- os.listdir naturally skips those
# since it only lists ROOT itself, one level up from tests/).
ENGINE_MODULES = sorted(
    name
    for name in os.listdir(ROOT)
    if name.endswith(".py") and os.path.isfile(os.path.join(ROOT, name))
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
    with open(path, encoding="utf-8") as handle:
        source = handle.read()
    return ast.parse(source, filename=filename)


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
