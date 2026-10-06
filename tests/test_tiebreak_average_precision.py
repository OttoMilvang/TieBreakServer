"""Average Buchholz must distinguish standings that coincide at two decimals."""
import gzip
import json
from decimal import Decimal
from pathlib import Path

from gacrux import tiebreak, trf2json


def test_eleven_round_average_buchholz_breaks_the_rounded_tie():
    corpus = Path(__file__).parent / "corpus" / "corpus.jsonl.gz"
    with gzip.open(corpus, "rt", encoding="utf-8") as handle:
        record = next(record for line in handle
                      if (record := json.loads(line))["name"] == "ind_01986")
    reader = trf2json.trf2json()
    reader.parse_file(record["trf"], True)
    tournament = reader.get_tournament(1)
    params = {"tiebreak": ["PTS", "BH", "AOB"], "check": True, "unrated": None}
    calculator = tiebreak.tiebreak(tournament, -1, params)
    standings = calculator.compute_tiebreaks(tournament, params)
    players = {player["cid"]: player for player in standings["competitors"]}

    # Both players have 6.5 points and 73.5 Buchholz. Their opponents' Buchholz
    # sums are 699.5 over ten played games and 769.5 over eleven played games.
    # Rounding both averages to 69.95 used to give both players rank 23.
    assert Decimal("699.5") / 10 < Decimal("769.5") / 11
    assert players[16]["tiebreakScore"] == [Decimal("6.5"), Decimal("73.5"), Decimal("69.950")]
    assert players[21]["tiebreakScore"] == [Decimal("6.5"), Decimal("73.5"), Decimal("69.955")]
    assert players[21]["rank"] == 23
    assert players[16]["rank"] == 24
