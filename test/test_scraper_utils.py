from datetime import datetime
import pytest
from bs4 import BeautifulSoup
from main import (
    extract_event_data,
    extract_match_data,
    extract_bye_teams
)
from models.models import parse_game_time_to_seconds

# -- parse_game_time_to_seconds --

@pytest.mark.parametrize("input_str,expected", [
    ("52:54", 3174),
    ("00:00", 0),
    ("12:05", 725),
    ("1:59", 119),
    ("80:00", 4800),
    ("bad", 0)
])
def test_parse_game_time_to_seconds(input_str, expected):
    assert parse_game_time_to_seconds(input_str) == expected

# -- parse_event --

def test_parse_event_single_player():
    html = '''
    <div class="match-centre-event__content">
        <span class="match-centre-event__timestamp">52:54</span>
        <h4 class="match-centre-event__title">Try</h4>
        <div class="match-centre-event__summary">
            <p class="match-centre-event__team-name">Storm</p>
            <p class="u-font-weight-500">Cameron Munster</p>
        </div>
    </div>
    '''
    soup = BeautifulSoup(html, 'html.parser')
    for result in extract_event_data(soup):
        assert result["timestamp"] == "52:54"
        assert result["title"] == "Try"
        assert result["team_name"] == "Storm"
        assert result["player"] == "Cameron Munster"

def test_parse_event_multiple_players():
    html = '''
    <div class="match-centre-event__content">
        <span class="match-centre-event__timestamp">65:20</span>
        <h4 class="match-centre-event__title">Interchange #8</h4>
        <div class="match-centre-event__summary">
            <p class="match-centre-event__team-name">Panthers</p>
            <ul>
                <li><span>on</span> Nathan Cleary</li>
                <li><span>off</span> Brian To'o</li>
            </ul>
        </div>
    </div>
    '''
    soup = BeautifulSoup(html, 'html.parser')
    results = list(extract_event_data(soup))
    assert results[0]["timestamp"] == "65:20"
    assert results[0]["title"] == "Interchange #8"
    assert results[0]["team_name"] == "Panthers"
    assert results[0]["player"] == "Nathan Cleary"
    assert results[0]["role"] == "on"

    assert results[1]["timestamp"] == "65:20"
    assert results[1]["title"] == "Interchange #8"
    assert results[1]["team_name"] == "Panthers"
    assert results[1]["player"] == "Brian To'o"
    assert results[1]["role"] == "off"

def test_extract_match_data():
    html = """
    <div>
        <p class="match-header__title">Round 12 - Sunday 26 May</p>
        <p class="match-team__name--home">Panthers</p>
        <p class="match-team__name--away">Storm</p>
        <div class="match-team__score--home">18</div>
        <div class="match-team__score--away">12</div>
        <p class="match-venue o-text">Venue: BlueBet Stadium</p>
        <div class="match-weather">
            <p class="match-weather__text">Ground Conditions: <span>Good</span></p>
            <p class="match-weather__text">Weather: <span>Fine</span></p>
            <p class="match-weather__text">Attendance: <span>15,234</span></p>
        </div>
    </div>
    """
    soup = BeautifulSoup(html, "html.parser")
    match_div = soup.find("div")

    expected = {
        "date": datetime(2025, 5, 26),
        "round": 12,
        "home_name": "Panthers",
        "away_name": "Storm",
        "home_score": 18,
        "away_score": 12,
        "venue": "BlueBet Stadium",
        "ground_conditions": "Good",
        "weather": "Fine",
        "attendance": "15,234",
    }

    result = extract_match_data(match_div, "2025")
    assert result == expected


def test_extract_bye_teams_basic():
    html = """
    <ul>
        <li class="match-bye-team"><span class="u-visually-hidden">Panthers</span></li>
        <li class="match-bye-team"><span class="u-visually-hidden">Storm</span></li>
    </ul>
    """
    result = extract_bye_teams(html)
    assert result == ["Panthers", "Storm"]

def test_extract_bye_teams_empty():
    html = "<ul></ul>"
    result = extract_bye_teams(html)
    assert result == []

def test_extract_bye_teams_ignores_non_hidden_spans():
    html = """
    <ul>
        <li class="match-bye-team"><span>Visible Text</span></li>
        <li class="match-bye-team"><span class="u-visually-hidden">Cowboys</span></li>
    </ul>
    """
    result = extract_bye_teams(html)
    assert result == ["Cowboys"]

def test_extract_bye_teams_ignores_empty_spans():
    html = """
    <ul>
        <li class="match-bye-team"><span class="u-visually-hidden">   </span></li>
        <li class="match-bye-team"><span class="u-visually-hidden">Raiders</span></li>
    </ul>
    """
    result = extract_bye_teams(html)
    assert result == ["Raiders"]
