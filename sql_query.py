import sqlite3
import pandas as pd
from contextlib import closing

class SQL_queries():
    def __init__(self):
        pass

    def open_database(self):
        with closing(sqlite3.connect("db/baseball_data.db")) as conn:
            print("Database successfully opened.")
            self.get_user_input(conn)
                
    def get_user_input(self, conn):
        while True:
            try:
                user_input = int(input("Would you like to 1. Filter, 2. Join, 3. Aggregate? (Please enter a number) "))
                
                if user_input in [1, 2, 3]:
                    break
                else:
                    user_input = input("Invalid choice. Please select 1, 2, or 3. ")
            except ValueError:
                user_input = input("Error: Please enter a number 1, 2, or 3. ")
        
        if user_input == 1:
            table_name, mapping = self.get_user_filter_query()
            filterd_table = self.filter_query(conn, table_name, mapping)
            print(filterd_table.head())
                
                
        elif user_input == 2:
            joined_draft = self.join_query(conn)
            print(joined_draft.head())
        
        else:
            pass
    
    def get_user_filter_query(self):
        tables = ["player_hit", "player_pitch", "team_hit", "team_pitch", "standing"]
        keys = ["Team", "Year", "Statistic", "League"]
        mapping = {}
        user_input = input("What table would you like to filter and look at? ").lower()
        while True:
            if user_input in tables:
                table_name = user_input
                break
            else:
                user_input = input("Please provide a valid table name ('player_hit', 'player_pitch', 'team_hit', 'team_pitch', 'standing') ")
        user_input = input("Do you want to filter by Team, Year, Statistic or League? ").title()
        while True:
            if user_input in keys:
                keyword = user_input
                break
            else:
                user_input = input("Please provide a valid choice ('Team', 'Year', Statistic, 'League') ").title()
        user_input = input("Would you like to filter for specific items? Y/N ").upper()
        if user_input == "Y":
            user_input = input("What would you like to look up? ").title()
            mapping[keyword] = f"{user_input}%"
        return table_name, mapping
        
    def filter_query(self, conn, table_name, mapping):
        query = f"SELECT * FROM [{table_name}]"
        conditions = []
        parameters = []
        for key, value in mapping.items():
            if value:
                conditions.append(f"[{key}] LIKE ?")
                parameters.append(value)
        if conditions:
            query += "WHERE" + "AND".join(conditions)
        filterd_table = pd.read_sql_query(query, conn, params = parameters)
        return filterd_table
            
    def join_query(self, conn):
        query = """SELECT d.name, d.Year as drafted, d.team, d.picked,
        
        MAX(CASE WHEN ph.statistic == "Complete Games" THEN ph.stat_values
            WHEN pp.statistic == "Complete Games" THEN pp.stat_values
            ELSE 0 END) AS [Complete Games],
        MAX(CASE WHEN ph.statistic == "Games" THEN ph.stat_values
            WHEN pp.statistic == "Games" THEN pp.stat_values
            ELSE 0 END) AS Games,
        MAX(CASE WHEN pp.statistic == "Winning Percentage" THEN pp.stat_values 
            WHEN ph.statistic == "Winning Percentage" THEN ph.stat_values
            ELSE 0 END) AS [winning percentage]
        
        FROM draft as d INNER JOIN player_hit as ph ON d.name = ph.name LEFT JOIN player_pitch as pp ON ph.name = pp.name WHERE d.picked < 10 GROUP BY d.name, d.year"""
        joined_draft = pd.read_sql_query(query, conn)
        return joined_draft
    
    def aggregate_query(self, *args):
        pass
# user_input = int(input("What would like to do?  Please provide a number, (1. See a specific year or team or league data. 2. Join Draft and Hit or Pitch Stats to see player's career stats. 3. Join Draft and Team stats to compare draft and team standings.) "))
# Want to take user input
SQL_queries().open_database() 