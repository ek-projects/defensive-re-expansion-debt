from defensive_recovery.competition import (
    ANALYTICS_CUP_TRACKING_MATCH_IDS,
    ANALYTICS_CUP_TRACKING_MATCH_ID_SET,
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


def test_full_analytics_cup_tracking_scope_is_frozen_and_contains_primary():
    assert len(ANALYTICS_CUP_TRACKING_MATCH_IDS) == 20
    assert len(ANALYTICS_CUP_TRACKING_MATCH_ID_SET) == 20
    assert OFFICIAL_DYNAMIC_EVENT_MATCH_ID_SET <= ANALYTICS_CUP_TRACKING_MATCH_ID_SET
