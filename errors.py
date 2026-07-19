# -*- coding: utf-8 -*-
"""
Exceptions raised by the Gacrux engine.

The engine is embedded and it is served over HTTP, so a fault has to arrive at the
caller as an exception it can act on. A caller has to be able to tell three different
things apart, and they are not variations of the same thing:

GacruxNoLegalPairing is a state of the tournament, not a defect of the engine.
    The rules do not guarantee that a field can be paired. Once the competitors have
    met each other often enough there is no assignment left that satisfies the absolute
    criteria, and FIDE C.04.3 says so itself: article 1.9.3 covers the case where a
    pairing cannot be completed and describes what the arbiter does about it -- pair as
    many competitors as can be paired and give a bye to the rest. A small field whose
    round robin is exhausted reaches this in a completely ordinary way, on input that is
    valid in every respect.

    The engine cannot make that decision on the caller's behalf: which competitors are
    left out is a decision of the arbiter, and it is taken outside the pairing rules. So
    the engine reports the state and stops. A caller that pairs a small tournament is
    expected to catch this exception -- not to log it as a crash.

GacruxInputError means the tournament that was handed to the engine is malformed.
    A record does not carry the data it must carry, or the records contradict each
    other. The reader will normally have recorded a status code for it as well; the
    exception exists so the failure is not silent when nobody looks at the status.

GacruxInvariantError means an internal consistency check of the engine failed.
    This is a bug in the engine. It is raised where the code has established something
    about its own state and then finds it does not hold. If one of these escapes, the
    pairing that was being computed is not to be trusted.

All of them derive from GacruxError, so a caller that only wants to know whether the
engine failed at all can catch that one.
"""


class GacruxError(RuntimeError):
    """Base class of every error raised by the engine."""


class GacruxNoLegalPairing(GacruxError):
    """No admissible pairing exists for this field or score bracket.

    A state of the tournament, not a defect: see FIDE C.04.3, article 1.9.3.
    """


class GacruxInputError(GacruxError):
    """The tournament handed to the engine is malformed or self-contradictory."""


class GacruxInvariantError(GacruxError):
    """An internal consistency check of the engine failed -- a bug in the engine."""
