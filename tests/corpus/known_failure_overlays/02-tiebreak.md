# Tie-break expectation changes

The one-sided-result, record-299 point adjustment, and abnormal-score fixes
remove the two tie-break fault groups from the baseline. Records that still
disagree after the checker reaches a verdict are reclassified as pairing,
standings, or combined disagreements by `02-tiebreak.json`.

The overlay deliberately contains only this branch's delta. Counts for the
effective set are derived by the harness after all installed overlays are
composed.
