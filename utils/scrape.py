import random
import re
from dataclasses import dataclass

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from sqlalchemy.orm import Session as OrmSession

from utils.db import create_bye_match, get_or_create_event, get_or_create_match
from utils.parse import (
    extract_bye_teams,
    extract_event_data,
    extract_match_data,
)

BASE_URL = "https://www.nrl.com"
DEFAULT_YEAR = "2025"
DEFAULT_COMP = 111  # NRL competition ID

@dataclass
class ScrapeConfig:
    session: OrmSession
    driver: webdriver
    year: int = DEFAULT_YEAR
    competition_id: int = DEFAULT_COMP

def create_driver() -> webdriver.Chrome:
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument(f"--user-data-dir=/tmp/chrome-user-data-{random.randint(1000, 9999)}")
    options.binary_location = "/usr/bin/chromium"
    return webdriver.Chrome(options=options)

def process_match_page(session: OrmSession, driver: webdriver, url: str) -> None:
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


def scrape_round(config: ScrapeConfig, round_number: int) -> None:
    print(f"\n========== Round {round_number} ==========")
    config.driver.get(f"{BASE_URL}/draw/?competition={config.competition_id}&round={round_number}&season={config.year}")
    soup = BeautifulSoup(config.driver.page_source, "html.parser")
    # Work out teams with a bye this round
    byes = soup.find_all("div", class_="o-shadowed-box u-spacing-mv-16 u-text-align-center")
    bye_teams = extract_bye_teams(str(byes))
    for team in bye_teams:
        create_bye_match(config.session, team, round_number)
    print(f"Bye teams for Round {round_number}: {bye_teams}")
    # Get all matches for the round
    matches = soup.find_all("a", class_="match--highlighted u-flex-column u-flex-align-items-center u-width-100")
    for match in matches:
        path = match.get("href")
        if path:
            process_match_page(config.session, config.driver, path)


def determine_latest_round(config: ScrapeConfig) -> int:
    """Finds the latest round number of completed matches for a given year / competition."""
    # if round is not included the browser redirects to the latest round
    config.driver.get(f"{BASE_URL}/draw/?competition={config.competition_id}&season={config.year}")
    final_url = config.driver.current_url
    round_match = re.search(r"round=(\d+)", final_url)
    last_round = int(round_match.group(1))
    print(f"Latest round for {config.year} is {last_round}")
    return last_round
