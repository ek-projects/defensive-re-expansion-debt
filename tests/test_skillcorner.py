import json
from defensive_recovery.skillcorner import load_match_context, defending_team, defensive_shape


def test_skillcorner_mapping_and_shape(tmp_path):
    meta = {
        "id": 1,
        "home_team": {"id": 10},
        "away_team": {"id": 20},
        "pitch_length": 105,
        "pitch_width": 68,
        "players": [],
    }
    for i in range(1, 9):
        meta["players"].append({"id": i, "team_id": 10, "player_role": {"position_group": "Central Midfielder"}})
    meta["players"].append({"id": 9, "team_id": 10, "player_role": {"position_group": "Goalkeeper"}})
    for i in range(11, 19):
        meta["players"].append({"id": i, "team_id": 20, "player_role": {"position_group": "Central Midfielder"}})
    meta["players"].append({"id": 19, "team_id": 20, "player_role": {"position_group": "Goalkeeper"}})
    path = tmp_path / "match.json"
    path.write_text(json.dumps(meta))
    ctx = load_match_context(path)

    frame = {"possession": {"group": "home team"}, "player_data": []}
    for j, pid in enumerate(range(11, 19)):
        frame["player_data"].append({"player_id": pid, "x": 10 + j, "y": -10 + 3*j})
    frame["player_data"].append({"player_id": 19, "x": 45, "y": 0})

    assert defending_team(frame, ctx) == 20
    shape = defensive_shape(frame, ctx)
    assert shape is not None
    assert shape.length > 0
    assert shape.width > 0
