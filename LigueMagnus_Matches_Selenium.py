
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import logging
import csv
from datetime import datetime
import re

def determine_leg(journee):
    return "First Leg" if int(journee) <= 22 else "Second Leg"

def determine_win_type(score):
    if "PRL" in score or "TAB" in score:
        return "Extra Time"
    elif "-" in score:
        return "Regular Time"
    return ""

def extract_score(score_text):
    match = re.search(r'(\d+\s*-\s*\d+)', score_text)
    return match.group(1).replace(" ", "") if match else ""

def is_available(score):
    return "yes" if score == "" else "no"

def determine_winner(home_team, away_team, score):
    if not score:
        return ""
    scores = score.split('-')
    if len(scores) != 2:
        return ""
    home_score, away_team_score = map(int, scores)
    if home_score > away_team_score:
        return home_team
    elif away_team_score > home_score:
        return away_team
    return "Draw"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

web = "https://liguemagnus.com/calendrier-resultats/?journee=&equipe=&poule=432&date_debut=&date_fin=2025-02-21"

# Set up Chrome options for headless execution
chrome_options = Options()
chrome_options.add_argument("--headless")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")

# Set up webdriver using webdriver_manager
service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=chrome_options)

driver.get(web)
logger.info(f"Current URL: {driver.current_url}")

wait = WebDriverWait(driver, 60)  # Increase wait time to 60 seconds
calendrier_div = wait.until(EC.presence_of_element_located((By.CLASS_NAME, "calendrier-general-compet")))
wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".calendrier-general-compet .cal-date")))

# Scroll the page
driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
time.sleep(5)  # Wait for content to load after scrolling

# Find all elements (dates and rows) using CSS selectors
all_elements = calendrier_div.find_elements(By.CSS_SELECTOR, ".cal-date, .row")

logger.info(f"Number of elements found: {len(all_elements)}")
for element in all_elements:
    logger.info(f"Element class: {element.get_attribute('class')}, text: {element.text[:50]}...")

# Use JavaScript to get content
all_content = driver.execute_script("""
    var div = document.querySelector('.calendrier-general-compet');
    return div.innerHTML;
""")
logger.info(f"Content retrieved via JavaScript: {all_content[:500]}...")  # Log first 500 characters

# Check for iframes
iframes = driver.find_elements(By.TAG_NAME, "iframe")
for iframe in iframes:
    logger.info(f"iframe src: {iframe.get_attribute('src')}")

matches = []
current_date = ""

for element in all_elements:
    if "cal-date" in element.get_attribute("class"):
        current_date = element.text
    elif "row" in element.get_attribute("class") and not "header-tab" in element.get_attribute("class"):
        match_data = element.text.split('\n')
        if len(match_data) >= 5:
            journee = match_data[0].replace('J', '')
            home_team, away_team = match_data[1], match_data[3]
            score_text = match_data[2]
            score = extract_score(score_text)

            matches.append({
                'leg': determine_leg(journee),
                'journee': journee,
                'date': current_date,
                'match': f"{home_team} - {away_team}",
                'win_type': determine_win_type(score_text),
                'score': score,
                'available': is_available(score),
                'winner': determine_winner(home_team, away_team, score)
            })

# Write to CSV file
with open('ligue_magnus_matches.csv', 'w', newline='', encoding='utf-8') as csvfile:
    fieldnames = ['leg', 'journee', 'date', 'match', 'win_type', 'score', 'available', 'winner']
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

    writer.writeheader()
    for match in matches:
        writer.writerow(match)

logger.info(f"CSV file 'ligue_magnus_matches.csv' has been created with {len(matches)} matches.")

driver.quit()
