import scraper_logic as scrape
import import_to_sql as import_sql

def main():
    print("Running Program")
    scraper = scrape.Scraper()
    convert_to_sql = import_sql.ConvertToSQL()
    scraper.scrape()
    convert_to_sql.run()
    
if __name__ == "__main__":
    main()