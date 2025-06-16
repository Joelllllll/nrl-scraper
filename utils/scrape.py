import random
import re

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from models.models import create_bye_match, get_or_create_event, get_or_create_match
from utils.parse import (
    extract_bye_teams,
    extract_event_data,
    extract_match_data,
)

BASE_URL = "https://www.nrl.com"
DEFAULT_YEAR = "2025"

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


def scrape_round(session, driver, round_number: int, year: int = DEFAULT_YEAR, competition_id: int = 111) -> None:
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


def determine_latest_round(driver, year: int, competition_id: int) -> int:
    """Finds the latest round number of completed matches for a given year / competition."""
    # if round is not included the browser redirects to the latest round
    driver.get(f"{BASE_URL}/draw/?competition={competition_id}&season={year}")
    final_url = driver.current_url
    round_match = re.search(r"round=(\d+)", final_url)
    last_round = int(round_match.group(1))
    print(f"Latest round for {year} is {last_round}")
    return last_round
