import os
from typing import Callable

from sqlalchemy import create_engine
from sqlalchemy.orm import Session as OrmSession
from sqlalchemy.orm import sessionmaker

from models.models import Event, EventPlayer, EventRole, EventType, Match, Player, Team
from utils.parse import parse_game_time_to_seconds

DATABASE_URL = (
    f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}"
    f"@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
)

def create_db_session(database_url: str = DATABASE_URL) -> Callable[[], OrmSession]:
    engine = create_engine(database_url, echo=False)
    return sessionmaker(bind=engine)


def commit(session, record) -> None:
    """
    Commit the current session to the database.
    """
    try:
        session.add(record)
        session.commit()
        session.flush()
    except Exception as e:
        print(f"Error committing record {record}: {e}")
        session.rollback()


def get_or_create_event_type(session, name: str) -> EventType:
    obj = session.query(EventType).filter_by(name=name).first()
    if not obj:
        obj = EventType(name=name)
        commit(session, obj)
    return obj


def get_or_create_team(session, name: str) -> Team:
    obj = session.query(Team).filter_by(name=name).first()
    if not obj:
        obj = Team(name=name)
        commit(session, obj)
    return obj


def get_or_create_match(session, data) -> Match:
    home_team = get_or_create_team(session, data["home_name"])
    away_team = get_or_create_team(session, data["away_name"])

    existing = session.query(Match).filter_by(
        date=data["date"], home_team_id=home_team.id, away_team_id=away_team.id
    ).first()

    if existing:
        return existing

    match = Match(
        date=data["date"], venue=data["venue"],
        round=data["round"],
        home_team_id=home_team.id, away_team_id=away_team.id,
        score_home=data["home_score"], score_away=data["away_score"],
        attendance=int((data["attendance"] or "0").replace(",", "")),
        ground_conditions=data["ground_conditions"], weather=data["weather"]
    )
    commit(session, match)
    return match

def get_or_create_player(session, name: str) -> Player:
    obj = session.query(Player).filter_by(name=name).first()
    if not obj:
        obj = Player(name=name, positions=[], date_of_birth=None)
        commit(session, obj)
    return obj

def get_or_create_event_role(session, role_name: str) -> EventRole:
    obj = session.query(EventRole).filter_by(role_name=role_name).first()
    if not obj:
        obj = EventRole(role_name=role_name)
        commit(session, obj)
    return obj

def get_or_create_event(session, match_id: int, parsed_event: dict) -> Event:
    """
    Get or create an Event based on match_id, event_type, player, and timestamp.
    Inserts both Event and EventPlayer rows.
    """
    event_type = get_or_create_event_type(session, parsed_event["title"])
    team = get_or_create_team(session, parsed_event["team_name"]) if parsed_event["team_name"] else None
    player = get_or_create_player(session, parsed_event["player"]) if parsed_event["player"] else None
    game_time = parse_game_time_to_seconds(parsed_event["timestamp"])
    description = parsed_event.get("role") or parsed_event.get("players")

    # Duplicate check: adjust criteria as needed (timestamp, type, player, match)
    existing = session.query(Event).filter_by(
        match_id=match_id,
        event_type_id=event_type.id,
        game_time_sec=game_time,
        player_id=player.id if player else None,
    ).first()

    if existing:
        return existing

    event = Event(
        match_id=match_id,
        team_id=team.id if team else None,
        player_id=player.id if player else None,
        event_type_id=event_type.id,
        game_time_sec=game_time,
        description=description,
    )
    commit(session, event)

    if player:
        ep = EventPlayer(event_id=event.id, player_id=player.id, 
                         role_id=get_or_create_event_role(session, parsed_event.get("role", "")).id)
        commit(session, ep)

    return event

def create_bye_match(session, team_name: str, round_number: int) -> None:
    """Create a match for a team that has a bye in the given round."""
    team = get_or_create_team(session, team_name)
    match_exists = session.query(Match).filter_by(
        round=round_number, home_team_id=team.id, away_team_id=None
    ).first()
    if match_exists:
        print(f"Bye match already exists for {team_name} in round {round_number}.")
        return
    else:
        match = Match(
            venue="Bye",
            round=round_number,
            home_team_id=team.id
        )
        commit(session, match)
