from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import csv
from datetime import datetime

web = "https://www.rts.ch/sport/resultats/#/results/hockey/nla/Phase-1-0"
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
    print(f"Webpage loaded: {web}")


    def parsefrenchdate(datestr):
        day, month, year = map(int, datestr.split('.'))
        return datetime(year, month, day)
    
    french_months = {
        1: 'janvier', 2: 'février', 3: 'mars', 4: 'avril', 5: 'mai', 6: 'juin',
        7: 'juillet', 8: 'août', 9: 'septembre', 10: 'octobre', 11: 'novembre', 12: 'décembre'
    }
    
    def format_french_date(date):
        return f"{date.day} {french_months[date.month]} {date.year}"
    
    def accept_cookies(driver):
        try:
            print("Waiting for cookie consent dialog...")
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "usercentrics-root"))
            )
            print("Cookie consent dialog found. Attempting to click 'Accept' button...")
            script = """
            var shadowRoot = document.querySelector("#usercentrics-root").shadowRoot;
            var button = shadowRoot.querySelector("button[data-testid='uc-deny-all-button']");
            if (button) {
                button.click();
                return true;
            }
            return false;
            """
            result = driver.execute_script(script)
            if result:
                print("Cookies accepted successfully")
            else:
                print("Failed to find or click the 'Accept' button")
            time.sleep(5)
        except Exception as e:
            print(f"Error accepting cookies: {str(e)}")
    
    
    def select_month(driver, month):
        try:
            print(f"Attempting to select month: {month}")
            month_selector = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located(
                    (By.XPATH, f"//p[@class='stxt-scrollselection__label' and text()='{month}']"))
            )
            print(f"Month selector found for {month}")
    
            # Try regular click first
            try:
                month_selector.click()
            except:
                # If regular click fails, try JavaScript click
                driver.execute_script("arguments[0].click();", month_selector)
    
            print(f"Clicked on month: {month}")
            time.sleep(2)
        except Exception as e:
            print(f"Error selecting month {month}: {str(e)}")
    
    def determine_win_type(score):
        return "Extra Time" if "ap" in score or "tb" in score else "Regular Time"
    
    
    def determine_winner(home_team, away_team, score):
        if score == "No Score":
            return ""  # Return empty string if no score
    
        try:
            # Clean the score by removing any trailing text
            score_parts = score.split('-')
            home_score = int(score_parts[0].strip())
            away_score = int(score_parts[1].split()[0].strip())  # Handle cases like "3 - 2 ap"
    
            if home_score > away_score:
                return home_team
            elif away_score > home_score:
                return away_team
            else:
                return ""  # In case of a tie
        except (ValueError, IndexError):
            print(f"Error determining winner: Invalid score format '{score}'")
            return ""  # Return empty string on error
    
    
    def clean_score(score):
        if score == "No Score":
            return score
        # Remove 'ap' or 'tb' from the score
        score_parts = score.split(' - ')
        cleaned_score = ' - '.join(part.split()[0] for part in score_parts)
        return cleaned_score
    
    
    def scrape_month(driver):
        try:
            # print("Attempting to scrape month data...")
            teams = {
                "Davos", "Zurich", "Berne", "Lausanne", "Kloten",
                "Zoug", "Bienne", "Langnau", "Fribourg", "Genève",
                "Ambri", "Lugano", "Rapperswil", "Ajoie"
            }
    
            dates = WebDriverWait(driver, 20).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".stxt-results-table__date-inner"))
            )
            # print(f"Found {len(dates)} dates")
    
            span_elements = driver.find_elements(By.XPATH, "//span")
            # print(f"Found {len(span_elements)} span elements")
    
            all_data = [span.text.strip() for span in span_elements]
    
            current_date = None
            temp_match = {}
            temp_score = None
            matches_data = []
    
            for span_text in all_data:
                if span_text in [date.text for date in dates]:
                    current_date = span_text
                    temp_match = {}
                    temp_score = None
                elif current_date:
                    if span_text in teams:
                        if "home_team" not in temp_match:
                            temp_match["home_team"] = span_text
                        elif "away_team" not in temp_match:
                            temp_match["away_team"] = span_text
                            temp_match["date"] = current_date
                            if temp_score:
                                win_type = determine_win_type(temp_score)  # Determine win type before cleaning
                                temp_match["score"] = clean_score(temp_score)
                            else:
                                temp_match["score"] = "No Score"
                                win_type = "Regular Time"
    
                            leg = "First Leg" if parsefrenchdate(current_date) < datetime(2024, 12, 4) else "Second Leg"
                            winner = determine_winner(temp_match["home_team"], temp_match["away_team"], temp_match["score"])
    
                            match_data = {
                                "leg": leg,
                                "journee": "",
                                "date": format_french_date(parsefrenchdate(current_date)),
                                "match": f"{temp_match['home_team']} - {temp_match['away_team']}",
                                "win_type": win_type,
                                "score": temp_match["score"],
                                "available": "yes" if temp_match["score"] == "No Score" else "no",
                                "winner": winner
                            }
                            matches_data.append(match_data)
                            temp_match = {}
                            temp_score = None
                    elif " - " in span_text:
                        temp_score = span_text
    
            return matches_data
    
        except Exception as e:
            print(f"Error scraping month: {str(e)}")
            return []
    
    def write_matches_to_csv(matches_data, filename):
        with open(filename, 'w', newline='') as csvfile:
            fieldnames = ['leg', 'journee', 'date', 'match', 'win_type', 'score', 'available', 'winner']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
    
            writer.writeheader()
            for match in matches_data:
                writer.writerow(match)
                # print(f"Wrote match to CSV: {match}")  # Debug print
    
    print("Starting the scraping process...")
    driver.get(web)
    print("Webpage loaded")
    accept_cookies(driver)
    accept_cookies(driver)
    
    months = ["Septembre", "Octobre", "Novembre", "Décembre", "Janvier", "Février", "Mars"]
    
    all_matches_data = []
    for month in months:
        print(f"\nScraping data for: {month}")
        select_month(driver, month)
        matches_data = scrape_month(driver)
        all_matches_data.extend(matches_data)
    
    if all_matches_data:
        write_matches_to_csv(all_matches_data, 'nl_matches.csv')
        print(f"Total matches written to CSV: {len(all_matches_data)}")
    else:
        print("No data collected for any month")
    
    print("Scraping process completed")
except Exception as e:
    print(f"An error occurred: {str(e)}")

finally:
    if driver:
        driver.quit()
