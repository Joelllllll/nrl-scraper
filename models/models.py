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
