#!/usr/bin/env python3
import argparse
import os
import random
import re
from typing import Generator

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models.models import (
    create_bye_match,
    get_or_create_event,
    get_or_create_match,
    parse_date,
)

BASE_URL = "https://www.nrl.com"
DEFAULT_YEAR = "2025"

# --- Database Setup ---
DATABASE_URL = (
    f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}"
    f"@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
)
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)

# --- Browser Setup ---
def create_driver() -> webdriver.Chrome:
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument(f'--user-data-dir=/tmp/chrome-user-data-{random.randint(1000,9999)}')
    options.binary_location = "/usr/bin/chromium"
    return webdriver.Chrome(options=options)


# --- Parsing Helpers ---
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


def process_match_page(session, driver: webdriver, url: str) -> None:
    print(f"Visiting match URL: {url}")
    driver.get(f"{BASE_URL}/{url}")
    year = re.search(r'/(\d{4})/', url).group(1)
    soup = BeautifulSoup(driver.page_source, "html.parser")
    for match_div in soup.find_all("div", class_="match"):
        data = extract_match_data(match_div, year)
        match = get_or_create_match(session, data)
        if len(match.events) > 0:
            print(f"Match {match.id} already has events, skipping event scraping.")
            continue
        print(f"Processing match events for match ID: {match.id}")
        try:
            # wait random time between 0 and 6 seconds to avoid being blocked
            play_by_play_tab = WebDriverWait(driver, random.randint(0, 6)).until(
                EC.element_to_be_clickable((By.XPATH, "//a[.//span[text()='Play by Play']]"))
            )
            play_by_play_tab.click()
            soup = BeautifulSoup(driver.page_source, "html.parser")
            for event_soup in soup.find_all("div", class_="match-centre-event__content"):
                for parsed in extract_event_data(event_soup):
                    if parsed:
                        get_or_create_event(session, match.id, parsed)
        except Exception as e:
            print("Error processing events:", e)



def scrape_round(session, round_number: int, year: int = DEFAULT_YEAR, competition_id: int = 111) -> None:
    driver = create_driver()
    print(f"\n========== Round {round_number} ==========")
    driver.get(f"{BASE_URL}/draw/?competition={competition_id}&round={round_number}&season={year}")
    soup = BeautifulSoup(driver.page_source, "html.parser")
    # Work out teams with a bye this round
    byes = soup.find_all("div", class_="o-shadowed-box u-spacing-mv-16 u-text-align-center")
    bye_teams = extract_bye_teams(str(byes))
    for team in bye_teams:
        create_bye_match(session, team, round_number)
    print(f"Bye teams for Round {round_number}: {bye_teams}")
    # Get all matches for the round
    matches = soup.find_all("a", class_="match--highlighted u-flex-column u-flex-align-items-center u-width-100")
    for match in matches:
        path = match.get("href")
        if path:
            process_match_page(session, driver, path)
    driver.quit()


parser = argparse.ArgumentParser(    
    description="Scrape NRL match data for a given year and round."
)
parser.add_argument(
    "--year",
    type=int,
    required=True,
    help="Year to scrape data for (default: 2025)"
)
parser.add_argument(
    "--comp",
    type=int,
    default=111,
    help="The ID of the competition to scrape (default: 111 for NRL)"
)
parser.add_argument(
    "--start-round",
    type=int,
    default=1,
    help="The round number to start scraping from (default: 1)"
)

def determine_latest_round(year: int, competition_id: int) -> int:
    """Finds the latest round number of completed matches for a given year / competition."""
    # if round is not included the browser redirects to the latest round
    driver.get(f"{BASE_URL}/draw/?competition={competition_id}&season={year}")
    final_url = driver.current_url
    round_match = re.search(r"round=(\d+)", final_url)
    last_round = int(round_match.group(1))
    print(f"Latest round for {year} is {last_round}")
    return last_round

# --- Entrypoint ---
if __name__ == "__main__":
    # Create a new session
    competition_id = parser.parse_args().comp
    year = parser.parse_args().year
    start_round = parser.parse_args().start_round
    print(f"""Starting NRL data scraping for
          \nyear: {year},
          \ncompetition: {competition_id},
          \nstarting round: {start_round}""")
    driver = create_driver()
    with Session() as session:

        for round in range(start_round, determine_latest_round(year, competition_id)):
            scrape_round(
                session=Session(),
                round_number=round,
                year=year,
                competition_id=competition_id
            )
