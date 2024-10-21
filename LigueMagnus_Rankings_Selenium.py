from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import csv
import time
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def scrape_standings(driver, wait):
    standings_div = wait.until(EC.presence_of_element_located((By.CLASS_NAME, "clearfix")))
    rows = standings_div.find_elements(By.CSS_SELECTOR, "tr")

    standings = []
    for row in rows[1:]:  # Skip header row
        cols = row.find_elements(By.TAG_NAME, "td")
        if len(cols) >= 10:
            standings.append({
                'rank': cols[0].text,
                'team': cols[1].text,
                'points': cols[3].text,
                'games_played': cols[4].text,
                'wins': cols[5].text,
                'overtime_wins': cols[6].text,
                'overtime_losses': cols[7].text,
                'losses': cols[8].text,
                'goals_for': cols[9].text,
                'goals_againts': cols[10].text,
                'penalty_minutes': cols[11].text
            })

    return standings


# Set up webdriver
standings_url = "https://liguemagnus.com/saison-reguliere/classement/?phase=432"
path = r'C:\WebDrivers\chromedriver-win64\chromedriver.exe'
service = Service(executable_path=path)

# Set up Chrome options for headless execution
chrome_options = Options()
chrome_options.add_argument("--headless")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")

# Set up webdriver using webdriver_manager
service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=chrome_options)
wait = WebDriverWait(driver, 20)

# Scrape standings data
driver.get(standings_url)
logger.info(f"Scraping standings data from: {standings_url}")
standings = scrape_standings(driver, wait)

# Write standings data to CSV
with open('ligue_magnus_rankings.csv', 'w', newline='', encoding='utf-8') as csvfile:
    fieldnames = ['rank', 'team', 'points', 'games_played', 'wins', 'overtime_wins', 'overtime_losses', 'losses',
                  'goals_for', 'goals_againts', 'penalty_minutes']
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
    writer.writeheader()
    for team in standings:
        writer.writerow(team)

logger.info("Standings data has been written to 'ligue_magnus_standings.csv'")

# Keep the browser open for 30 seconds
time.sleep(30)

driver.quit()
