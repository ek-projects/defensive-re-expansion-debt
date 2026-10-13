from __future__ import annotations

# Analytics Cup 2.0 football matches with Game Intelligence Dynamic Events.
# These IDs define the primary labelled evaluation set used in the submission.
OFFICIAL_DYNAMIC_EVENT_MATCH_IDS: tuple[int, ...] = (
    1886347,
    1899585,
    1925299,
    1953632,
    1996435,
    2006229,
    2011166,
    2013725,
    2015213,
    2017461,
)

OFFICIAL_DYNAMIC_EVENT_MATCH_ID_SET = frozenset(OFFICIAL_DYNAMIC_EVENT_MATCH_IDS)
