#!/usr/bin/env python3
"""
NIFTY GEX (Gamma Exposure) Dashboard
Strike-wise GEX, Net GEX, Vega Analysis
"""

import json
import threading
import time
import math
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.animation import FuncAnimation
import numpy as np
import requests
from datetime import datetime, timedelta

# Data Server Configuration
DATA_SERVER_URL = "http://127.0.0.1:8888"

# NIFTY Configuration
NIFTY_TOKEN = "99926000"
STRIKE_INTERVAL = 50
NUM_STRIKES = 15  # ±15 strikes for better GEX view
RISK_FREE_RATE = 0.065  # 6.5% risk-free rate (RBI repo rate)
NIFTY_LOT_SIZE = 75

# Global storage
option_data = {}
spot_price = 0
spot_close = 0
current_expiry = ""
option_tokens = {'CE': {}, 'PE': {}}
strikes = []
gex_data = {}  # Store calculated GEX per strike
previous_gex = {}  # Store previous GEX values to handle data gaps


# ============== BLACK-SCHOLES FUNCTIONS ==============

def norm_cdf(x):
    return (1.0 + math.erf(x / math.sqrt(2.0))) / 2.0

def norm_pdf(x):
    return math.exp(-0.5 * x * x) / math.sqrt(2 * math.pi)

def calculate_d1_d2(S, K, T, r, sigma):
    if T <= 0 or sigma <= 0:
        return 0, 0
    d1 = (math.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * math.sqrt(T))
    d2 = d1 - sigma * math.sqrt(T)
    return d1, d2

def bs_price(S, K, T, r, sigma, option_type):
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

def calculate_gamma(S, K, T, r, sigma):
    if T <= 0 or sigma <= 0:
        return 0
    d1, _ = calculate_d1_d2(S, K, T, r, sigma)
    return norm_pdf(d1) / (S * sigma * math.sqrt(T))

def calculate_vega(S, K, T, r, sigma):
    if T <= 0 or sigma <= 0:
        return 0
    d1, _ = calculate_d1_d2(S, K, T, r, sigma)
    return S * norm_pdf(d1) * math.sqrt(T) / 100


# ============== GEX CALCULATION ==============

def calculate_gex(gamma, oi_contracts, spot, contract_size=NIFTY_LOT_SIZE):
    """
    Calculate Gamma Exposure (GEX) - Standard Formula
    GEX = Gamma × OI (contracts) × Contract_Size × Spot² × 0.01
    Returns value in Crores for readability
    """
    if gamma <= 0 or oi_contracts <= 0 or spot <= 0:
        return 0
    gex = gamma * oi_contracts * contract_size * (spot ** 2) * 0.01
    return gex / 10000000  # Convert to Crores


def calculate_all_gex(spot, days_to_expiry):
    """Calculate GEX for all strikes"""
    global gex_data, option_data, option_tokens, previous_gex

    T = max(days_to_expiry / 365, 0.0001)
    gex_data = {}

    for strike in strikes:
        ce_token = option_tokens['CE'].get(strike, {}).get('token', '')
        pe_token = option_tokens['PE'].get(strike, {}).get('token', '')

        ce_data = option_data.get(ce_token, {})
        pe_data = option_data.get(pe_token, {})

        ce_ltp = ce_data.get('ltp', 0)
        pe_ltp = pe_data.get('ltp', 0)
        ce_oi_qty = ce_data.get('oi', 0)  # Raw OI in quantity
        pe_oi_qty = pe_data.get('oi', 0)  # Raw OI in quantity

        # Convert OI to contracts
        ce_oi = ce_oi_qty / NIFTY_LOT_SIZE
        pe_oi = pe_oi_qty / NIFTY_LOT_SIZE

        # If no OI data for both CE and PE, use previous values
        if ce_oi == 0 and pe_oi == 0:
            if strike in previous_gex:
                gex_data[strike] = previous_gex[strike]
            continue

        # Calculate IV
        ce_iv = implied_volatility(ce_ltp, spot, strike, T, RISK_FREE_RATE, 'CE') if ce_ltp > 0 else 0.15
        pe_iv = implied_volatility(pe_ltp, spot, strike, T, RISK_FREE_RATE, 'PE') if pe_ltp > 0 else 0.15

        # Calculate Gamma
        ce_gamma = calculate_gamma(spot, strike, T, RISK_FREE_RATE, ce_iv)
        pe_gamma = calculate_gamma(spot, strike, T, RISK_FREE_RATE, pe_iv)

        # Calculate Vega
        ce_vega = calculate_vega(spot, strike, T, RISK_FREE_RATE, ce_iv)
        pe_vega = calculate_vega(spot, strike, T, RISK_FREE_RATE, pe_iv)

        # Calculate GEX (OI is now in contracts)
        # Call GEX is positive (dealers are long gamma)
        # Put GEX is negative (dealers are short gamma from puts)
        call_gex = calculate_gex(ce_gamma, ce_oi, spot)
        put_gex = calculate_gex(pe_gamma, pe_oi, spot)

        # Net GEX = Call GEX - Put GEX (from dealer perspective)
        net_gex = call_gex - put_gex

        # Vega Exposure (OI already in contracts)
        call_vex = ce_vega * ce_oi * NIFTY_LOT_SIZE / 10000000  # In Crores
        put_vex = pe_vega * pe_oi * NIFTY_LOT_SIZE / 10000000

        gex_data[strike] = {
            'call_gex': call_gex,
            'put_gex': put_gex,
            'net_gex': net_gex,
            'call_vega': ce_vega * ce_oi,  # Vega exposure
            'put_vega': pe_vega * pe_oi,   # Vega exposure
            'call_vex': call_vex,
            'put_vex': put_vex,
            'call_oi': ce_oi,  # Already in contracts
            'put_oi': pe_oi,   # Already in contracts
            'call_gamma': ce_gamma,
            'put_gamma': pe_gamma
        }

        # Store for future use
        previous_gex[strike] = gex_data[strike]

    return gex_data


# ============== ANGEL ONE CONNECTION ==============

def login():
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
    return round(spot / STRIKE_INTERVAL) * STRIKE_INTERVAL

def get_current_expiry(all_tokens):
    nifty_opts = [t for t in all_tokens
                  if t.get('exch_seg') == 'NFO'
                  and 'NIFTY' in t.get('symbol', '')
                  and t.get('instrumenttype') == 'OPTIDX'
                  and 'BANKNIFTY' not in t.get('symbol', '')]
    expiries = set(t.get('expiry', '') for t in nifty_opts)
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
    token_file = "/Users/harsh/Desktop/test 1/angelone_tokens.json"
    try:
        with open(token_file, 'r') as f:
            return json.load(f)
    except:
        print("Downloading token file...")
        url = "https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json"
        response = requests.get(url, timeout=60)
        return response.json()

def load_option_tokens(all_tokens, expiry, atm_strike):
    global option_tokens, strikes
    print(f"\nLoading tokens for expiry: {expiry}, ATM: {atm_strike}")

    strikes = []
    for i in range(-NUM_STRIKES, NUM_STRIKES + 1):
        strikes.append(atm_strike + (i * STRIKE_INTERVAL))

    option_tokens = {'CE': {}, 'PE': {}}

    for token in all_tokens:
        if token.get('exch_seg') != 'NFO':
            continue
        if token.get('instrumenttype') != 'OPTIDX':
            continue
        symbol = token.get('symbol', '')
        if not symbol.startswith('NIFTY') or 'BANKNIFTY' in symbol:
            continue
        token_expiry = token.get('expiry', '')
        if token_expiry != expiry:
            continue
        try:
            strike_str = token.get('strike', '0')
            strike = int(float(strike_str) / 100)
            if strike in strikes:
                if symbol.endswith('CE'):
                    option_tokens['CE'][strike] = {
                        'token': token['token'],
                        'symbol': symbol
                    }
                elif symbol.endswith('PE'):
                    option_tokens['PE'][strike] = {
                        'token': token['token'],
                        'symbol': symbol
                    }
        except:
            continue

    print(f"Found {len(option_tokens['CE'])} CE and {len(option_tokens['PE'])} PE options")
    return option_tokens, strikes


# ============== DATA SERVER FUNCTIONS ==============

def check_data_server():
    """Check if data server is running"""
    try:
        response = requests.get(f"{DATA_SERVER_URL}/health", timeout=2)
        if response.status_code == 200:
            return True
    except:
        pass
    return False


def fetch_spot_from_server():
    """Fetch spot price from data server"""
    try:
        response = requests.get(f"{DATA_SERVER_URL}/spot", timeout=1)
        if response.status_code == 200:
            return response.json()
    except:
        pass
    return None


def fetch_options_from_server():
    """Fetch all options data from data server"""
    try:
        response = requests.get(f"{DATA_SERVER_URL}/options", timeout=1)
        if response.status_code == 200:
            return response.json()
    except:
        pass
    return None


# ============== MATPLOTLIB DASHBOARD ==============

def create_dashboard():
    """Create the matplotlib figure with subplots"""
    plt.style.use('dark_background')
    fig = plt.figure(figsize=(16, 10))
    fig.suptitle('NIFTY GEX Dashboard', fontsize=16, fontweight='bold', color='white')

    # Create grid
    gs = fig.add_gridspec(3, 2, height_ratios=[2, 2, 1], hspace=0.3, wspace=0.25)

    # Subplot 1: Strike-wise GEX (top left)
    ax1 = fig.add_subplot(gs[0, 0])
    ax1.set_title('GEX by Strike', fontsize=12, fontweight='bold')

    # Subplot 2: Net GEX horizontal (top right)
    ax2 = fig.add_subplot(gs[0, 1])
    ax2.set_title('Net GEX (Total GEX)', fontsize=12, fontweight='bold')

    # Subplot 3: OI Chart (middle left)
    ax3 = fig.add_subplot(gs[1, 0])
    ax3.set_title('Open Interest by Strike', fontsize=12, fontweight='bold')

    # Subplot 4: Gamma Chart (middle right)
    ax4 = fig.add_subplot(gs[1, 1])
    ax4.set_title('Gamma by Strike', fontsize=12, fontweight='bold')

    # Subplot 5: Summary bars (bottom - spans both columns)
    ax5 = fig.add_subplot(gs[2, :])
    ax5.set_title('Summary Totals', fontsize=12, fontweight='bold')

    plt.tight_layout()
    return fig, (ax1, ax2, ax3, ax4, ax5)


def update_dashboard(frame, axes, expiry):
    """Update dashboard with latest data"""
    global spot_price, gex_data, strikes

    ax1, ax2, ax3, ax4, ax5 = axes

    if spot_price <= 0 or not option_data:
        return

    # Calculate days to expiry
    try:
        expiry_date = datetime.strptime(expiry, "%d%b%Y")
    except:
        expiry_date = datetime.now() + timedelta(days=4)
    days_to_expiry = max((expiry_date - datetime.now()).days + 1, 1)

    # Recalculate GEX
    calculate_all_gex(spot_price, days_to_expiry)

    atm_strike = calculate_atm_strike(spot_price)

    # Prepare data
    sorted_strikes = sorted(strikes)
    call_gex = [gex_data.get(s, {}).get('call_gex', 0) for s in sorted_strikes]
    put_gex = [gex_data.get(s, {}).get('put_gex', 0) for s in sorted_strikes]
    net_gex = [gex_data.get(s, {}).get('net_gex', 0) for s in sorted_strikes]
    call_oi = [gex_data.get(s, {}).get('call_oi', 0) for s in sorted_strikes]
    put_oi = [gex_data.get(s, {}).get('put_oi', 0) for s in sorted_strikes]
    call_vega = [gex_data.get(s, {}).get('call_vega', 0) for s in sorted_strikes]
    put_vega = [gex_data.get(s, {}).get('put_vega', 0) for s in sorted_strikes]
    call_vex = [gex_data.get(s, {}).get('call_vex', 0) for s in sorted_strikes]
    put_vex = [gex_data.get(s, {}).get('put_vex', 0) for s in sorted_strikes]

    x = np.arange(len(sorted_strikes))
    width = 0.35

    # ===== Plot 1: GEX Bar Chart =====
    ax1.clear()
    ax1.bar(x - width/2, put_gex, width, label='Put GEX', color='#4A90D9', alpha=0.8)
    ax1.bar(x + width/2, call_gex, width, label='Call GEX', color='#D94A4A', alpha=0.8)
    ax1.set_xlabel('Strike')
    ax1.set_ylabel('GEX (Cr)')
    ax1.set_title(f'GEX by Strike | Spot: {spot_price:.2f} | ATM: {atm_strike}', fontsize=11, fontweight='bold')
    ax1.set_xticks(x[::2])
    ax1.set_xticklabels([str(s) for s in sorted_strikes[::2]], rotation=45, fontsize=8)
    ax1.legend(loc='upper right', fontsize=8)
    ax1.axvline(x=sorted_strikes.index(atm_strike) if atm_strike in sorted_strikes else len(x)//2,
                color='yellow', linestyle='--', linewidth=1, alpha=0.7)
    ax1.grid(axis='y', alpha=0.3)

    # ===== Plot 2: Net GEX Horizontal =====
    ax2.clear()
    colors = ['#4A90D9' if g < 0 else '#D94A4A' for g in net_gex]
    y_pos = np.arange(len(sorted_strikes))
    ax2.barh(y_pos, net_gex, color=colors, alpha=0.8)
    ax2.set_yticks(y_pos[::2])
    ax2.set_yticklabels([str(s) for s in sorted_strikes[::2]], fontsize=8)
    ax2.set_xlabel('Net GEX (Cr)')
    ax2.set_title(f'Net GEX | DTE: {days_to_expiry}', fontsize=11, fontweight='bold')
    ax2.axvline(x=0, color='white', linewidth=0.5)
    ax2.grid(axis='x', alpha=0.3)

    # Highlight max positive and negative
    if net_gex:
        max_idx = net_gex.index(max(net_gex))
        min_idx = net_gex.index(min(net_gex))
        ax2.barh(max_idx, net_gex[max_idx], color='#00FF00', alpha=0.9)
        ax2.barh(min_idx, net_gex[min_idx], color='#FF6600', alpha=0.9)

    # ===== Plot 3: OI Chart =====
    ax3.clear()
    ax3.bar(x - width/2, put_oi, width, label='Put OI', color='#4A90D9', alpha=0.8)
    ax3.bar(x + width/2, call_oi, width, label='Call OI', color='#D94A4A', alpha=0.8)
    ax3.set_xlabel('Strike')
    ax3.set_ylabel('OI (Contracts)')
    ax3.set_title('Open Interest by Strike', fontsize=11, fontweight='bold')
    ax3.set_xticks(x[::2])
    ax3.set_xticklabels([str(s) for s in sorted_strikes[::2]], rotation=45, fontsize=8)
    ax3.legend(loc='upper right', fontsize=8)
    ax3.axvline(x=sorted_strikes.index(atm_strike) if atm_strike in sorted_strikes else len(x)//2,
                color='yellow', linestyle='--', linewidth=1, alpha=0.7)
    ax3.grid(axis='y', alpha=0.3)

    # Format OI in K
    ax3.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x/1000:.0f}K' if x >= 1000 else f'{x:.0f}'))

    # ===== Plot 4: Vega Chart =====
    ax4.clear()
    ax4.bar(x - width/2, put_vega, width, label='Put Vega', color='#4A90D9', alpha=0.8)
    ax4.bar(x + width/2, call_vega, width, label='Call Vega', color='#D94A4A', alpha=0.8)
    ax4.set_xlabel('Strike')
    ax4.set_ylabel('Vega')
    ax4.set_title('Vega by Strike', fontsize=11, fontweight='bold')
    ax4.set_xticks(x[::2])
    ax4.set_xticklabels([str(s) for s in sorted_strikes[::2]], rotation=45, fontsize=8)
    ax4.legend(loc='upper right', fontsize=8)
    ax4.grid(axis='y', alpha=0.3)

    # ===== Plot 5: Summary Totals =====
    ax5.clear()

    total_call_gex = sum(call_gex)
    total_put_gex = sum(put_gex)
    total_net_gex = sum(net_gex)
    total_call_vega = sum(call_vega)
    total_put_vega = sum(put_vega)
    total_call_vex = sum(call_vex)
    total_put_vex = sum(put_vex)

    categories = ['GEX (Cr)', 'Vega', 'VEX (Cr)']
    put_values = [total_put_gex, total_put_vega, total_put_vex]
    call_values = [total_call_gex, total_call_vega, total_call_vex]

    y_pos = np.arange(len(categories))
    height = 0.35

    bars1 = ax5.barh(y_pos - height/2, put_values, height, label='Put', color='#4A90D9', alpha=0.8)
    bars2 = ax5.barh(y_pos + height/2, call_values, height, label='Call', color='#D94A4A', alpha=0.8)

    ax5.set_yticks(y_pos)
    ax5.set_yticklabels(categories)
    ax5.set_xlabel('Value')
    ax5.legend(loc='upper right', fontsize=8)
    ax5.grid(axis='x', alpha=0.3)

    # Add value labels
    for bar, val in zip(bars1, put_values):
        ax5.text(bar.get_width() + 0.5, bar.get_y() + bar.get_height()/2,
                f'{val:.2f}', va='center', fontsize=9, color='#4A90D9')
    for bar, val in zip(bars2, call_values):
        ax5.text(bar.get_width() + 0.5, bar.get_y() + bar.get_height()/2,
                f'{val:.2f}', va='center', fontsize=9, color='#D94A4A')

    # Add Net GEX text
    ax5.text(0.98, 0.95, f'Net GEX: {total_net_gex:.2f} Cr', transform=ax5.transAxes,
             fontsize=11, fontweight='bold', color='#00FF00' if total_net_gex > 0 else '#FF6600',
             ha='right', va='top')

    # Update timestamp
    plt.suptitle(f'NIFTY GEX Dashboard | {datetime.now().strftime("%H:%M:%S")} | Expiry: {expiry}',
                 fontsize=14, fontweight='bold', color='white')


def polling_thread_func():
    """Background thread to poll data from server"""
    global spot_price, option_data

    while True:
        try:
            # Fetch spot price
            spot_data = fetch_spot_from_server()
            if spot_data and spot_data.get('ltp', 0) > 0:
                spot_price = spot_data['ltp']

            # Fetch options data
            options_data = fetch_options_from_server()
            if options_data:
                # Update option_data with server data
                for token, data in options_data.items():
                    if token not in option_data:
                        option_data[token] = {}
                    option_data[token].update(data)

            time.sleep(0.5)  # 500ms polling interval
        except Exception as e:
            time.sleep(1)


def run_gex_dashboard():
    """Main function to run GEX dashboard"""
    global spot_price, option_data, current_expiry, option_tokens, strikes

    print("=" * 70)
    print("NIFTY GEX DASHBOARD".center(70))
    print("(Using Central Data Server)".center(70))
    print("=" * 70)

    # Check data server
    print("Checking data server...")
    if not check_data_server():
        print("\nERROR: Data server not running!")
        print("Please start data_server.py first:")
        print("  python3 data_server.py")
        print("\nThen run this dashboard again.")
        return

    print("Data server connected!")

    # Get spot price from server
    spot_data = fetch_spot_from_server()
    if spot_data and spot_data.get('ltp', 0) > 0:
        spot_price = spot_data['ltp']
    else:
        print("Failed to get NIFTY spot price from server")
        return

    print(f"NIFTY Spot: {spot_price}")
    atm_strike = calculate_atm_strike(spot_price)
    print(f"ATM Strike: {atm_strike}")

    # Get expiry from data server (actual expiry from token data)
    try:
        response = requests.get(f"{DATA_SERVER_URL}/all", timeout=2)
        if response.status_code == 200:
            all_data = response.json()
            current_expiry = all_data.get('expiry', '')
            if not current_expiry:
                print("Failed to get expiry from server")
                return
    except Exception as e:
        print(f"Failed to get expiry: {e}")
        return

    print(f"Expiry: {current_expiry}")

    # Generate strikes around ATM
    strikes = []
    for i in range(-NUM_STRIKES, NUM_STRIKES + 1):
        strikes.append(atm_strike + (i * STRIKE_INTERVAL))

    # Initialize option_tokens from server data
    option_tokens = {'CE': {}, 'PE': {}}

    # Fetch options and map to strikes
    options_data = fetch_options_from_server()
    if options_data:
        for token, data in options_data.items():
            option_data[token] = data
            # Map token to option_tokens based on strike and type
            opt_type = data.get('type', '')
            strike = data.get('strike', 0)
            if opt_type in ['CE', 'PE'] and strike in strikes:
                option_tokens[opt_type][strike] = {
                    'token': token,
                    'symbol': data.get('symbol', '')
                }

    print(f"Loaded {len(option_tokens['CE'])} CE + {len(option_tokens['PE'])} PE options from server")

    # Start polling thread
    print("Starting data polling...")
    poll_thread = threading.Thread(target=polling_thread_func, daemon=True)
    poll_thread.start()

    # Wait for data
    print("Waiting for data...")
    time.sleep(3)

    # Check data availability
    options_with_oi = sum(1 for data in option_data.values() if data.get('oi', 0) > 0)
    print(f"Options with OI: {options_with_oi}")

    # Create dashboard
    print("Starting GEX Dashboard...")
    fig, axes = create_dashboard()

    # Animation for live updates (every 2 seconds)
    ani = FuncAnimation(fig, update_dashboard, fargs=(axes, current_expiry),
                       interval=2000, cache_frame_data=False)

    try:
        plt.show()
    except KeyboardInterrupt:
        pass
    finally:
        print("\nClosing...")
        print("Done.")


if __name__ == "__main__":
    run_gex_dashboard()
