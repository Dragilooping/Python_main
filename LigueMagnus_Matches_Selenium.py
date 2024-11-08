
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import logging
import csv
from datetime import datetime, timedelta
import re
import time
import traceback

MONTH_TRANSLATIONS = {
    'January': 'janvier', 'February': 'février', 'March': 'mars', 'April': 'avril',
    'May': 'mai', 'June': 'juin', 'July': 'juillet', 'August': 'août',
    'September': 'septembre', 'October': 'octobre', 'November': 'novembre', 'December': 'décembre'
}

def convert_date_format(date_string):
    try:
        # Parse the English date
        date_obj = datetime.strptime(date_string, "%B %d, %Y")
        date_obj += timedelta(days=1)
        # Format the date in French
        day = date_obj.day
        month = MONTH_TRANSLATIONS[date_obj.strftime('%B')]
        year = date_obj.year
        french_date = f"{day} {month} {year}"
        return french_date
    except ValueError:
        # If parsing fails, return the original string
        return date_string
        
def replace_team_names(team_name):
    replacements = {
        "BRIANÇON": "BRIANCON",
        "CERGY-PONTOISE": "CERGY"
    }
    return replacements.get(team_name, team_name)
    
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
        return replace_team_names(home_team)
    elif away_team_score > home_score:
        return replace_team_names(away_team)
    return "Draw"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

web = "https://liguemagnus.com/calendrier-resultats/?journee=&equipe=&poule=432&date_debut=&date_fin=2025-02-21"
driver = None
try:
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    wait = WebDriverWait(driver, 20)

    driver.get(web)
    logger.info(f"Scraping standings data from: {web}")

    calendrier_div = wait.until(EC.presence_of_element_located((By.CLASS_NAME, "calendrier-general-compet")))
    header_tab = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".calendrier-general-compet .row.header-tab")))
    logger.info(f"Header tab found: {header_tab.text}")

    all_elements = calendrier_div.find_elements(By.CSS_SELECTOR, ".cal-date, .row")
    logger.info(f"Number of elements found: {len(all_elements)}")

    for index, element in enumerate(all_elements):
        logger.info(f"Element {index}: Class: {element.get_attribute('class')}, Text: {element.text[:50]}...")

    matches = []
    current_date = ""

    for element in all_elements:
        if "cal-date" in element.get_attribute("class"):
            current_date = element.text
            current_date = convert_date_format(current_date)
        elif "row" in element.get_attribute("class") and "header-tab" not in element.get_attribute("class"):
            match_data = element.text.split('\n')
            if len(match_data) >= 4:  # We need at least 4 elements: Journee, Home team, Time/Score, Away team
                journee = match_data[0].replace('J', '')
                home_team = replace_team_names(match_data[1])
                score_or_time = match_data[2]
                away_team = replace_team_names(match_data[3])
                
                logger.info(f"Processing match: Journee {journee}")
                logger.info(f"Match data: {match_data}")
                
                score = extract_score(score_or_time)
                if not score:
                    score_text = "vs"
                else:
                    score_text = score_or_time
                
                match = {
                    'leg': determine_leg(journee),
                    'journee': journee,
                    'date': current_date,
                    'match': f"{home_team} - {away_team}",
                    'win_type': determine_win_type(score_text),
                    'score': score,
                    'available': is_available(score),
                    'winner': determine_winner(home_team, away_team, score)
                }
                matches.append(match)
                logger.info(f"Match processed: {match}")
            else:
                logger.info(f"Row skipped: insufficient data ({len(match_data)} < 4)")
    
    logger.info(f"Number of matches processed: {len(matches)}")

    with open('ligue_magnus_matches.csv', 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['leg', 'journee', 'date', 'match', 'win_type', 'score', 'available', 'winner']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for match in matches:
            writer.writerow(match)

    logger.info("CSV file 'ligue_magnus_matches.csv' has been created.")

except Exception as e:
    logger.error(f"An error occurred: {str(e)}")
    logger.error(traceback.format_exc())
    if driver:
        logger.warning("Page source:")
        logger.warning(driver.page_source)

finally:
    if driver:
        driver.quit()
