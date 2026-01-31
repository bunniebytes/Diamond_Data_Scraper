import os
import pandas as pd
import json
from time import sleep
import re
from io import StringIO
from collections import defaultdict

from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Define a directory for the user profile (cache and cookies will be saved here)
profile_dir = os.path.abspath('selenium_profile')

# Ensure the directory exists
if not os.path.exists(profile_dir):
    os.makedirs(profile_dir)

options = webdriver.ChromeOptions()
options.add_argument('--headless')  # Enable headless mode
options.add_argument('--disable-gpu')  # Optional, recommended for Windows
options.add_argument(f"--user-data-dir={profile_dir}") # Specify the user data directory argument

driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()),options=options)

class Scraper():
    def __init__(self):
        self.scraped_pages = {}
        self.events = {}
        self.player_stats = defaultdict(dict)
        self.team_stats = defaultdict(dict)

    def scrape(self):
        try:
            links = self.get_year_links("https://www.baseball-almanac.com/yearmenu.shtml")
            # links = ["https://www.baseball-almanac.com/yearly/yr1887n.shtml", "https://www.baseball-almanac.com/yearly/yr1970n.shtml"]
            self.log_html(links)
            # self.log_html(["https://www.baseball-almanac.com/yearly/yr1970n.shtml", "https://www.baseball-almanac.com/yearly/yr1986n.shtml", "https://www.baseball-almanac.com/yearly/yr1887n.shtml", "https://www.baseball-almanac.com/yearly/yr1883n.shtml", "https://www.baseball-almanac.com/yearly/yr1934a.shtml"])
            # self.log_data()
            
            # Testing purposes saved all the html into a csv so I can test my code without constantly scraping website for the html.
            # df = pd.DataFrame(self.scraped_pages.items(), columns=['URL', 'HTML_Content'])
            # df.to_csv("test.csv", index = False)
            
        except Exception as e:
            print("Unable to open the url provided.")
            print(f"Exception: {type(e).__name__} {e}")

        # data = pd.read_csv("test.csv")
        # html_strings = data["HTML_Content"]
        # self.log_data(html_strings)
        player_hit_df, player_pitch_df, player_standing_df = self.convert_stats_to_df(self.player_stats)
        team_hit_df, team_pitch_df, standing_df = self.convert_stats_to_df(self.team_stats)
        # events_df = pd.DataFrame(self.events)
        
        # # TODO THIS IS TEST TO MAKE SURE DATA IS CORRECT
        # temp = pd.json_normalize(self.player_stats)
        # temp.to_csv("test.csv", index = False)
        print(player_hit_df)
        print(player_pitch_df)
        player_hit_df.to_csv("player_hit.csv", index = False)
        player_pitch_df.to_csv("player_pitch.csv", index = False)
        team_hit_df.to_csv("team_hit.csv", index = False)
        team_pitch_df.to_csv("team_pitch.csv", index = False)
        standing_df.to_csv("standing.csv", index = False)
        # events_df.to_csv("events.csv", index=False)
        

        driver.quit()
  
    def get_year_links(self, link):
        driver.get(link)
        search_results = driver.find_elements(By.CSS_SELECTOR, "table.ba-sub > tbody > tr > td.datacolBox > a")
        # only scraping data for the American and National leagues
        pattern = r"yr(?!(?:188[2-9]|189[01])a)\d{4}(a|n).shtml"
        links = [link.get_attribute("href") for link in search_results if re.search(pattern, link.get_attribute("href"))]
    
        return links
    
    # This gets the html for the new page and stores it in a dictionary with the link.  Also checks to make sure it is only for American and National League
    def get_html(self, driver, link):
        html_string = driver.find_element(By.XPATH, "//div[starts-with(@class, 'container') or starts-with(@id, 'container')][.//table]").get_attribute("innerHTML")
        self.scraped_pages[link] = html_string
        
    def get_year_league(self, html_string : str):
        # pulling the header from the intro to get the year and the league
        pattern = r"(?i)\d{4}\s(american|national)\sleague"
        search_result = re.search(pattern, html_string).group()
        if search_result:
            year, league = search_result.split(" ", 1)
            year, league = int(year), league.title()
            if (year >= 1901 and league == "American League") or league == "National League":
                # print(f"Successfully retrieved {year} {league}")
                return year, league
        # TODO This is being raised because American Association has link that also ends in a.  Need to fix

    # find's all the tbody tags in the html string
    def find_tables(self, html_string : str):
        all_tables = pd.read_html(StringIO(html_string))
        # print(f"Found {len(all_tables)} tables on the page.")
        
        return all_tables
    
    # TODO Make this smaller functions T_T Need to delete?
    # def get_data(self, driver):
        player_stats_dict = {}
        team_stats_dict = {}
        search_results = driver.find_elements(By.CSS_SELECTOR, "table.boxed")
        
        for result in search_results:
            col_names = []
            duplicate_rows = {}
            table_name = None
            col_num = None
            data_list = []
            
            rows = result.find_elements(By.TAG_NAME, "tr")
            for row in rows:
                # league_pattern = r"(American|National)\sLeague"
                temp_table_name, temp_col_num = self.find_table_name_and_columns(row)
                temp_col_names, temp_dup_rows = self.find_col_names(row)
                data, temp_dup_rows = self.find_table_data(row, col_num, duplicate_rows)
                if temp_table_name:
                    table_name = temp_table_name
                if temp_col_num:
                    col_num = temp_col_num
                if temp_dup_rows:
                    duplicate_rows = temp_dup_rows
                if temp_col_names:
                    col_names = temp_col_names
                
            # TODO clean up events (do it in a seperate function??)
                if data and col_names:
                    if len(data) == len(col_names):
                        data_list.append(data)
                    
            if table_name and col_names and data_list:
                # Convert the list of rows into a list of dictionaries
                list_of_dictionaries = [dict(zip(col_names, row)) for row in data_list]
                
                # Determine which dictionary to add to
                if table_name[0] == "Player":
                    player_stats_dict[table_name[-1]] = list_of_dictionaries
                elif table_name[0] == "Team":
                    team_stats_dict[table_name[-1]] = list_of_dictionaries
                    
        return player_stats_dict, team_stats_dict
    
    def find_table_name(self, table : list):
        # Know that the table name will always be 0 key in the list
        table_name = []
        player_pattern = r"(Player|Pitcher)"
        team_pattern = r"Team(?=\sReview)|Team Standings"
        stat_name = r"(Hitting|Pitching)\sStatistics"
        player = "Player"
        col = table[0][0]
        # TODO get rid of this bandaid
        bandaid = table[len(table) - 1][0]

        if match := re.search(player_pattern, col):
            table_name.append(player)
        if (match := re.search(team_pattern, col)) or (match := re.search(team_pattern, bandaid)):
            team = match.group().split(" ")
            table_name.extend(team)
        if match := re.search(stat_name, col):
            stat = match.group(0)
            table_name.append(stat)
        # if len(table_name) == 1:
        #     print(team)
        return table_name
    
    def find_col_names(self, table : list):
        # the column names will be index 1 in the list of rows
        col_names = [col for col in table[1].values() if col != "Top 25"]
        # col_names = [col.replace(" [Click for roster]", "").replace(" | Roster", "").replace("(s)", "") for col in table[1].values() if isinstance(col, str)]
        return col_names

    def find_table_data(self, col_names : list, table):
        # We know the data starts at the second index of the list.  We want to return a list of dictionaries, each dictionary for 1 row in the table with column name as the key
        events = None
        events_pattern = r".*(Seasonal|Salary).*"
        table_data = []
        
        # TODO need to address the East/West/Central issue for the Standing table
        for row in table[2::]:
            row_dict = {}
            for idx, col_name in enumerate(col_names):
                row_values = [value for value in row.values()]
                current_val = str(row_values[idx])
                if match := re.search(events_pattern, current_val):
                    events = match.group()
                if col_name != row_values[idx] and len(set(row_values)) != 1:
                    row_dict[col_name.replace(" [Click for roster]", "").replace(" | Roster", "").replace("(s)", "")] = row_values[idx]
            if row_dict:
                table_data.append(row_dict)
                
        return table_data, events
            
    def get_table_data(self, all_dfs: list):
        player_dict = {}
        team_dict = {}
        events_dict = {}
        for df in all_dfs:
            # Checking to make sure it is leaderboard vs statistics
            if len(df.columns) <= 6:
                records = df.to_dict("records")
                col_names = self.find_col_names(records)
                table_data, events = self.find_table_data(col_names, records)
                dict_name, table_name = self.find_table_name(records)
                if dict_name == "Player":
                    player_dict[table_name] = table_data
                else:
                    team_dict[table_name] = table_data
                if events:
                    events_dict = self.clean_events(events)
                    
        return player_dict, team_dict, events_dict

    def clean_events(self, events):
        # TODO save events links and scrape that for winners
        events_dict = {}
        seasonal_pattern = r"Seasonal Events:\s*(.*?)(?=Navigation|$)"
        avg_salary_pattern = r"(Average\sSalary:\s[\d\$,.]+)"
        min_salary_pattern = r"(Minimum\sSalary:\s[\d\$,.]+)"
        seasonal_event = re.search(seasonal_pattern, events)
        avg_salary = re.search(avg_salary_pattern, events)
        min_salary = re.search(min_salary_pattern, events)
        
        if seasonal_event:
            events_label, events_list = seasonal_event.group().split(": ")
            events_list = events_list.split(" | ")
            events_dict[events_label] = events_list
        if avg_salary:
            avg_salary_label, avg_salary_amount = avg_salary.group().split(": $")
            events_dict[avg_salary_label] = avg_salary_amount
        if min_salary:
            min_salary_label, min_salary_amount = min_salary.group().split(": $")
            events_dict[min_salary_label] = min_salary_amount
        return events_dict

    def log_data(self, html_strings):
        player_dict = {}
        team_dict = {}
        for html_string in html_strings:
            year, league = self.get_year_league(html_string)
            if year and league:
                print(f"Collecting data for {year} {league}")
                all_dfs = self.find_tables(html_string)
                player_dict, team_dict, events_dict = self.get_table_data(all_dfs)
                if events_dict:
                    events_dict["Year"] = year
                    self.events[year] = events_dict

                self.player_stats[year][league] = player_dict
                self.team_stats[year][league] = team_dict
    
    def convert_events_to_df(self, events_dict):
        # Events will have tables [Events, Salary]
        events_list = ["Special Events", "Salary"]
    
    def convert_stats_to_df(self, dictionary):
        hit_table = []
        pitch_table = []
        standing_table = []
        # Current list of tables for stats [Hitting Statistics, Pitching Statistics, Standings]
        for year, leagues in dictionary.items():
            for league, data in leagues.items():
                # try:
                for items in data.get("Hitting Statistics", []):
                    self.add_to_table(hit_table, items, year, league)
                for items in data.get("Pitching Statistics", []):
                    self.add_to_table(pitch_table, items, year, league)
                for items in data.get("Standings", []):
                    self.add_to_table(standing_table, items, year, league)
                # except Exception:
                #     print(league)
        hit_stats = pd.DataFrame(hit_table).dropna(axis=1, how='all')
        pitch_stats = pd.DataFrame(pitch_table).dropna(axis=1, how='all')
        standing_stats = pd.DataFrame(standing_table).dropna(axis=1, how='all')

        return hit_stats, pitch_stats, standing_stats

    def add_to_table(self, table, items, year, league):
        if items:
            stats = items.copy()
            stats["Year"] = year
            stats["League"] = league
            table.append(stats)
            
    # def clean_df(self, df):
    #     cleaned_df = df.dropna(axis=1, how='all')
    #     return cleaned_df

if __name__ == "__main__":
    Scraper().scrape()