# FIDE pairing and tie-break conformance corpus

This directory contains complete, self-contained tournament fixtures for testing
FIDE Dutch individual pairing (C.04.3), FIDE Swiss team pairing (C.04.6), and
C.07 tie-break calculations.

## Files

```
tests/corpus/
  corpus.jsonl.gz            gzip-compressed JSON Lines fixture data
  known_failures.json        baseline expected failures, grouped by reason
  known_failure_overlays/    feature-owned expectation deltas
  _harness.py                corpus loader and in-process checker driver
  test_corpus.py             pytest entry point
  regen_known_failures.py    expectation regeneration tool
```

## Corpus contents

The corpus contains 6,000 TRF-2026 tournaments:

| category | valid | invalid | total |
|----------|------:|--------:|------:|
| Individual | 4,281 | 719 | 5,000 |
| Team | 682 | 318 | 1,000 |
| **Total** | **4,963** | **1,037** | **6,000** |

Each decompressed line is one JSON object:

```json
{"name": "ind_00000", "category": "individual", "valid": true,
 "skip": false, "skip_reason": null, "trf": "062 45\n072 45\n001 ..."}
```

| field | type | meaning |
|-------|------|---------|
| `name` | string | unique fixture identifier and pytest test id |
| `category` | string | `"individual"` or `"team"` |
| `valid` | bool | expected checker verdict |
| `skip` | bool | whether the fixture is excluded from the run |
| `skip_reason` | string or null | reason for an exclusion |
| `trf` | string | complete TRF-2026 file text |

No current fixture is skipped. The `skip` fields remain part of the format so a
consumer can stage future additions when necessary.

The fixtures cover field and team sizes, board and round counts, draws,
forfeits, byes, Baku acceleration, prohibited pairings (record 260), Type A and
Type B team colour models, match-point and game-point primary scoring (record
192), and the individual and team tie-break catalogues (record 212).

### What the fixtures do not cover

No fixture carries these records. Unit tests under `tests/` cover them instead.

| record | what it decides |
|--------|-----------------|
| 162 | the game score system |
| 202 | the tie-breaks used to break a tie in the standings |
| 240 | half-point and full-point byes |
| 300 | out-of-order pairings, which set board order |
| 320 | pairing-allocated byes of a team event |
| 330 | forfeited team matches |
| 362 | the team match-point score system |
| XXZ | competitors who will not meet |

Record 260 appears in individual fixtures only. Eight result codes appear in no
fixture: `W`, `D` and `L` (an unrated played result), `X` and `?` (which score
as "A"), `F`, `A`, and a blank. The "A" points class is therefore not scored end
to end by any fixture.

## Verdict semantics

`valid` is an identity verdict, not a general quality score. A fixture is valid
when every declared pairing agrees board-for-board and colour-for-colour with
the pairing prescribed by the engine, and every declared rank agrees with the
ranking calculated from its declared tie-breaks. An invalid fixture deviates
from at least one of those prescribed results.

TRF records the declared ranking but does not carry golden numeric tie-break
values. The corpus therefore detects a tie-break calculation error when it
changes that ranking; it cannot detect an incorrect intermediate value that
leaves the final order unchanged. The reader separately checks that declared
score totals reconcile with the recorded results and score system.

Most invalid fixtures depart from the prescribed pairing or ranking in one
respect, and the name records which:

| mechanism | category | difference |
|-----------|----------|--------|
| `c1` | individual | repeat pairing |
| `c2` | individual | second pairing-allocated bye for an ineligible player |
| `c3` | individual | pairing of two players with the same absolute colour preference |
| `team_colour` | team | reversed board colours in one match |
| `team_opponent` | team | cross-swapped opponents in two matches |
| `team_rank` | team | swapped final ranks for two teams |

Invalid fixtures are parseable and internally consistent; the intended failure
is the mismatch with the prescribed pairing or ranking.

Eighteen team fixtures are invalid for a different reason and carry no such
suffix: they declare a round in which more than one team has no opponent, where
C.04.6 art. 1.4 allows one pairing-allocated bye. There is no pairing to compare
them against, so the engine reports the round rather than ranking it.

## Running the tests

The harness writes each embedded `trf` value to a temporary file and drives the
same `common_main` pipeline as `pairingchecker.py` and `tiebreakchecker.py`. It
checks that the tie-break path does not fault and that the combined pairing and
standings identity verdict agrees with `valid`.

By default pytest selects a deterministic sample of about 500 records:

```bash
pytest tests/corpus/ -n auto
```

Set `TIEBREAK_CORPUS_FULL=1` to run all records:

```bash
TIEBREAK_CORPUS_FULL=1 pytest tests/corpus/ -n auto
```

CI runs the complete corpus in round-robin shards. `TIEBREAK_CORPUS_SHARDS`
sets the number of shards and `TIEBREAK_CORPUS_SHARD` selects the zero-based
shard index. Once every runner finishes, CI posts or updates one pull-request
comment with the combined results; the same report remains available on the
workflow run's summary page.

Fixtures in the composed known-failure data run under strict `xfail` markers. A
fixed disagreement therefore becomes an XPASS and fails the suite until its
expectation is removed. `known_failures.json` is the common baseline. Each
optional feature owns a separate JSON overlay with `remove` names and `add`
groups, so independent changes never regenerate or rewrite a shared snapshot.
Overlays are applied in filename order; each operation names a fixture, making
the effective set deterministic and reviewable.

Feature-specific rationale lives beside the overlays in
`known_failure_overlays/*.md`. Aggregate counts are intentionally not copied
into this README; derive the current totals from the composed data:

```bash
PYTHONPATH=tests/corpus python3 -c 'import _harness; print(len(_harness.load_known_failures()))'
```

Regeneration refuses unclassified failures by default. Review and classify every
new disagreement rather than treating regeneration as an automatic re-baseline.
