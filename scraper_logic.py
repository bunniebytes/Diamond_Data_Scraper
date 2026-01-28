import os
import pandas as pd
import json
from time import sleep
import re
from collections import defaultdict

from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By

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
        self.events = {}
        self.player_stats = defaultdict(dict)
        self.team_stats = defaultdict(dict)

    def scrape(self):
        try:
            links = self.get_year_links("https://www.baseball-almanac.com/yearmenu.shtml")
            # links = ["https://www.baseball-almanac.com/yearly/yr1887n.shtml", "https://www.baseball-almanac.com/yearly/yr1970n.shtml"]
            self.log_data(links)
            # self.log_data(["https://www.baseball-almanac.com/yearly/yr1970n.shtml", "https://www.baseball-almanac.com/yearly/yr1986n.shtml", "https://www.baseball-almanac.com/yearly/yr1887n.shtml", "https://www.baseball-almanac.com/yearly/yr1883n.shtml", "https://www.baseball-almanac.com/yearly/yr1934a.shtml"])
            
        except Exception as e:
            print("Unable to open the url provided.")
            print(f"Exception: {type(e).__name__} {e}")

        player_hit_df, player_pitch_df, player_standing_df = self.convert_stats_to_df(self.player_stats)
        team_hit_df, team_pitch_df, standing_df = self.convert_stats_to_df(self.team_stats)
        
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
        
        driver.quit()
  
    def get_year_links(self, link):
        driver.get(link)
        search_results = driver.find_elements(By.CSS_SELECTOR, "table.ba-sub > tbody > tr > td.datacolBox > a")
        # only scraping data for the American and National leagues
        pattern = r"yr\d{4}(a|n)\.shtml$"
        links = [link.get_attribute("href") for link in search_results if re.search(pattern, link.get_attribute("href"))]
    
        return links
    
    # This gets the driver for the new page
    def get_driver_new_page(self, link):
        driver.get(link)
    
    def get_year_league(self, driver):
        # pulling the header from the intro to get the year and the league
        scraped_data = driver.find_element(By.CSS_SELECTOR, "div.intro > h1")
        pattern = r"\d{4}\s(AMERICAN|NATIONAL)\sLEAGUE"
        try:
            search_result = re.search(pattern, scraped_data.text).group()
            if search_result:
                year, league = search_result.split(" ", 1)
                year, league = int(year), league.title()
            if (year >= 1901 and league == "American League") or league == "National League":
                return year, league
        # TODO This is being raised because American Association has link that also ends in a.  Need to fix
        except Exception:
            pass

        
    # TODO Make this smaller functions T_T
    def get_data(self, driver):
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
                data, temp_dup_rows = self.find_cell_data(row, col_num, duplicate_rows)
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
    
    def find_table_name_and_columns(self, row):
        table_name = []
        player_pattern = r"(Player|Pitcher)"
        team_pattern = r"Team(?= Review)|Team Standings"
        stat_name = r"^.+Statistics"
        try:
            headers = [header.text for header in row.find_elements(By.XPATH, ".//h2 | .//p")]
        except:
            pass
        if not headers:
            return None, None
        num_cols = row.find_element(By.TAG_NAME, "td").get_attribute("colspan")

        if match := re.search(player_pattern, headers[0]):
            player = "Player"
            table_name.append(player)
        if match := re.search(team_pattern, headers[0]) or (match := re.search(team_pattern, headers[1])):
            team = match.group().split(" ")
            table_name.extend(team)
        if match := re.search(stat_name, headers[1]):
            stat = match.group()
            table_name.append(stat)
            
        return table_name, int(num_cols)
    
    def find_col_names(self, row):
        try:
            elements = row.find_elements(By.XPATH, ".//td[contains(@class, 'banner')]")
        except:
            pass
        col_names = []
        duplicate_row_val = {}
        if not elements:
            return None, None
        regions = ["East", "Central", "West"]
        for idx, name in enumerate(elements):
            num_rows = name.get_attribute("rowspan")
            if num_rows:
                duplicate_row_val[idx] = [name.text, int(num_rows)]
            if name.text in regions:
                col_names.append("Region")
            else:
                col_names.append(name.text.replace(" [Click for roster]", "").strip())
        return col_names, duplicate_row_val

    def find_cell_data(self, row, num_cols, duplicate_rows):
        try:
            cells = row.find_elements(By.XPATH, ".//td[contains(@class, 'datacolBox') or contains(@class, 'datacolBlue')]")
        except:
            pass
        if not cells:
            return None, duplicate_rows
        data = []
        for idx, cell in enumerate(cells):
            num_rows = cell.get_attribute("rowspan")
            if num_rows:
                duplicate_rows[idx] = [cell.text, int(num_rows)]
            data.append(cell.text.strip())
        if len(data) != num_cols:
            for idx, value in duplicate_rows.items():
                data.insert(idx, value[0])
                duplicate_rows[idx][1] -= 1
        duplicate_rows = {k: v for k, v in duplicate_rows.items() if v[1] > 0}
        # if len(cells) > 1 and len(cells) == len(col_names):
        #     prev_cells = cells
        #     cell_results.append(cells)
        return data, duplicate_rows

    def clean_events(self, driver):
        # TODO save events links and scrape that for winners
        events_dict = {}
        row = None
        try:
            row = driver.find_element(By.XPATH, ".//td[contains(., 'Events') or contains(., 'Salary')]")
        except:
            pass
        if not row:
            return events_dict
        
        event_text = row.text.split("\n")
        
        for text in event_text:
            text = text.split(": ")
            title = text[0]
            info = text[1].split(" | ")
            if "Events" in title or "Salary" in title:
                events_dict[title] = info
        return events_dict
        
    # def get_event(self, driver):
    #     search_results = driver.find_elements(By.CSS_SELECTOR, "table.boxed > tbody > tr")
        
    #     print(search_results)
    
    def log_data(self, links : list):
        for link in links:
            try:
                driver.get(link)
                sleep(2)
            except Exception:
                pass
            year, league = self.get_year_league(driver)
            if year and league:
                player, team = self.get_data(driver)
                self.player_stats[year][league] = player
                self.team_stats[year][league] = team
                if not self.events.get(year):
                    events = self.clean_events(driver)
                    self.events[year] = events
            
    
    def convert_events_to_df(self, dictionary):
        # Events will have tables [Events, Salary]
        events_list = ["Special Events", "Salary"]
    
    def convert_stats_to_df(self, dictionary):
        hit_table = []
        pitch_table = []
        standing_table = []
        # Current list of tables for stats [Hitting Statistics, Pitching Statistics, Standings]
        for year, leagues in dictionary.items():
            for league, data in leagues.items():
                for items in data.get("Hitting Statistics", []):
                    self.add_to_table(hit_table, items, year, league)
                for items in data.get("Pitching Statistics", []):
                    self.add_to_table(pitch_table, items, year, league)
                for items in data.get("Standings", []):
                    self.add_to_table(standing_table, items, year, league)
                    
        hit_stats = pd.DataFrame(hit_table)
        pitch_stats = pd.DataFrame(pitch_table)
        standing_stats = pd.DataFrame(standing_table)

        return hit_stats, pitch_stats, standing_stats
        

    def add_to_table(self, table, items, year, league):
        if items:
            stats = items.copy()
            stats["Year"] = year
            stats["League"] = league
            table.append(stats)

if __name__ == "__main__":
    Scraper().scrape()