#!/usr/bin/env python3

import argparse
from dataclasses import dataclass

from tqdm import tqdm

from utils.db import create_db_session
from utils.scrape import ScrapeConfig, create_driver, determine_latest_round, scrape_round


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Scrape NRL match data for a given year and round.")
    parser.add_argument("--year", type=int, required=True, help="Year to scrape data for (e.g. 2025)")
    parser.add_argument("--comp", type=int, default=111, help="Competition ID to scrape (default: 111 for NRL)")
    parser.add_argument("--start-round", type=int, default=1, help="Round number to start from (default: 1)")
    return parser.parse_args()


@dataclass
class ScrapeArgs:
    year: int
    comp: int
    start_round: int


def main() -> None:
    args = parse_args()
    print(
        f"Starting NRL data scraping for:\n"
        f"  Year: {args.year}\n"
        f"  Competition ID: {args.comp}\n"
        f"  Starting Round: {args.start_round}"
    )

    config = ScrapeConfig(
        session=create_db_session()(),
        driver=create_driver(),
        year=args.year,
        competition_id=args.comp,
    )

    try:
        latest_round = determine_latest_round(config)
        for round_number in tqdm(range(args.start_round, latest_round)):
            scrape_round(config=config, round_number=round_number)
    finally:
        config.driver.quit()

    print("Scraping completed.")


if __name__ == "__main__":
    main()
