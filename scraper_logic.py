if __name__ == "__main__":
    # Backwards-compatible entrypoint. Prefer running:
    #   python -m diamond_data_scraper.cli
    from diamond_data_scraper.cli import main

    raise SystemExit(main())