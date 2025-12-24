#!/usr/bin/env python3
"""
NIFTY Option Chain - Live with Greeks
ATM ± 10 Strikes with IV, Delta, Gamma, Theta, Vega
"""

import pyotp
import json
import struct
import threading
import time
import math
import os
import csv
import websocket
from datetime import datetime, timedelta
from SmartApi import SmartConnect
import requests

# Angel One Credentials
CREDENTIALS = {
    "client_id": "H124854",
    "password": "4794",
    "api_key": "5dZpj3Dg",
    "totp_secret": "L2AAG25BMVUICSO52GIMMHBPOE",
}

# NIFTY Configuration
NIFTY_TOKEN = "99926000"  # NIFTY 50 Index token
STRIKE_INTERVAL = 50  # NIFTY strike interval
NUM_STRIKES = 10  # ±10 strikes from ATM
RISK_FREE_RATE = 0.065  # 6.5% risk-free rate (RBI repo rate)
NIFTY_LOT_SIZE = 75  # NIFTY lot size (updated)

# Data Storage Configuration
DATA_BASE_PATH = "/Users/harsh/Desktop/test 1/data"
SAVE_DATA = True  # Set to False to disable saving

# Data Server Configuration (for shared mode)
DATA_SERVER_URL = "http://127.0.0.1:8888"

# Global storage
option_data = {}
spot_price = 0
spot_close = 0
spot_open = 0
spot_high = 0
spot_low = 0
futures_price = 0
futures_close = 0
futures_open = 0
futures_high = 0
futures_low = 0
futures_oi = 0
futures_volume = 0
futures_token = None
futures_symbol = ""
current_expiry = ""
ws_connection = None

# File writers (to keep files open for faster writing)
spot_writer = None
futures_writer = None
option_writers = {}


# ============== BLACK-SCHOLES GREEKS CALCULATOR ==============

def norm_cdf(x):
    """Standard normal cumulative distribution function"""
    return (1.0 + math.erf(x / math.sqrt(2.0))) / 2.0

def norm_pdf(x):
    """Standard normal probability density function"""
    return math.exp(-0.5 * x * x) / math.sqrt(2 * math.pi)

def calculate_d1_d2(S, K, T, r, sigma):
    """Calculate d1 and d2 for Black-Scholes"""
    if T <= 0 or sigma <= 0:
        return 0, 0
    d1 = (math.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * math.sqrt(T))
    d2 = d1 - sigma * math.sqrt(T)
    return d1, d2

def bs_price(S, K, T, r, sigma, option_type):
    """Black-Scholes option price"""
    if T <= 0:
        if option_type == 'CE':
            return max(0, S - K)
        else:
            return max(0, K - S)

    d1, d2 = calculate_d1_d2(S, K, T, r, sigma)

    if option_type == 'CE':
        price = S * norm_cdf(d1) - K * math.exp(-r * T) * norm_cdf(d2)
    else:
        price = K * math.exp(-r * T) * norm_cdf(-d2) - S * norm_cdf(-d1)

    return price

def implied_volatility(market_price, S, K, T, r, option_type, max_iter=100):
    """Calculate implied volatility using Bisection method (guaranteed convergence)"""
    if T <= 0 or market_price <= 0:
        return 0

    # Calculate intrinsic value
    intrinsic = max(0, S - K) if option_type == 'CE' else max(0, K - S)

    # If market price is less than intrinsic (deep ITM, negative time value)
    if market_price < intrinsic:
        return 0.01  # 1% IV for deep ITM (Gamma will be ~0)

    # Bisection method: guaranteed to converge
    low_vol = 0.001   # 0.1% IV (lower bound for better precision)
    high_vol = 5.0    # 500% IV (higher bound for edge cases)

    # Adaptive tolerance based on price magnitude
    tolerance = max(0.01, market_price * 0.001)  # 0.1% of price or min 0.01

    for _ in range(max_iter):
        mid_vol = (low_vol + high_vol) / 2
        mid_price = bs_price(S, K, T, r, mid_vol, option_type)

        diff = mid_price - market_price

        if abs(diff) < tolerance:
            return mid_vol

        if diff > 0:
            # Price too high, reduce IV
            high_vol = mid_vol
        else:
            # Price too low, increase IV
            low_vol = mid_vol

        # Check if range is small enough (IV precision)
        if (high_vol - low_vol) < 0.0001:
            break

    return mid_vol

def calculate_delta(S, K, T, r, sigma, option_type):
    """Calculate Delta"""
    if T <= 0 or sigma <= 0:
        if option_type == 'CE':
            return 1.0 if S > K else 0.0
        else:
            return -1.0 if S < K else 0.0

    d1, _ = calculate_d1_d2(S, K, T, r, sigma)

    if option_type == 'CE':
        return norm_cdf(d1)
    else:
        return norm_cdf(d1) - 1

def calculate_gamma(S, K, T, r, sigma):
    """Calculate Gamma (same for CE and PE)"""
    if T <= 0 or sigma <= 0:
        return 0

    d1, _ = calculate_d1_d2(S, K, T, r, sigma)
    return norm_pdf(d1) / (S * sigma * math.sqrt(T))

def calculate_theta(S, K, T, r, sigma, option_type):
    """Calculate Theta (per day)"""
    if T <= 0 or sigma <= 0:
        return 0

    d1, d2 = calculate_d1_d2(S, K, T, r, sigma)

    term1 = -(S * norm_pdf(d1) * sigma) / (2 * math.sqrt(T))

    if option_type == 'CE':
        term2 = -r * K * math.exp(-r * T) * norm_cdf(d2)
    else:
        term2 = r * K * math.exp(-r * T) * norm_cdf(-d2)

    return (term1 + term2) / 365  # Per day

def calculate_vega(S, K, T, r, sigma):
    """Calculate Vega (same for CE and PE)"""
    if T <= 0 or sigma <= 0:
        return 0

    d1, _ = calculate_d1_d2(S, K, T, r, sigma)
    return S * norm_pdf(d1) * math.sqrt(T) / 100  # Per 1% change


# ============== ANGEL ONE CONNECTION ==============

def login():
    """Login to Angel One"""
    print("Logging in to Angel One...")
    totp = pyotp.TOTP(CREDENTIALS["totp_secret"]).now()
    obj = SmartConnect(api_key=CREDENTIALS["api_key"])
    data = obj.generateSession(
        clientCode=CREDENTIALS["client_id"],
        password=CREDENTIALS["password"],
        totp=totp
    )

    if data['status']:
        print("Login successful!")
        return obj, data['data']['jwtToken'], obj.getfeedToken()
    else:
        print(f"Login failed: {data}")
        return None, None, None

def get_nifty_spot(obj):
    """Get current NIFTY spot price and previous close"""
    global spot_close
    try:
        ltp_data = obj.ltpData(exchange="NSE", tradingsymbol="NIFTY", symboltoken=NIFTY_TOKEN)
        if ltp_data['status']:
            spot_close = ltp_data['data'].get('close', 0)
            return ltp_data['data']['ltp']
    except Exception as e:
        print(f"Error getting NIFTY spot: {e}")
    return None

def calculate_atm_strike(spot):
    """Calculate ATM strike based on spot price"""
    return round(spot / STRIKE_INTERVAL) * STRIKE_INTERVAL

def get_current_expiry(all_tokens):
    """Get nearest expiry from available tokens"""
    nifty_opts = [t for t in all_tokens
                  if t.get('exch_seg') == 'NFO'
                  and 'NIFTY' in t.get('symbol', '')
                  and t.get('instrumenttype') == 'OPTIDX'
                  and 'BANKNIFTY' not in t.get('symbol', '')]

    expiries = set(t.get('expiry', '') for t in nifty_opts)

    # Parse and find nearest future expiry
    today = datetime.now()
    nearest_expiry = None
    min_days = 999

    for exp in expiries:
        try:
            # Set expiry time to 15:30 (market close) for accurate comparison
            exp_date = datetime.strptime(exp, '%d%b%Y').replace(hour=15, minute=30)
            time_diff = (exp_date - today).total_seconds()
            days = (exp_date.date() - today.date()).days
            # Include today's expiry until 15:30
            if time_diff >= 0 and days < min_days:
                min_days = days
                nearest_expiry = exp
        except:
            continue

    return nearest_expiry

def load_all_tokens():
    """Load all tokens from file or download"""
    token_file = "/Users/harsh/Desktop/test 1/angelone_tokens.json"

    try:
        with open(token_file, 'r') as f:
            return json.load(f)
    except:
        print("Downloading token file...")
        url = "https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json"
        response = requests.get(url, timeout=60)
        return response.json()

def get_nearest_futures_token(all_tokens):
    """Get nearest NIFTY futures token"""
    nifty_fut = [t for t in all_tokens if t.get('exch_seg') == 'NFO'
                 and t.get('symbol', '').startswith('NIFTY')
                 and t.get('instrumenttype') == 'FUTIDX'
                 and 'BANKNIFTY' not in t.get('symbol', '')
                 and 'FINNIFTY' not in t.get('symbol', '')
                 and 'MIDCPNIFTY' not in t.get('symbol', '')
                 and 'NIFTYNXT' not in t.get('symbol', '')]

    today = datetime.now()
    valid_futures = []
    for t in nifty_fut:
        try:
            # Set expiry time to 15:30 for accurate comparison
            exp_date = datetime.strptime(t.get('expiry', ''), '%d%b%Y').replace(hour=15, minute=30)
            if exp_date >= today:
                valid_futures.append((exp_date, t))
        except:
            pass

    if valid_futures:
        valid_futures.sort(key=lambda x: x[0])
        nearest = valid_futures[0][1]
        return nearest.get('token'), nearest.get('symbol')
    return None, None

def load_option_tokens(all_tokens, expiry, atm_strike):
    """Load option tokens for ATM ± 10 strikes"""
    print(f"\nLoading tokens for expiry: {expiry}, ATM: {atm_strike}")

    # Generate strikes
    strikes = []
    for i in range(-NUM_STRIKES, NUM_STRIKES + 1):
        strikes.append(atm_strike + (i * STRIKE_INTERVAL))

    # Find matching tokens
    option_tokens = {'CE': {}, 'PE': {}}

    for token in all_tokens:
        if token.get('exch_seg') != 'NFO':
            continue
        if token.get('instrumenttype') != 'OPTIDX':
            continue

        symbol = token.get('symbol', '')
        if not symbol.startswith('NIFTY') or 'BANKNIFTY' in symbol:
            continue

        # Check expiry
        token_expiry = token.get('expiry', '')
        if token_expiry != expiry:
            continue

        # Parse strike and option type
        try:
            strike_str = token.get('strike', '0')
            strike = int(float(strike_str) / 100)  # Strike is in paise

            if strike in strikes:
                if symbol.endswith('CE'):
                    option_tokens['CE'][strike] = {
                        'token': token['token'],
                        'symbol': symbol,
                        'lotsize': int(token.get('lotsize', NIFTY_LOT_SIZE))
                    }
                elif symbol.endswith('PE'):
                    option_tokens['PE'][strike] = {
                        'token': token['token'],
                        'symbol': symbol,
                        'lotsize': int(token.get('lotsize', NIFTY_LOT_SIZE))
                    }
        except:
            continue

    print(f"Found {len(option_tokens['CE'])} CE and {len(option_tokens['PE'])} PE options")
    return option_tokens, strikes


# ============== WEBSOCKET HANDLING ==============

def parse_best_5_data(data):
    """
    Parse Best 5 Bid/Ask data from bytes 147-347 (200 bytes)
    Each packet: 20 bytes = flag(2) + qty(8) + price(8) + orders(2)
    Flag: 0 = Bid, 1 = Ask
    """
    bids = []
    asks = []
    bid_qty = []
    ask_qty = []

    try:
        # 10 packets × 20 bytes each
        for i in range(10):
            offset = i * 20
            if offset + 20 > len(data):
                break

            flag = struct.unpack('<H', data[offset:offset+2])[0]
            qty = struct.unpack('<q', data[offset+2:offset+10])[0]
            price = struct.unpack('<q', data[offset+10:offset+18])[0] / 100
            # orders = struct.unpack('<H', data[offset+18:offset+20])[0]  # Not needed for now

            if flag == 0:  # Bid
                bids.append(price)
                bid_qty.append(qty)
            else:  # Ask
                asks.append(price)
                ask_qty.append(qty)
    except:
        pass

    return {
        'bids': bids,
        'asks': asks,
        'bid_qty': bid_qty,
        'ask_qty': ask_qty
    }


def parse_snapquote_packet(data):
    """Parse SnapQuote mode (mode 3) binary packet - 379 bytes"""
    try:
        if len(data) < 155:
            return None

        token = data[2:27].decode('utf-8').strip('\x00')
        ltp = struct.unpack('<q', data[43:51])[0] / 100
        ltq = struct.unpack('<q', data[51:59])[0]
        atp = struct.unpack('<q', data[59:67])[0] / 100
        volume = struct.unpack('<q', data[67:75])[0]
        total_buy_qty = struct.unpack('<q', data[75:83])[0]
        total_sell_qty = struct.unpack('<q', data[83:91])[0]
        open_price = struct.unpack('<q', data[91:99])[0] / 100
        high = struct.unpack('<q', data[99:107])[0] / 100
        low = struct.unpack('<q', data[107:115])[0] / 100
        close = struct.unpack('<q', data[115:123])[0] / 100
        oi = struct.unpack('<q', data[131:139])[0]

        # Parse Best 5 Bid/Ask if data available (bytes 147-347)
        best_5 = {'bids': [], 'asks': [], 'bid_qty': [], 'ask_qty': []}
        if len(data) >= 347:
            best_5 = parse_best_5_data(data[147:347])

        return {
            'token': token,
            'ltp': ltp,
            'ltq': ltq,
            'atp': atp,
            'volume': volume,
            'total_buy_qty': total_buy_qty,
            'total_sell_qty': total_sell_qty,
            'open': open_price,
            'high': high,
            'low': low,
            'close': close,
            'oi': oi,
            'best_bids': best_5['bids'],
            'best_asks': best_5['asks'],
            'bid_qty': best_5['bid_qty'],
            'ask_qty': best_5['ask_qty']
        }
    except Exception as e:
        return None

def parse_ltp_packet(data):
    """Parse LTP mode (mode 1) binary packet - 51 bytes"""
    try:
        if len(data) < 51:
            return None

        token = data[2:27].decode('utf-8').strip('\x00')
        ltp = struct.unpack('<q', data[43:51])[0] / 100

        return {'token': token, 'ltp': ltp}
    except:
        return None


# ============== DISPLAY FUNCTIONS ==============

def clear_screen():
    """Clear terminal screen"""
    print("\033[2J\033[H", end="")


# ============== DATA SAVING FUNCTIONS ==============

def create_data_folders(expiry):
    """Create folder structure for data storage"""
    today = datetime.now().strftime("%Y-%m-%d")

    # Main date folder
    date_folder = os.path.join(DATA_BASE_PATH, today)

    # Options folder with expiry subfolder
    options_folder = os.path.join(date_folder, "options", expiry)

    # Create all folders
    os.makedirs(options_folder, exist_ok=True)

    return date_folder, options_folder

def init_spot_file(date_folder):
    """Initialize spot CSV file with headers"""
    global spot_writer

    filepath = os.path.join(date_folder, "spot.csv")
    # Check if file exists AND has content
    file_has_data = os.path.exists(filepath) and os.path.getsize(filepath) > 0

    file_handle = open(filepath, 'a', newline='', buffering=1)  # Line buffered
    writer = csv.writer(file_handle)

    if not file_has_data:
        writer.writerow([
            'timestamp', 'ltp', 'open', 'high', 'low', 'close',
            'change', 'change_pct'
        ])
        file_handle.flush()

    spot_writer = {'writer': writer, 'handle': file_handle}
    return file_handle

def init_futures_file(date_folder):
    """Initialize futures CSV file with headers"""
    global futures_writer

    filepath = os.path.join(date_folder, "futures.csv")
    # Check if file exists AND has content
    file_has_data = os.path.exists(filepath) and os.path.getsize(filepath) > 0

    file_handle = open(filepath, 'a', newline='', buffering=1)  # Line buffered
    writer = csv.writer(file_handle)

    if not file_has_data:
        writer.writerow([
            'timestamp', 'symbol', 'ltp', 'open', 'high', 'low', 'close',
            'change', 'change_pct', 'oi', 'volume'
        ])
        file_handle.flush()

    futures_writer = {'writer': writer, 'handle': file_handle}
    return file_handle

def init_option_file(options_folder, strike, opt_type, expiry):
    """Initialize option CSV file with headers"""
    global option_writers

    filename = f"NIFTY_{strike}_{opt_type}.csv"
    filepath = os.path.join(options_folder, filename)
    # Check if file exists AND has content
    file_has_data = os.path.exists(filepath) and os.path.getsize(filepath) > 0

    file_handle = open(filepath, 'a', newline='', buffering=1)  # Line buffered
    writer = csv.writer(file_handle)

    if not file_has_data:
        writer.writerow([
            'timestamp', 'symbol', 'expiry', 'strike', 'type',
            'ltp', 'open', 'high', 'low', 'close', 'change', 'change_pct',
            'oi', 'volume', 'iv', 'delta', 'gamma', 'theta', 'vega'
        ])
        file_handle.flush()

    key = f"{strike}_{opt_type}"
    option_writers[key] = {'writer': writer, 'handle': file_handle}

    return writer

def save_spot_tick(timestamp):
    """Save spot tick to CSV"""
    global spot_writer, spot_price, spot_close, spot_open, spot_high, spot_low

    if not SAVE_DATA or spot_writer is None or spot_price <= 0:
        return

    change = spot_price - spot_close if spot_close > 0 else 0
    change_pct = (change / spot_close * 100) if spot_close > 0 else 0

    spot_writer['writer'].writerow([
        timestamp,
        f"{spot_price:.2f}",
        f"{spot_open:.2f}",
        f"{spot_high:.2f}",
        f"{spot_low:.2f}",
        f"{spot_close:.2f}",
        f"{change:+.2f}",
        f"{change_pct:+.2f}"
    ])
    spot_writer['handle'].flush()

def save_futures_tick(timestamp):
    """Save futures tick to CSV"""
    global futures_writer, futures_price, futures_close, futures_symbol
    global futures_open, futures_high, futures_low, futures_oi, futures_volume

    if not SAVE_DATA or futures_writer is None or futures_price <= 0:
        return

    change = futures_price - futures_close if futures_close > 0 else 0
    change_pct = (change / futures_close * 100) if futures_close > 0 else 0

    futures_writer['writer'].writerow([
        timestamp,
        futures_symbol,
        f"{futures_price:.2f}",
        f"{futures_open:.2f}",
        f"{futures_high:.2f}",
        f"{futures_low:.2f}",
        f"{futures_close:.2f}",
        f"{change:+.2f}",
        f"{change_pct:+.2f}",
        futures_oi,
        futures_volume
    ])
    futures_writer['handle'].flush()

def save_option_tick(timestamp, strike, opt_type, data, spot, expiry):
    """Save option tick to CSV"""
    global option_writers

    if not SAVE_DATA:
        return

    key = f"{strike}_{opt_type}"
    if key not in option_writers:
        return

    writer = option_writers[key]['writer']

    ltp = data.get('ltp', 0)
    open_price = data.get('open', 0)
    high = data.get('high', 0)
    low = data.get('low', 0)
    close = data.get('close', 0)
    oi = data.get('oi', 0)
    volume = data.get('volume', 0)

    # Calculate change
    change = ltp - close if close > 0 else 0
    change_pct = (change / close * 100) if close > 0 else 0

    # Calculate Greeks
    try:
        expiry_date = datetime.strptime(expiry, "%d%b%Y")
    except:
        expiry_date = datetime.now() + timedelta(days=4)
    days_to_expiry = max((expiry_date - datetime.now()).days + 1, 1)

    if ltp > 0 and spot > 0:
        greeks = calculate_greeks_for_option(strike, opt_type, ltp, spot, days_to_expiry)
    else:
        greeks = {'iv': 0, 'delta': 0, 'gamma': 0, 'theta': 0, 'vega': 0}

    symbol = f"NIFTY{expiry}{strike}{opt_type}"

    writer.writerow([
        timestamp,
        symbol,
        expiry,
        strike,
        opt_type,
        f"{ltp:.2f}",
        f"{open_price:.2f}",
        f"{high:.2f}",
        f"{low:.2f}",
        f"{close:.2f}",
        f"{change:+.2f}",
        f"{change_pct:+.2f}",
        int(oi / NIFTY_LOT_SIZE),  # OI in contracts
        volume,
        f"{greeks['iv']:.2f}",
        f"{greeks['delta']:.4f}",
        f"{greeks['gamma']:.6f}",
        f"{greeks['theta']:.2f}",
        f"{greeks['vega']:.2f}"
    ])
    option_writers[key]['handle'].flush()

def flush_all_files():
    """Flush all file buffers to disk"""
    global spot_writer, futures_writer, option_writers

    try:
        if spot_writer:
            spot_writer['handle'].flush()
    except:
        pass

    try:
        if futures_writer:
            futures_writer['handle'].flush()
    except:
        pass

    for _, data in option_writers.items():
        try:
            data['handle'].flush()
        except:
            pass

def close_all_files():
    """Close all open file handles"""
    global spot_writer, futures_writer, option_writers

    # Close spot file
    try:
        if spot_writer:
            spot_writer['handle'].close()
    except:
        pass

    # Close futures file
    try:
        if futures_writer:
            futures_writer['handle'].close()
    except:
        pass

    # Close all option files
    for _, data in option_writers.items():
        try:
            data['handle'].close()
        except:
            pass

    option_writers = {}

def calculate_greeks_for_option(strike, opt_type, ltp, spot, days_to_expiry):
    """Calculate all Greeks for an option"""
    T = max(days_to_expiry / 365, 0.0001)

    # Calculate IV first
    iv = implied_volatility(ltp, spot, strike, T, RISK_FREE_RATE, opt_type)

    if iv <= 0:
        iv = 0.15  # Default IV

    # Calculate Greeks
    delta = calculate_delta(spot, strike, T, RISK_FREE_RATE, iv, opt_type)
    gamma = calculate_gamma(spot, strike, T, RISK_FREE_RATE, iv)
    theta = calculate_theta(spot, strike, T, RISK_FREE_RATE, iv, opt_type)
    vega = calculate_vega(spot, strike, T, RISK_FREE_RATE, iv)

    return {
        'iv': iv * 100,  # Convert to percentage
        'delta': delta,
        'gamma': gamma,
        'theta': theta,
        'vega': vega
    }

def display_option_chain(option_tokens, strikes, spot, expiry):
    """Display the option chain with all data"""
    global option_data, futures_price, futures_close, spot_close

    # Calculate days to expiry
    try:
        expiry_date = datetime.strptime(expiry, "%d%b%Y")
    except:
        expiry_date = datetime.now() + timedelta(days=4)
    days_to_expiry = max((expiry_date - datetime.now()).days + 1, 1)

    atm_strike = calculate_atm_strike(spot)

    # Calculate spot change
    spot_chg = spot - spot_close if spot_close > 0 else 0
    spot_chg_pct = (spot_chg / spot_close * 100) if spot_close > 0 else 0

    # Calculate futures change
    fut_chg = futures_price - futures_close if futures_close > 0 else 0
    fut_chg_pct = (fut_chg / futures_close * 100) if futures_close > 0 else 0

    clear_screen()

    print("=" * 140)
    print(f"{'NIFTY OPTION CHAIN - LIVE':^140}")
    spot_str = f"Spot: {spot:.2f} ({spot_chg:+.2f} {spot_chg_pct:+.2f}%)"
    fut_str = f"Fut: {futures_price:.2f} ({fut_chg:+.2f} {fut_chg_pct:+.2f}%)"
    header_info = f"{spot_str} | {fut_str} | ATM: {atm_strike} | Expiry: {expiry} | DTE: {days_to_expiry}"
    print(f"{header_info:^140}")
    print("=" * 140)

    # Header
    print(f"{'':=^140}")
    print(f"{'CALLS':^65}|{'STRIKE':^10}|{'PUTS':^65}")
    print(f"{'':=^140}")
    print(f"{'IV%':>8}{'Delta':>8}{'Gamma':>8}{'Theta':>8}{'Vega':>7}{'OI':>10}{'LTP':>10}{'Chg%':>7}|{'':^10}|{'LTP':>10}{'Chg%':>7}{'OI':>10}{'Vega':>7}{'Theta':>8}{'Gamma':>8}{'Delta':>8}{'IV%':>8}")
    print(f"{'':=^140}")

    # Data rows
    for strike in sorted(strikes, reverse=True):
        # Get CE data
        ce_token = option_tokens['CE'].get(strike, {}).get('token', '')
        ce_data = option_data.get(ce_token, {})
        ce_ltp = ce_data.get('ltp', 0)
        ce_oi = ce_data.get('oi', 0)
        ce_close = ce_data.get('close', ce_ltp)
        ce_chg = ((ce_ltp - ce_close) / ce_close * 100) if ce_close > 0 else 0

        # Get PE data
        pe_token = option_tokens['PE'].get(strike, {}).get('token', '')
        pe_data = option_data.get(pe_token, {})
        pe_ltp = pe_data.get('ltp', 0)
        pe_oi = pe_data.get('oi', 0)
        pe_close = pe_data.get('close', pe_ltp)
        pe_chg = ((pe_ltp - pe_close) / pe_close * 100) if pe_close > 0 else 0

        # Calculate Greeks
        if ce_ltp > 0 and spot > 0:
            ce_greeks = calculate_greeks_for_option(strike, 'CE', ce_ltp, spot, days_to_expiry)
        else:
            ce_greeks = {'iv': 0, 'delta': 0, 'gamma': 0, 'theta': 0, 'vega': 0}

        if pe_ltp > 0 and spot > 0:
            pe_greeks = calculate_greeks_for_option(strike, 'PE', pe_ltp, spot, days_to_expiry)
        else:
            pe_greeks = {'iv': 0, 'delta': 0, 'gamma': 0, 'theta': 0, 'vega': 0}

        # Format strike (highlight ATM)
        strike_str = f"*{strike}*" if strike == atm_strike else str(strike)

        # Format OI in K/L (OI comes in quantity, convert to contracts)
        def format_oi(oi):
            contracts = oi / NIFTY_LOT_SIZE
            if contracts >= 100000:
                return f"{contracts/100000:.1f}L"
            elif contracts >= 1000:
                return f"{contracts/1000:.0f}K"
            elif contracts > 0:
                return f"{contracts:.0f}"
            return "0"

        # ITM highlighting
        ce_itm = ">" if strike < atm_strike else " "
        pe_itm = "<" if strike > atm_strike else " "

        print(f"{ce_greeks['iv']:>7.1f}%{ce_greeks['delta']:>8.3f}{ce_greeks['gamma']:>8.4f}{ce_greeks['theta']:>8.2f}{ce_greeks['vega']:>7.2f}{format_oi(ce_oi):>10}{ce_ltp:>10.2f}{ce_chg:>+7.1f}|{strike_str:^10}|{pe_ltp:>10.2f}{pe_chg:>+7.1f}{format_oi(pe_oi):>10}{pe_greeks['vega']:>7.2f}{pe_greeks['theta']:>8.2f}{pe_greeks['gamma']:>8.4f}{pe_greeks['delta']:>8.3f}{pe_greeks['iv']:>7.1f}%")

    print("=" * 140)
    print(f"Last Update: {datetime.now().strftime('%H:%M:%S.%f')[:-3]} | Ticks: {len(option_data)} options | Press Ctrl+C to exit")


def check_data_server():
    """Check if data server is running"""
    try:
        response = requests.get(f"{DATA_SERVER_URL}/health", timeout=2)
        if response.status_code == 200:
            return True
    except:
        pass
    return False


def fetch_all_data_from_server():
    """Fetch all data from data server"""
    try:
        response = requests.get(f"{DATA_SERVER_URL}/all", timeout=1)
        if response.status_code == 200:
            return response.json()
    except:
        pass
    return None


def polling_thread_func(option_tokens, strikes, expiry, token_to_strike):
    """Background thread to poll data from server"""
    global spot_price, option_data, futures_price, futures_close
    global futures_open, futures_high, futures_low, futures_oi, futures_volume
    global spot_close

    last_display_time = 0

    while True:
        try:
            all_data = fetch_all_data_from_server()
            if all_data:
                tick_timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]

                # Update spot
                spot_data = all_data.get('spot', {})
                if spot_data.get('ltp', 0) > 0:
                    spot_price = spot_data['ltp']
                    if spot_data.get('close', 0) > 0:
                        spot_close = spot_data['close']
                    if SAVE_DATA:
                        save_spot_tick(tick_timestamp)

                # Update futures
                futures_data = all_data.get('futures', {})
                if futures_data.get('ltp', 0) > 0:
                    futures_price = futures_data['ltp']
                    if futures_data.get('close', 0) > 0:
                        futures_close = futures_data['close']
                    if futures_data.get('open', 0) > 0:
                        futures_open = futures_data['open']
                    if futures_data.get('high', 0) > 0:
                        futures_high = futures_data['high']
                    if futures_data.get('low', 0) > 0:
                        futures_low = futures_data['low']
                    if futures_data.get('oi', 0) > 0:
                        futures_oi = futures_data['oi']
                    if futures_data.get('volume', 0) > 0:
                        futures_volume = futures_data['volume']
                    if SAVE_DATA:
                        save_futures_tick(tick_timestamp)

                # Update options
                options_data = all_data.get('options', {})
                for token, data in options_data.items():
                    option_data[token] = data
                    if SAVE_DATA and token in token_to_strike:
                        opt_type, strike = token_to_strike[token]
                        save_option_tick(tick_timestamp, strike, opt_type, data, spot_price, expiry)

                # Update display (with minimum 100ms gap)
                current_time = time.time()
                if current_time - last_display_time >= 0.1:
                    last_display_time = current_time
                    display_option_chain(option_tokens, strikes, spot_price, expiry)

            time.sleep(0.1)  # 100ms polling interval
        except Exception as e:
            time.sleep(0.5)


def run_option_chain():
    """Main function to run the option chain"""
    global spot_price, option_data, futures_token, futures_symbol, current_expiry

    print("=" * 140)
    print("NIFTY OPTION CHAIN - LIVE".center(140))
    print("(Using Central Data Server)".center(140))
    print("=" * 140)

    # Check data server
    print("Checking data server...")
    if not check_data_server():
        print("\nERROR: Data server not running!")
        print("Please start data_server.py first:")
        print("  python3 data_server.py")
        print("\nThen run this option chain again.")
        return

    print("Data server connected!")

    # Get initial data from server
    all_data = fetch_all_data_from_server()
    if not all_data:
        print("Failed to get data from server")
        return

    # Get spot price
    spot_data = all_data.get('spot', {})
    spot_price = spot_data.get('ltp', 0)
    if spot_price <= 0:
        print("Failed to get NIFTY spot price")
        return

    print(f"NIFTY Spot: {spot_price}")

    # Calculate ATM
    atm_strike = calculate_atm_strike(spot_price)
    print(f"ATM Strike: {atm_strike}")

    # Get futures info
    futures_data = all_data.get('futures', {})
    futures_symbol = futures_data.get('symbol', 'NIFTY FUT')
    futures_token = futures_data.get('token', '')
    print(f"Futures: {futures_symbol}")

    # Get expiry from data server (actual expiry from token data)
    expiry = all_data.get('expiry', '')
    if not expiry:
        print("Failed to get expiry from server")
        return
    current_expiry = expiry
    print(f"Expiry: {expiry}")

    # Generate strikes around ATM
    strikes = []
    for i in range(-NUM_STRIKES, NUM_STRIKES + 1):
        strikes.append(atm_strike + (i * STRIKE_INTERVAL))

    # Build option_tokens from server data
    option_tokens = {'CE': {}, 'PE': {}}
    token_to_strike = {}

    options_data = all_data.get('options', {})
    for token, data in options_data.items():
        option_data[token] = data
        opt_type = data.get('type', '')
        strike = data.get('strike', 0)
        if opt_type in ['CE', 'PE'] and strike in strikes:
            option_tokens[opt_type][strike] = {
                'token': token,
                'symbol': data.get('symbol', '')
            }
            token_to_strike[token] = (opt_type, strike)

    print(f"Loaded {len(option_tokens['CE'])} CE + {len(option_tokens['PE'])} PE options")

    # Initialize data storage
    if SAVE_DATA:
        print("\nInitializing data storage...")
        date_folder, options_folder = create_data_folders(expiry)
        print(f"Data folder: {date_folder}")

        # Initialize spot and futures files
        init_spot_file(date_folder)
        init_futures_file(date_folder)

        # Initialize option files for each strike
        for strike in strikes:
            init_option_file(options_folder, strike, 'CE', expiry)
            init_option_file(options_folder, strike, 'PE', expiry)
        print(f"Initialized {len(strikes) * 2} option files")

    # Start polling thread
    print("\nStarting data polling...")
    poll_thread = threading.Thread(
        target=polling_thread_func,
        args=(option_tokens, strikes, expiry, token_to_strike),
        daemon=True
    )
    poll_thread.start()

    # Wait for initial data
    print("Waiting for data...")
    time.sleep(2)

    # Initial display
    display_option_chain(option_tokens, strikes, spot_price, expiry)

    # Keep running until Ctrl+C
    try:
        while True:
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\n\nExiting...")

        # Close all data files
        if SAVE_DATA:
            print("Closing data files...")
            close_all_files()
            print("Data files saved.")

        print("Done.")


if __name__ == "__main__":
    run_option_chain()
