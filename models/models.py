from sqlalchemy import (
    ARRAY,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    PrimaryKeyConstraint,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.sql import func

Base = declarative_base()

def get_or_create_event_type(session, name: str):
    obj = session.query(EventType).filter_by(name=name).first()
    if not obj:
        obj = EventType(name=name)
        session.add(obj)
        session.flush()
    return obj


def get_or_create_team(session, name: str):
    obj = session.query(Team).filter_by(name=name).first()
    if not obj:
        obj = Team(name=name)
        session.add(obj)
        session.flush()
    return obj


def get_or_create_match(session, data):
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

def get_or_create_player(session, name: str):
    obj = session.query(Player).filter_by(name=name).first()
    if not obj:
        obj = Player(name=name, positions=[], date_of_birth=None)  # minimal
        session.add(obj)
        session.flush()
    return obj

def get_or_create_event_role(session, role_name: str):
    obj = session.query(EventRole).filter_by(role_name=role_name).first()
    if not obj:
        obj = EventRole(role_name=role_name)
        session.add(obj)
        session.flush()
    return obj

def get_or_create_event(session, match_id: int, parsed_event: dict):
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

def parse_game_time_to_seconds(time_str: str) -> int:
    "Takes in game time in 'MM:SS' format and converts it to seconds."
    try:
        minutes, seconds = map(int, time_str.strip().split(":"))
        return minutes * 60 + seconds
    except Exception as e:
        print(f"Error parsing time '{time_str}': {e}")
        return 0

class Team(Base):
    __tablename__ = 'teams'
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False, unique=True)

    players = relationship('TeamMembership', back_populates='team')
    home_matches = relationship('Match', foreign_keys='Match.home_team_id', back_populates='home_team')
    away_matches = relationship('Match', foreign_keys='Match.away_team_id', back_populates='away_team')
    appearances = relationship('PlayerAppearance', back_populates='team')
    events = relationship('Event', back_populates='team')


class Player(Base):
    __tablename__ = 'players'
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    positions = Column(ARRAY(Text))
    date_of_birth = Column(Date)
    height = Column(Integer)
    weight = Column(Integer)
    birthplace = Column(String(255))
    nickname = Column(String(255))
    junior_club = Column(String(255))
    biography = Column(Text)
    debut = Column(JSONB)
    career = Column(JSONB)

    memberships = relationship('TeamMembership', back_populates='player')
    appearances = relationship('PlayerAppearance', back_populates='player')
    event_players = relationship('EventPlayer', back_populates='player')


class Match(Base):
    __tablename__ = 'matches'
    id = Column(Integer, primary_key=True)
    round = Column(Integer, nullable=False)
    date = Column(DateTime(timezone=True))
    venue = Column(String(255))
    home_team_id = Column(Integer, ForeignKey('teams.id', ondelete='CASCADE'), nullable=False)
    away_team_id = Column(Integer, ForeignKey('teams.id', ondelete='CASCADE'))
    score_home = Column(Integer)
    score_away = Column(Integer)
    attendance = Column(Integer)
    weather = Column(String(255))
    ground_conditions = Column(String(255))

    home_team = relationship('Team', foreign_keys=[home_team_id], back_populates='home_matches')
    away_team = relationship('Team', foreign_keys=[away_team_id], back_populates='away_matches')
    appearances = relationship('PlayerAppearance', back_populates='match')
    events = relationship('Event', back_populates='match')


class TeamMembership(Base):
    __tablename__ = 'team_memberships'
    id = Column(Integer, primary_key=True)
    player_id = Column(Integer, ForeignKey('players.id', ondelete='CASCADE'), nullable=False)
    team_id = Column(Integer, ForeignKey('teams.id', ondelete='CASCADE'), nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date)

    player = relationship('Player', back_populates='memberships')
    team = relationship('Team', back_populates='players')


class PlayerAppearance(Base):
    __tablename__ = 'player_appearances'
    id = Column(Integer, primary_key=True)
    player_id = Column(Integer, ForeignKey('players.id', ondelete='CASCADE'), nullable=False)
    match_id = Column(Integer, ForeignKey('matches.id', ondelete='CASCADE'), nullable=False)
    team_id = Column(Integer, ForeignKey('teams.id', ondelete='CASCADE'), nullable=False)
    jersey_number = Column(Integer)
    stats = Column(JSONB)

    player = relationship('Player', back_populates='appearances')
    match = relationship('Match', back_populates='appearances')
    team = relationship('Team', back_populates='appearances')


class EventType(Base):
    __tablename__ = 'event_types'
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False, unique=True)
    description = Column(Text)

    events = relationship('Event', back_populates='event_type')


class EventRole(Base):
    __tablename__ = 'event_roles'
    id = Column(Integer, primary_key=True)
    role_name = Column(String(50), unique=True)

    event_players = relationship('EventPlayer', back_populates='role')


class Event(Base):
    __tablename__ = 'events'

    id = Column(Integer, primary_key=True)
    match_id = Column(Integer, ForeignKey('matches.id', ondelete='CASCADE'), nullable=False)
    team_id = Column(Integer, ForeignKey('teams.id', ondelete='CASCADE'))
    event_type_id = Column(Integer, ForeignKey('event_types.id', ondelete='CASCADE'), nullable=False)
    player_id = Column(Integer, ForeignKey('players.id', ondelete='SET NULL'), nullable=True)
    game_time_sec = Column(Integer, nullable=False)
    description = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    match = relationship('Match', back_populates='events')
    team = relationship('Team', back_populates='events')
    event_type = relationship('EventType', back_populates='events')
    player = relationship('Player')  # direct link to main player
    players = relationship('EventPlayer', back_populates='event', cascade='all, delete')


class EventPlayer(Base):
    __tablename__ = 'event_players'
    event_id = Column(Integer, ForeignKey('events.id', ondelete='CASCADE'))
    player_id = Column(Integer, ForeignKey('players.id', ondelete='CASCADE'))
    role_id = Column(Integer, ForeignKey('event_roles.id', ondelete='CASCADE'), nullable=True)

    __table_args__ = (
        PrimaryKeyConstraint('event_id', 'player_id'),
    )

    event = relationship('Event', back_populates='players')
    player = relationship('Player', back_populates='event_players')
    role = relationship('EventRole', back_populates='event_players')
