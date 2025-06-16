# nrl-scraper
Scrape the National Rugby League site nrl.com for match data

## Features

- Scrape NRL match info: teams, scores, players, match results, weather, attendance, etc.
- Extract detailed play-by-play events with timestamps and player info.
- Handles bye rounds.
- Uses Selenium with headless Chromium for browser automation.
- Saves data using SQLAlchemy ORM into PostgreSQL.

## Usage

1. Clone repo
```bash
git clone https://github.com/your-username/nrl-scraper.git
cd nrl-scraper
```
2. Build image and bring up containers
```bash
docker-compose  build
docker-compose  up
```
This will create a PostgreSQL 15 Alpine database and start the scraper app

3. Start script with args (inside container)
```bash
docker exec -it nrl_scraper bash
./main.py --year 2025 --comp 111 --start-round 3
```
The script will start at a given round (default 1) and consume all match data up until the current round
If previous year it will consume everything
