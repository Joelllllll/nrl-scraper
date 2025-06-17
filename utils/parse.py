import re
from datetime import datetime
from typing import Generator

from bs4 import BeautifulSoup


def parse_date(date_str: str, year: int) -> datetime:
    "Parses a date string in the format 'Day DD Month YYYY' and returns a datetime object."
    clean_str = re.sub(r'(\d{1,2})(st|nd|rd|th)', r'\1', date_str + " " + year)
    return datetime.strptime(clean_str, "%A %d %B %Y")

def parse_game_time_to_seconds(time_str: str) -> int:
    "Takes in game time in 'MM:SS' format and converts it to seconds."
    try:
        minutes, seconds = map(int, time_str.strip().split(":"))
        return minutes * 60 + seconds
    except Exception as e:
        print(f"Error parsing time '{time_str}': {e}")
        return 0


def extract_bye_teams(html: str) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    bye_teams = set()

    for span in soup.select("li.match-bye-team span.u-visually-hidden"):
        team_name = span.get_text(strip=True)
        if team_name:
            bye_teams.add(team_name)

    return list(bye_teams)


def extract_match_data(match_div: BeautifulSoup, year: int) -> dict:
    "Extracts match data from a BeautifulSoup match div."
    date_tag = match_div.find("p", class_="match-header__title")
    date = parse_date(date_tag.get_text(strip=True).split(" - ")[1], year)

    round_num = int(
        (date_tag.get_text(strip=True).split(" - ")[0]).split("Round ")[-1].strip()
    )

    home_name = match_div.find("p", class_="match-team__name--home").get_text(strip=True)
    away_name = match_div.find("p", class_="match-team__name--away").get_text(strip=True)
    home_score = int(match_div.find("div", class_="match-team__score--home").find(string=True, recursive=False).strip())
    away_score = int(match_div.find("div", class_="match-team__score--away").find(string=True, recursive=False).strip())

    venue_tag = match_div.find("p", class_="match-venue o-text")
    venue = venue_tag.get_text(strip=True).replace("Venue:", "").strip() if venue_tag else None

    ground_conditions = weather = attendance = None
    weather_div = match_div.find("div", class_="match-weather")
    if weather_div:
        for p in weather_div.find_all("p", class_="match-weather__text"):
            text = p.get_text(strip=True)
            if "Ground Conditions:" in text:
                ground_conditions = p.find("span").get_text(strip=True)
            elif "Weather:" in text:
                weather = p.find("span").get_text(strip=True)
            elif "Attendance:" in text:
                attendance = p.find("span").get_text(strip=True)

    return {
        "date": date,
        "round": round_num,
        "home_name": home_name,
        "away_name": away_name,
        "home_score": home_score,
        "away_score": away_score,
        "venue": venue,
        "ground_conditions": ground_conditions,
        "weather": weather,
        "attendance": attendance
    }


def extract_event_data(event) -> Generator[dict, None, None]:
    try:
        timestamp = event.find("span", class_="match-centre-event__timestamp").get_text(strip=True)
        title = event.find("h4", class_="match-centre-event__title").get_text(strip=True)
        summary = event.find("div", class_="match-centre-event__summary")

        team_tag = summary.find("p", class_="match-centre-event__team-name") if summary else None
        player_tag = summary.find("p", class_="u-font-weight-500") if summary else None
        ul = summary.find("ul") if summary else None

        players = []
        if ul:
            for li in ul.find_all("li"):
                role = li.find("span").get_text(strip=True)
                name = li.get_text(strip=True).replace(role, "").strip()
                players.append({"role": role, "name": name})

                yield {
                    "timestamp": timestamp,
                    "title": title,
                    "team_name": team_tag.get_text(strip=True) if team_tag else None,
                    "player": name,
                    "role": role
                }
        else:
                yield {
                    "timestamp": timestamp,
                    "title": title,
                    "team_name": team_tag.get_text(strip=True) if team_tag else None,
                    "player": player_tag.get_text(strip=True) if player_tag else None,
                    "role": None
                }
    except Exception as e:
        print("Failed to parse event:", e)
        return None
