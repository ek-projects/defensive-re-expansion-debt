from defensive_recovery.competition import (
    OFFICIAL_DYNAMIC_EVENT_MATCH_IDS,
    OFFICIAL_DYNAMIC_EVENT_MATCH_ID_SET,
)


def test_official_dynamic_event_scope_is_frozen():
    expected = {
        1886347, 1899585, 1925299, 1953632, 1996435,
        2006229, 2011166, 2013725, 2015213, 2017461,
    }
    assert len(OFFICIAL_DYNAMIC_EVENT_MATCH_IDS) == 10
    assert len(set(OFFICIAL_DYNAMIC_EVENT_MATCH_IDS)) == 10
    assert OFFICIAL_DYNAMIC_EVENT_MATCH_ID_SET == expected
