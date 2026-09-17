# Tie-break expectations and record-299 corpus cleanup

Record 299 was injected into generated tournaments after their pairings and
standings had already been produced. The resulting files could exercise the
reader, but they were not internally consistent end-to-end fixtures: applying
their score adjustment would necessarily make some later pairings and ranks
stale. This branch removes those injected records from the generated corpus.
Focused tests retain coverage of the supported record-299 forms.

The one-sided-result and abnormal-score fixes, together with that cleanup,
remove the obsolete tie-break fault and disagreement groups from the baseline.
Four team fixtures still disagree for reasons independent of record 299; the
overlay reclassifies them by the checker result that remains after removal.

The overlay deliberately contains only this branch's delta. Counts for the
effective set are derived by the harness after all installed overlays are
composed.
