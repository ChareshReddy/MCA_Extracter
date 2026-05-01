# ==========================================
# MCA EXTRACTION ENGINE - CONFIGURATION FILE
# ==========================================
# You can modify these values to adjust how the engine behaves.
# You MUST restart the engine after making changes here.

# --- Scraper Delays ---
# The engine will pause for a random time between these two values (in seconds)
# after extracting each record to mimic human behavior and prevent blocking.
DELAY_MIN_SECONDS = 30
DELAY_MAX_SECONDS = 60

# --- Extraction Limits ---
# Maximum number of CINs allowed in a single uploaded Excel file.
MAX_RECORDS_PER_FILE = 500

# --- Target URLs ---
# The base URLs used for extraction. Only change these if the target website changes its domain.
BASE_URL = "https://www.instafinancials.com"
SEARCH_HANDLER_URL = f"{BASE_URL}/Handlers/SearchHandler.ashx"
