import requests
from bs4 import BeautifulSoup
import re
import pandas as pd
import unicodedata
import os
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

url = 'https://www.hockeyarchives.info/France2025Magnus.htm'


def scrape_ligue_magnus_data_regular_season(url):
    try:
        response = requests.get(url)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"An error occurred: {e}")
        return []

    soup = BeautifulSoup(response.content, 'html.parser')
    pre_tags = soup.find_all('pre')
    title_tags = soup.find_all('p')

    data = []
    title_index = 5
    for index, pre in enumerate(pre_tags[:45], start=1):
        title_text = ""
        while title_index < len(title_tags):
            title_text = title_tags[title_index].get_text().strip()
            title_index += 1
            if not title_text.startswith('*'):
                break
        matches = pre.get_text().strip().split('\n')
        data.append({"title": title_text, "matches": matches})
    return data


def scrape_ligue_magnus_data_playoffs(url):
    try:
        response = requests.get(url)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"An error occurred: {e}")
        return []

    soup = BeautifulSoup(response.content, 'html.parser')
    playoffs_anchor = soup.find('a', {'name': 'PO'})

    data = []
    if playoffs_anchor and playoffs_anchor.find_parent('p'):
        current_element = playoffs_anchor.find_parent('p').find_next_sibling()
        current_title = ""
        while current_element:
            if current_element.name == 'p':
                current_title = current_element.get_text(strip=True)
                if "Meilleurs marqueurs" in current_title:
                    break
            elif current_element.name == 'pre':
                matches_text = current_element.get_text(strip=True)
                matches = re.findall(r'([^()]+\([^)]+\))', matches_text)
                data.append({"title": current_title, "matches": matches})
            current_element = current_element.find_next_sibling()
    return data

def clean_number(value):
    return re.sub(r'[^0-9]', '', value)

def normalize_text(text):
    # Convert to NFD form and remove diacritics
    text = ''.join(c for c in unicodedata.normalize('NFD', text)
                   if unicodedata.category(c) != 'Mn')
    # Replace specific characters
    text = text.replace('ç', 'c')
    return text

def determine_winner(match, score):
    if not score:
        return ''
    teams = match.split(' - ')
    if len(teams) != 2:
        return 'Invalid match format'
    scores = score.split('-')
    if len(scores) != 2:
        return 'Invalid score format'
    try:
        home_score, away_score = map(int, scores)
        if home_score > away_score:
            return teams[0]
        elif away_score > home_score:
            return teams[1]
        else:
            return 'Draw'
    except ValueError:
        return 'Invalid score'


def create_dataframe(regular_season_data, playoffs_data):
    all_data = []
    ranking_data = []

    for data_type, data in [("Regular Season", regular_season_data), ("Playoffs", playoffs_data)]:
        for item in data:
            title = normalize_text(item['title'])
            journee_match = re.search(r'(\d+)(?:re|e) journee', title)
            journee = journee_match.group(1) if journee_match else ""
            date_match = re.search(r'\((.*?)\)', title)
            default_date = normalize_text(date_match.group(1) if date_match else "")

            if "matches" in item:  # This is match data
                for match in item['matches']:
                    match = normalize_text(match)
                    match_date = re.search(r'\[(.*?)\]', match)
                    date = match_date.group(1) if match_date else default_date

                    match = re.sub(r'\[.*?\]', '', match).strip()

                    match_parts = re.split(r'(\d+-\d+(?:\s+(?:a\.p\.|t\.a\.b\.))?)', match)

                    teams = match_parts[0].strip()
                    score_part = match_parts[1].strip() if len(match_parts) > 1 else ""

                    if score_part:
                        available = 'no'
                        if 'a.p.' in score_part or 't.a.b.' in score_part:
                            win_type = 'Extra Time'
                            score = score_part.split()[0]
                        else:
                            win_type = 'Regular Time'
                            score = score_part
                        winner = determine_winner(teams, score)
                    else:
                        available = 'yes'
                        win_type = ''
                        score = ''
                        winner = ''

                    if data_type == "Regular Season":
                        try:
                            leg = "First Leg" if int(journee) <= 22 else "Second Leg"
                        except ValueError:
                            leg = "Unknown"
                    else:
                        leg = "Playoffs"

                    if leg == "Unknown":
                        # This is likely ranking data
                        parts = teams.split()
                        if len(parts) >= 3 and parts[0].isdigit():
                            rank = int(parts[0])
                            team = parts[1]
                            points = int(clean_number(parts[2]))
                            ranking_data.append({
                                'Rank': rank,
                                'Team': team,
                                'Points': points
                            })
                    else:
                        all_data.append({
                            'leg': leg,
                            'journee': journee,
                            'date': date,
                            'match': teams,
                            'win_type': win_type,
                            'score': score,
                            'available': available,
                            'winner': winner
                        })

    matches_df = pd.DataFrame(all_data)
    rankings_df = pd.DataFrame(ranking_data)

    return matches_df, rankings_df

def main():
    try:
        logger.info("Starting data scraping process")
        regular_season_data = scrape_ligue_magnus_data_regular_season(url)
        playoffs_data = scrape_ligue_magnus_data_playoffs(url)

        logger.info("Creating DataFrames")
        matches_df, rankings_df = create_dataframe(regular_season_data, playoffs_data)

        logger.info("Saving DataFrames to CSV")
        # Get the directory of the current script
        current_dir = os.path.dirname(os.path.abspath(__file__))
        
        # Save DataFrames to CSV in the same directory as the script
        matches_csv_path = os.path.join(current_dir, 'ligue_magnus_matches.csv')
        rankings_csv_path = os.path.join(current_dir, 'ligue_magnus_rankings.csv')
        
        matches_df.to_csv(matches_csv_path, index=False)
        rankings_df.to_csv(rankings_csv_path, index=False)

        logger.info(f"CSV files saved: {matches_csv_path}, {rankings_csv_path}")
    except Exception as e:
        logger.error(f"An error occurred: {e}")

if __name__ == "__main__":
    main()
