import os
import pandas as pd
import json
from time import sleep
import re
from io import StringIO
from collections import defaultdict
from urllib.parse import urljoin
import ast

from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException

# Define a directory for the user profile (cache and cookies will be saved here)
# profile_dir = os.path.abspath('selenium_profile')

# # Ensure the directory exists
# if not os.path.exists(profile_dir):
#     os.makedirs(profile_dir)

# options = webdriver.ChromeOptions()
# options.add_argument('--headless')  # Enable headless mode
# options.add_argument('--disable-gpu')  # Optional, recommended for Windows
# options.add_argument(f"--user-data-dir={profile_dir}") # Specify the user data directory argument

# driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()),options=options)

class Scraper():
    def __init__(self):
        # self.driver = driver
        self.scraped_stat_pages = {}
        self.scraped_event_pages = {}
        self.events = defaultdict(dict)
        self.player_stats = defaultdict(dict)
        self.team_stats = defaultdict(dict)

    def scrape(self):
        # try:
        #     links = self.get_year_links("https://www.baseball-almanac.com/yearmenu.shtml")
        # # #     # links = ["https://www.baseball-almanac.com/yearly/yr1970n.shtml", "https://www.baseball-almanac.com/yearly/yr1986n.shtml", "https://www.baseball-almanac.com/yearly/yr1887n.shtml", "https://www.baseball-almanac.com/yearly/yr1883n.shtml", "https://www.baseball-almanac.com/yearly/yr1934a.shtml"]
        #     self.get_html(links)
            
        # # # #     # Testing purposes saved all the html into a csv so I can test my code without constantly scraping website for the html.
        #     data_to_save = [
        #         {**value, "url": url} 
        #         for url, value in self.scraped_event_pages.items()
        #     ]

        #     # Create the DataFrame
            # events_df = pd.DataFrame(data_to_save)

            # Save it - now 'url' will be its own column!
        #     events_df.to_csv("events_test.csv", index=False)
            
        # except Exception as e:
        #     print("Unable to open the url provided.")
        #     print(f"Exception: {type(e).__name__} {e}")

        df = pd.read_csv("events_test.csv")
        data_list = df.to_dict('records')

        # # Now pass that list to your function
        self.log_event_data(data_list)
        
        data = pd.read_csv("test.csv")
        html_strings = data["HTML_Content"]
        self.log_stat_data(html_strings)
        # print(self.events)
        
        salary_df, home_run_derby_df, draft_df = self.convert_events_to_df(self.events)
        # print(salary_df.head())
        # print(home_run_derby_df.head())
        # print(draft_df.head())
        salary_df.to_csv("csv_files/salary.csv", index = False)
        home_run_derby_df.to_csv("csv_files/home_run_derby.csv", index = False)
        draft_df.to_csv("csv_files/draft.csv", index = False)
        
        
        player_hit_df, player_pitch_df, player_standing_df = self.convert_stats_to_df(self.player_stats)
        team_hit_df, team_pitch_df, standing_df = self.convert_stats_to_df(self.team_stats)
        
        
        # # TODO THIS IS TEST TO MAKE SURE DATA IS CORRECT
        # temp = pd.json_normalize(self.player_stats)
        # temp.to_csv("test.csv", index = False)
        # print(player_hit_df)
        # print(player_pitch_df)
        player_hit_df.to_csv("csv_files/player_hit.csv", index = False)
        player_pitch_df.to_csv("csv_files/player_pitch.csv", index = False)
        team_hit_df.to_csv("csv_files/team_hit.csv", index = False)
        team_pitch_df.to_csv("csv_files/team_pitch.csv", index = False)
        standing_df.to_csv("csv_files/standing.csv", index = False)

        # self.driver.quit()
  
    def get_year_links(self, link):
        self.driver.get(link)
        search_results = self.driver.find_elements(By.CSS_SELECTOR, "table.ba-sub > tbody > tr > td.datacolBox > a")
        # only scraping data for the American and National leagues
        pattern = r"yr(?!(?:188[2-9]|189[01])a)\d{4}(a|n).shtml"
        links = [link.get_attribute("href") for link in search_results if re.search(pattern, link.get_attribute("href"))]
    
        return links
    
    # Takes the html found and gets the link of the events on the page if exists and stores them to a dictionary with year and event name and html for event pages?
    def get_event_links(self, current_page, html_string):
        events_links = {}
        events_pattern = r"Seasonal Events:\s*(.*?)(?=Navigation|$)"
        match = re.search(events_pattern, html_string)
        if match:
            events_html = match.group(1)
            link_pattern = r'href="([^"]+)">([^<]+)<\/a>'
            event_links_and_names = re.findall(link_pattern, events_html)
            # Getting event names from links because some pages have the links listed under wrong text
            for link, name in event_links_and_names:
                year_match = re.search(r'(?:yr)?(\d{4})', link)
                year = year_match.group(1).strip() if year_match else None
                
                link_lower = link.lower()
                if "hrderby" in link_lower or "home-run-derby" in link_lower:
                    event_type = "Home Run Derby"
                elif "asgbox" in link_lower or "all-star-game" in link_lower:
                    event_type = "All-Star Game"
                elif "draft" in link_lower:
                    event_type = "Draft"
                elif "ws" in link_lower:
                    event_type = "World Series"

                full_url = urljoin(current_page, link)
                events_links[full_url] = {"Year": year, "Event": event_type}
        return events_links
    
    # This gets the html for the new page and stores it in a dictionary with the link.  Also checks to make sure it is only for American and National League
    def get_html(self, stats_links):
        for stats_link in stats_links:
            print(f"Attempting to scrape {stats_link}")
            self.driver.get(stats_link)
            html_string = self.driver.find_element(By.XPATH, "//div[starts-with(@class, 'container') or starts-with(@id, 'container')][.//table]").get_attribute("innerHTML")
            self.scraped_stat_pages[stats_link] = html_string
            
            events_links = self.get_event_links(stats_link, html_string)
            for event_link, data in events_links.items():
                if not self.scraped_event_pages.get(event_link):
                    self.get_events_html(event_link, data)

    def get_events_html(self, event_link, data):
        print(f"Test - Attempting to scrape {event_link}")
        self.driver.get(event_link)
        try:
            # Find the table, then get its parent container
            element = self.driver.find_element(By.ID, "/wrapper").get_attribute("innerHTML")
            html_string = element.get_attribute("outerHTML")
        except NoSuchElementException:
            # Fallback: Just grab the whole body if the specific container isn't found
            html_string = self.driver.find_element(By.TAG_NAME, "body").get_attribute("innerHTML")
        self.scraped_event_pages[event_link] = {**data, "html" : html_string}
        
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

    # find's all the tbody tags in the html string can be used for both stats and events
    def find_tables(self, html_string : str):
        all_tables = pd.read_html(StringIO(html_string))
        # print(f"Found {len(all_tables)} tables on the page.")
        
        return all_tables
    
    # This is to find the table names for the stats page
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
    
    # This is to find col names for the stats page
    def find_col_names(self, table : list):
        # the column names will be index 1 in the list of rows
        col_names = [col.replace('\xa0', ' ').strip() for col in table[1].values() if isinstance(col, str)]
        # TODO Clean this up >_<
        col_names = [col.replace(" [Click for roster]", "").replace(" | Roster", "").replace("(s)", "").replace("East", "Region").replace("#", "stat_values").strip().lower() for col in col_names if col != "Top 25"]
        return col_names

    def find_table_data(self, col_names : list, table : list):
        # We know the data starts at the second index of the list.  We want to return a list of dictionaries, each dictionary for 1 row in the table with column name as the key
        salary = None
        salary_pattern = r".*(Salary).*"
        table_data = []
        
        for row in table[2::]:
            row_dict = {}
            row_values = [value for value in row.values()]
            # Checks if min and avg salary data provided
            if any(match := re.search(salary_pattern, str(val)) for val in row_values):
                salary = match.group()
                # if match := re.search(salary_pattern, current_val):
            # This skips adding any of the rows that are banners/column names in the table
            if any("Team" in str(val) for val in row_values) or any("Selected" in str(val) for val in row_values) or len(set(row_values)) == 1:
                continue
            for idx, col_name in enumerate(col_names):
                current_val = str(row_values[idx])
                if "$" in current_val:
                    row_values[idx] = current_val.replace("$", "").replace(",", "")
                if col_name == "wp":
                    row_values[idx] = current_val.replace(",", ".")
                if isinstance(row_values[idx], str):
                    row_dict[col_name] = row_values[idx]
            if row_dict:
                table_data.append(row_dict)
                
        return table_data, salary
            
    def get_table_data(self, all_dfs: list, year):
        player_dict = {}
        team_dict = {}
        salary_dict = {}
        for df in all_dfs:
            # Checking to make sure it is leaderboard vs statistics
            if len(df.columns) <= 8:
                records = df.to_dict("records")
                col_names = self.find_col_names(records)
                table_data, salary = self.find_table_data(col_names, records)
                dict_name, table_name = self.find_table_name(records)
                if dict_name == "Player":
                    player_dict[table_name] = table_data
                else:
                    team_dict[table_name] = table_data
                if salary:
                    salary_dict = self.clean_salary(salary, year)
                    
        return player_dict, team_dict, salary_dict
        
    def clean_salary(self, events, year):
        # TODO save events links and scrape that for winners
        events_dict = {}
        avg_salary_pattern = r"(Average\sSalary:\s[\d\$,.]+)"
        min_salary_pattern = r"(Minimum\sSalary:\s[\d\$,.]+)"
        avg_salary = re.search(avg_salary_pattern, events)
        min_salary = re.search(min_salary_pattern, events)
        events_dict["Year"] = year
        if avg_salary:
            avg_salary_label, avg_salary_amount = avg_salary.group().split(": $")
            avg_salary_amount = float(avg_salary_amount.replace(",", ""))
            events_dict[avg_salary_label] = avg_salary_amount
        if min_salary:
            min_salary_label, min_salary_amount = min_salary.group().split(": $")
            min_salary_amount = float(min_salary_amount.replace(",", ""))
            events_dict[min_salary_label] = min_salary_amount
        return events_dict

    def log_stat_data(self, html_strings):
        player_dict = {}
        team_dict = {}
        for html_string in html_strings:
            salary = []
            year, league = self.get_year_league(html_string)
            if year and league:
                # print(f"Collecting data for {year} {league}")
                all_dfs = self.find_tables(html_string)
                player_dict, team_dict, salary_dict = self.get_table_data(all_dfs, year)

                self.player_stats[year][league] = player_dict
                self.team_stats[year][league] = team_dict
                if salary_dict:
                    salary.append(salary_dict)
                    self.events[year]["Salary"] = salary

    def find_event_table_name(self, event, table : list):
        # Know that the table name will always be 0 key in the list
        table_name = [None, None]
        col = table[0][0]
        # TODO All-Star and World Series
        if event == "All-Star Game":
            table_name_pattern = r"(\d{4})?.*? (?:All-Star Game|ASG|Midsummer Classic)\s+(?:The\s+)?(?:\d{4}\s+)?([\w\s-]+)"
            if match := re.search(table_name_pattern, col):
                year = match.group(1)
                temp = match.group(2)
                table_name = [event, temp]
        # There are a bunch of different types of tables on here.  Will need to organize after
        if event == "World Series":
            opponents_pattern = r"^.*?\|\s*(?:.*Program\s+)?(.*?)\s*(?:\(\d+\))?\s+vs\s+(.*?)(?:\s*\(\d+\))?\s*\|.*$"
            game_num_pattern = r"^(Game\s+\d+).*?\s+(Line\s+Score)(?:\s*\||$)"
            composite_pattern = r"Composite (Hitting|Pitching) Statistics"
            if match := re.search(opponents_pattern, col):
                team_a = match.group(1).strip()
                team_b = match.group(2).strip()
                table_name = [team_a, team_b]
            elif match := re.search(game_num_pattern, col):
                game_num = match.group(1)
                score_type = match.group(2)
                table_name = [game_num, score_type]
            elif match := re.search(composite_pattern, col):
                complete_name = match.group(0)
                stat_type = match.group(1)
                table_name = [complete_name, stat_type]
        if event == "Draft":
            table_name_pattern = r"^(\d{4})"
            if match := re.search(table_name_pattern, col):
                year = match.group(0)
                year_event = f"{year} {event}"
                table_name = [int(year), "Draft First Round Picks"]
        # Home run derby pages have multiple years on them.  Need to get table name and year as well as location for table name from header
        if event == "Home Run Derby":
            table_name_pattern = r"^(\d{4})?.*?(?:Logo|Derby)\s+(?:\d{4}\s+)?(?:Home Run Derby\s+)?(?:Official Logo\s+)?(.* / .*)$"
            if match := re.search(table_name_pattern, col):
                year = match.group(1)
                location = match.group(2).strip()
                year_event = f"{year} {event}"
                table_name = [int(year), location]
        return table_name
        
    # We will already know the event name - we just need to handle the tables as the need to be (ex draft will be similar to stats but All Star and World Series need to be adjusted )
    # TODO FIX All-Star and World Series for now will disregard to finish project
    def find_event_col_names(self, event, table : list):
        col_names = []
        if event == "All-Star Game":
            col_names = list(dict.fromkeys(table[1].values()))
            col_names = ["Position" if col_name == "Pos" else col_name.replace(" MLB", "").replace(" Major League Baseball", "").replace("POS", "Position").replace("(s)", "").replace(" (ASGs)", "").strip() for col_name in col_names if isinstance(col_name, str)]
            if len(col_names) < 3 and "Fast Facts" not in col_names[0] and "Capsule" not in col_names[0]:
                col_names = [f"{col_names[0].split()[0]} {event}", "Fast Facts or Capsule"]
        if event == "World Series":
            col_names = list(dict.fromkeys(table[1].values()))
            col_names = ["Position" if col_name == "Pos" else col_name.replace("25-Man Roster", "Name").replace("POS", "Position").replace("Positions", "Position").replace("(s)", "").replace(" *", "").replace("Pitching Staff", "Name").strip() for col_name in col_names if isinstance(col_name, str)]
        # Home run derby and draft pages are same layout as stats pages
        if event == "Draft" or event == "Home Run Derby":
            col_names = self.find_col_names(table)
            col_names = [col_name.replace("college or hometown", "college_hs_hometown").replace("college or high school", "college_hs_hometown").replace("round1", "round 1").replace("round2", "round 2").replace("1stinning", "round 1").replace("2ndinning", "round 2").replace("stat_values", "picked").replace("selected by", "team").strip().lower() for col_name in col_names]
        return col_names

    def find_event_table_data(self, event : str, col_names : list, table : list):
        table_data = []
        # if event == "All-Star Game":
            # pass
        # if event == "World Series":
            # pass
        # Home run derby tables are same layout as stat tables and should work with self.find_table_data()
        if event == "Draft" or event == "Home Run Derby":
            table_data = self.find_table_data(col_names, table)[0]
        return table_data

    def get_event_table_data(self, event : str, event_dfs : list):
        event_dict = {}
        for event_df in event_dfs:
            # if event == "World Series":
            #     print(event_df)
            # table_text = event_df.to_string()
            # if "←" in table_text or "→" in table_text:
            #     continue
            if len(event_df) > 1:
                records = event_df.to_dict("records")
                data1, data2 = self.find_event_table_name(event, records)
                col_names = self.find_event_col_names(event, records)
                table_data = self.find_event_table_data(event, col_names, records)
                if event == "Home Run Derby":
                    table_data = [{**row, "Location": data2} for row in table_data]
                    event_dict[data1] = table_data
                if event == "Draft":
                    event_dict[data1] = table_data
        return event_dict
                
    def log_event_data(self, event_datas):
        event_dict = {}
        for event_data in event_datas:
            year = event_data.get("Year")
            event = event_data.get("Event")
            html_string = event_data.get("html")
            event_dfs = self.find_tables(html_string)
            event_dict = self.get_event_table_data(event, event_dfs)
            if event == "Draft" or event == "Home Run Derby":
                for key, value in event_dict.items():
                    self.events[key][event] = value
    
    def convert_events_to_df(self, events_dict):
        salary_table = []
        draft_table = []
        home_run_derby_table = []
        
        for year, events in events_dict.items():
            for items in events.get("Salary", []):
                self.add_to_events(salary_table, items, year)
            for items in events.get("Home Run Derby", []):
                self.add_to_events(home_run_derby_table, items, year)
            for items in events.get("Draft", []):
                self.add_to_events(draft_table, items, year)
        salary_stats = pd.DataFrame(salary_table).dropna(axis=1, how='all')
        home_run_derby_stats = pd.DataFrame(home_run_derby_table).dropna(axis=1, how='all')
        draft_stats = pd.DataFrame(draft_table).dropna(axis=1, how='all')
        return salary_stats, home_run_derby_stats, draft_stats
      
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
    
    def add_to_events(self, table, items, year):
        if items:
            stats = items.copy()
            stats["Year"] = year
            table.append(stats)
            
    # def clean_df(self, df):
    #     cleaned_df = df.dropna(axis=1, how='all')
    #     return cleaned_df

if __name__ == "__main__":
    Scraper().scrape()