#!/usr/bin/env python3

import argparse
import os
import random

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from utils.scrape import determine_latest_round, scrape_round

DATABASE_URL = (
    f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}"
    f"@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
)


def create_driver() -> webdriver.Chrome:
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument(f"--user-data-dir=/tmp/chrome-user-data-{random.randint(1000, 9999)}")
    options.binary_location = "/usr/bin/chromium"
    return webdriver.Chrome(options=options)


def create_db_session(database_url: str = DATABASE_URL) -> sessionmaker:
    engine = create_engine(database_url, echo=False)
    return sessionmaker(bind=engine)


def parse_args():
    parser = argparse.ArgumentParser(description="Scrape NRL match data for a given year and round.")
    parser.add_argument("--year", type=int, required=True, help="Year to scrape data for (e.g. 2025)")
    parser.add_argument("--comp", type=int, default=111, help="Competition ID to scrape (default: 111 for NRL)")
    parser.add_argument("--start-round", type=int, default=1, help="Round number to start from (default: 1)")
    return parser.parse_args()


def main():
    args = parse_args()
    print(
        f"Starting NRL data scraping for:\n"
        f"  Year: {args.year}\n"
        f"  Competition ID: {args.comp}\n"
        f"  Starting Round: {args.start_round}"
    )

    driver = create_driver()
    Session = create_db_session()
    
    try:
        with Session() as session:
            latest_round = determine_latest_round(driver, args.year, args.comp)
            for round_number in range(args.start_round, latest_round):
                scrape_round(
                    session=session,
                    driver=driver,
                    round_number=round_number,
                    year=args.year,
                    competition_id=args.comp,
                )
    finally:
        driver.quit()

    print("Scraping completed.")


if __name__ == "__main__":
    main()
