import os
import sys
from datetime import datetime
from typing import Callable

from sqlalchemy.orm import Session as OrmSession

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest

from main import create_db_session
from utils.db import (
    get_or_create_event_role,
    get_or_create_event_type,
    get_or_create_match,
    get_or_create_player,
    get_or_create_team,
)

DATABASE_URL = (
    f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/test"
)


def make_match_data(home, away, home_score=10, away_score=12) -> dict[str, any]:
    return {
        "round": 1,
        "date": datetime(2025, 3, 2, 15, 0),
        "venue": "Suncorp Stadium",
        "home_name": home,
        "away_name": away,
        "home_score": home_score,
        "away_score": away_score,
        "attendance": "20,000",
        "ground_conditions": "Dry",
        "weather": "Sunny",
    }


@pytest.fixture(scope="function")
def session() -> Callable[[], OrmSession]:
    return create_db_session(DATABASE_URL)()


def test_get_or_create_team(session) -> None:
    team = get_or_create_team(session, "Rabbitohs")
    assert team.name == "Rabbitohs"
    team2 = get_or_create_team(session, "Rabbitohs")
    assert team.id == team2.id  # should not create duplicate


def test_get_or_create_event_type(session) -> None:
    et = get_or_create_event_type(session, "Try")
    assert et.name == "Try"


def test_get_or_create_player(session) -> None:
    player = get_or_create_player(session, "Latrell Mitchell")
    assert player.name == "Latrell Mitchell"


def test_get_or_create_event_role(session) -> None:
    role = get_or_create_event_role(session, "Try Scorer")
    assert role.role_name == "Try Scorer"


def test_creates_new_match(session) -> None:
    data = make_match_data("Storm", "Eels", 20, 18)
    match = get_or_create_match(session, data)

    assert match.id is not None
    assert match.home_team.name == "Storm"
    assert match.away_team.name == "Eels"
    assert match.score_home == 20
    assert match.score_away == 18
    assert match.attendance == 20000
    assert match.venue == "Suncorp Stadium"
    session.rollback()  # Clean up after test
