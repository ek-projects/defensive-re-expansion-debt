from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterator
import json
import numpy as np

from .geometry import ShapeMetrics, compute_shape_metrics


@dataclass(frozen=True)
class MatchContext:
    match_id: int
    home_team_id: int
    away_team_id: int
    pitch_length: float
    pitch_width: float
    player_team: dict[int, int]
    goalkeepers: frozenset[int]


def load_match_context(path: str | Path) -> MatchContext:
    raw = json.loads(Path(path).read_text())
    player_team: dict[int, int] = {}
    goalkeepers: set[int] = set()
    for p in raw.get("players", []):
        pid = p.get("id")
        tid = p.get("team_id")
        if pid is None or tid is None:
            continue
        player_team[int(pid)] = int(tid)
        role = (p.get("player_role") or {}).get("position_group", "")
        if str(role).strip().lower() == "goalkeeper":
            goalkeepers.add(int(pid))
    return MatchContext(
        match_id=int(raw["id"]),
        home_team_id=int(raw["home_team"]["id"]),
        away_team_id=int(raw["away_team"]["id"]),
        pitch_length=float(raw["pitch_length"]),
        pitch_width=float(raw["pitch_width"]),
        player_team=player_team,
        goalkeepers=frozenset(goalkeepers),
    )


def iter_tracking(path: str | Path) -> Iterator[dict]:
    """Stream SkillCorner JSONL tracking in constant memory."""
    with Path(path).open("r", encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                yield json.loads(line)


def team_in_possession(frame: dict, ctx: MatchContext) -> int | None:
    group = ((frame.get("possession") or {}).get("group") or "").strip().lower()
    if group == "home team":
        return ctx.home_team_id
    if group == "away team":
        return ctx.away_team_id
    return None


def defending_team(frame: dict, ctx: MatchContext) -> int | None:
    possessing = team_in_possession(frame, ctx)
    if possessing == ctx.home_team_id:
        return ctx.away_team_id
    if possessing == ctx.away_team_id:
        return ctx.home_team_id
    return None


def team_positions(
    frame: dict,
    ctx: MatchContext,
    team_id: int,
    *,
    include_goalkeeper: bool = False,
) -> np.ndarray:
    points: list[tuple[float, float]] = []
    for p in frame.get("player_data") or []:
        pid = p.get("player_id")
        if pid is None or ctx.player_team.get(int(pid)) != int(team_id):
            continue
        if not include_goalkeeper and int(pid) in ctx.goalkeepers:
            continue
        x, y = p.get("x"), p.get("y")
        if x is None or y is None:
            continue
        if np.isfinite(float(x)) and np.isfinite(float(y)):
            points.append((float(x), float(y)))
    return np.asarray(points, dtype=float).reshape((-1, 2))


def defensive_shape(frame: dict, ctx: MatchContext) -> ShapeMetrics | None:
    team_id = defending_team(frame, ctx)
    if team_id is None:
        return None
    xy = team_positions(frame, ctx, team_id, include_goalkeeper=False)
    if len(xy) < 6:
        return None
    return compute_shape_metrics(xy)
