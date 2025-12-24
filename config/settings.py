"""
NIFTY Trading System - Central Configuration
All constants and settings in one place.

NOTE: CREDENTIALS are NOT stored here (as per CLAUDE.md rules)
      They remain in their original files.
"""

# =============================================================================
# NIFTY INSTRUMENT CONFIGURATION
# =============================================================================

NIFTY_TOKEN = "99926000"          # NIFTY 50 Index token
NIFTY_LOT_SIZE = 75               # NIFTY lot size
STRIKE_INTERVAL = 50              # NIFTY strike price interval
NUM_STRIKES = 10                  # Default ±10 strikes from ATM
RISK_FREE_RATE = 0.065            # 6.5% risk-free rate (RBI repo rate)

# =============================================================================
# TRADING TIME CONFIGURATION
# =============================================================================

TRADING_DAYS_PER_YEAR = 252       # Trading days in a year
TRADING_MINUTES_PER_DAY = 375     # 9:15 AM to 3:30 PM = 6.25 hours

# =============================================================================
# DATA SERVER CONFIGURATION
# =============================================================================

SERVER_PORT = 9999                # Data server port
DATA_SERVER_URL = f"http://127.0.0.1:{SERVER_PORT}"
UPDATE_INTERVAL = 0.1             # 100ms minimum between broadcasts

# =============================================================================
# DATA STORAGE CONFIGURATION
# =============================================================================

DATA_BASE_PATH = "/Users/harsh/Desktop/test 1/data"
SAVE_DATA = True                  # Set to False to disable saving
