# Tie-break expectations and record-299 corpus cleanup

Some corpus fixtures carried a record 299 that their pairings and standings
did not reflect. Those files could exercise the reader, but they were not
internally consistent end-to-end fixtures: applying their score adjustment
would make some later pairings and ranks stale. This branch removes that
record from the 299 affected fixtures. Focused tests retain coverage of the
supported record-299 forms.

The updated records are stored in `fixture_overlays/02-tiebreak.jsonl.gz`,
which the harness applies on top of the shared `corpus.jsonl.gz`. Fifty-two
of them are team fixtures that the C.04.6 overlay also updates; that overlay
sorts later, so its versions are used when both are present.

The one-sided-result and abnormal-score changes, together with that cleanup,
remove the obsolete tie-break fault and disagreement groups from the baseline.
Three team fixtures still disagree for reasons independent of record 299; the
overlay reclassifies them by the checker result that remains after removal.

The overlay deliberately contains only this branch's delta. Counts for the
effective set are derived by the harness after all installed overlays are
composed.

ACC/X now adds the virtual game points of record 250 to the secondary score
of a match-point team tournament. In the Baku team fixtures record 250 gives
0.0 virtual game points, so where an accelerated team and a team outside the
acceleration are level on match points, art. 4.2.2 decides the first team
on game points alone. That agrees with the declared colours of 32 fixtures
listed as refusing the prescribed pairing. It disagrees with 10 others,
whose declared colours count half the accelerated team's virtual match
points as game points; they are listed under "the engine refuses the
prescribed pairing: virtual game points of record 250".
