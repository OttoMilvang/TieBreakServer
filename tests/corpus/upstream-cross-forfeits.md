# Cross-forfeited team draws

Upstream commit c9d84ab counts a match as played when both teams score game
points, including a match whose boards all end by forfeit. The corpus previously
built the following fixtures without counting those matches in the played-match
and colour histories:

- `team_0142`: round 2, teams 8 and 2, opposite forfeit winners on the two boards.
  Including that drawn match changes prescribed colours in rounds 3 and 6 and
  prescribed opponents in round 4.
- `team_0172`: round 7, teams 11 and 10, opposite forfeit winners on the two boards.
  Including that drawn match changes the round 8 bye, opponents and colours.

Their original TRF records are retained. Both fixtures are now labelled invalid
because their later declared pairings differ from the current upstream engine.
This records upstream's changed cross-forfeit interpretation; it does not resolve
how an all-forfeit draw should be classified under C.04.6.

`team_0256` remains invalid. Under the same upstream change its declared round 5
pairing is correctly rejected, so its obsolete expected-failure entry is removed.
