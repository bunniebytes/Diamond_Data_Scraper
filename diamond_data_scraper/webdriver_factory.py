from __future__ import annotations

import os
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager


def build_chrome_driver(*, headless: bool, profile_dir: str) -> webdriver.Chrome:
    """
    Create and return a configured Chrome WebDriver instance.

    Note: `webdriver_manager` downloads/chooses an appropriate chromedriver automatically.
    """
    profile_dir = os.path.abspath(profile_dir)
    os.makedirs(profile_dir, exist_ok=True)

    options = webdriver.ChromeOptions()
    if headless:
        options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument(f"--user-data-dir={profile_dir}")

    return webdriver.Chrome(
        service=ChromeService(ChromeDriverManager().install()),
        options=options,
    )

