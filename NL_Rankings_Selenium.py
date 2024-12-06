from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import csv
import time

chrome_options = Options()
chrome_options.add_argument("--headless")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")

service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=chrome_options)

web = "https://www.rts.ch/sport/resultats/#/results/hockey/nla/Phase-1-0/rankings/700217"
driver = webdriver.Chrome(service=service, options=chrome_options)

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


def get_rankings():
    try:
        # Wait for the rankings table to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "table.stxt-ranking-table__table"))
        )

        # Get all td elements within the rankings table
        td_elements = driver.find_elements(By.CSS_SELECTOR, "td")

        # Parse the data
        rankings_data = []
        current_row = []
        for td in td_elements:
            text = td.text.strip()
            if text:  # Only add non-empty text
                current_row.append(text)
            if len(current_row) == 9:  # Each row should have exactly 9 fields
                rank, team, games_played, wins, overtime_wins, overtime_losses, losses, goals, points = current_row

                # Split goals into goals_for and goals_against
                goals_for, goals_against = map(int, goals.split('-'))

                # Append parsed data to rankings_data
                rankings_data.append([
                    rank.strip('.'), team, points, games_played, wins,
                    overtime_wins, overtime_losses, losses,
                    goals_for, goals_against
                ])
                current_row = []

        # Write to CSV
        with open('nl_rankings.csv', 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(['rank', 'team', 'points', 'games_played', 'wins',
                             'overtime_wins', 'overtime_losses', 'losses',
                             'goals_for', 'goals_against'])
            writer.writerows(rankings_data)

        print("Rankings data has been written to nl_rankings.csv")

    except Exception as e:
        print(f"An error occurred: {str(e)}")
        import traceback
        print(traceback.format_exc())

    finally:
        driver.quit()

driver.get(web)
accept_cookies(driver)
accept_cookies(driver)
get_rankings()
