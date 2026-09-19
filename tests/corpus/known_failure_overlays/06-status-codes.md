# Rounds that cannot be paired

The checker used to answer a team round with no legal pairing with a pairing of its own,
so the declared round always compared equal and the file was accepted. This branch leaves
the condition to the caller, and the round is reported with status 505 instead.

Twenty-two team records were accepted that way, each declaring a round in which more
than one team has no opponent. `fixture_overlays/00-status-codes.jsonl.gz` carries the
twenty of them this branch's corpus still marks valid, with the verdict the round gives
them, and changes nothing else about the record. Fixture overlays apply in filename
order and the last one wins, so it is numbered to sort first: a feature that replaces the
same record keeps its own version of it.

Two of the twenty, team_0347 and team_0642, are also on the record 299 list: their 299
line stops the reader before it reaches the rounds, so on this branch they are refused
for that, and the record is marked invalid to say so. A branch that removes the 299 line
replaces the record with its own version, which sorts later and decides the verdict:
team_0347 still declares such a round, team_0642 does not.

The known-failure lists those records are on describe a checker that accepts them, which
stops being true here. This file removes the names, and is numbered to sort after the
lists it clears, since overlays apply in filename order.
