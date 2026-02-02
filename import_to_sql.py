import sqlite3
import pandas as pd
from contextlib import closing
import csv

class ConvertToSQL():
    def __init__(self):
        pass
    
    def run(self):
        player_hit_df = self.convert_csv_to_sql("player_hit.csv")
        player_pitch_df = self.convert_csv_to_sql("player_pitch.csv")
        standing_df = self.convert_csv_to_sql("standing.csv")
        team_hit_df = self.convert_csv_to_sql("team_hit.csv")
        team_pitch_df = self.convert_csv_to_sql("team_pitch.csv")
        draft_df = self.convert_csv_to_sql("draft.csv")
        home_run_derby_df = self.convert_csv_to_sql("home_run_derby.csv")
        salaries = self.convert_csv_to_sql("salary.csv")
        
    def convert_csv_to_sql(self, file):
        table_name = file.replace(".csv", "")
        df = pd.read_csv(file)
        self.clean_data(df)
        
        with closing(sqlite3.connect("baseball_data.db")) as conn:
            print("Database successfully opened.")
            df.to_sql(table_name, conn, if_exists = "replace", index = True, index_label = "row_id")
        
        if not conn:
            print("Database successfully close")
        return df
        

    def clean_data(self, df):
        self.combine_duplicate_columns(df)
        self.standardize_column_types(df)
        # print(df.head())
        
    def combine_duplicate_columns(self, df):
        column_names = df.columns.str.strip()
        # print(column_names)
        duplicate_mapping = {"Wins" : "W",
                "Losses" : "L",
                "Ties" : "T"}
        for full_stat, letter_stat in duplicate_mapping.items():
            if full_stat in column_names and letter_stat in column_names:
                df[full_stat] = pd.to_numeric(df[full_stat], errors = "coerce")
                df[letter_stat] = pd.to_numeric(df[letter_stat], errors = "coerce")
                df[full_stat] = df[letter_stat].fillna(df[full_stat]).fillna(0).astype(int)
                df.drop(columns = letter_stat, errors = "ignore", inplace = True)
    
    def standardize_column_types(self, df):
        column_names = df.columns
        type_mapping = {"Year" : int,
                        "#" : float,
                        # "Wins" : int,
                        # "Losses" : int,
                        # "Ties" : int,
                        "GB" : float}
        for column_name, data_type in type_mapping.items():
            if column_name in column_names:
                df[column_name] = pd.to_numeric(df[column_name], errors = "coerce").fillna(0).astype(data_type)
                
if __name__ == "__main__":
    ConvertToSQL().run()