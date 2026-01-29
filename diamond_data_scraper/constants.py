import re

YEAR_MENU_URL = "https://www.baseball-almanac.com/yearmenu.shtml"

# Matches the year-menu link format like ".../yearly/yr1970n.shtml" or ".../yearly/yr1934a.shtml".
YEARLY_LINK_RE = re.compile(r"/yearly/yr(?P<year>\d{4})(?P<league_code>[an])\.shtml$")

# Matches the H1 header content on year pages.
YEAR_LEAGUE_HEADER_RE = re.compile(r"(?P<year>\d{4})\s(?P<league>AMERICAN|NATIONAL)\sLEAGUE")

# Extracts canonical stat table keys from header text.
STAT_TABLE_KEY_RE = re.compile(r"\b(Hitting Statistics|Pitching Statistics|Standings)\b")

