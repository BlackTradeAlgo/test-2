#!/usr/bin/env python3
"""
NIFTY Web-Style GEX Dashboard
Implements website-style GEX calculation with:
- Futures-based underlying
- Trading minutes time calculation
- Implied dividend yield
- IV skew from ATM
- Sign convention: Call GEX (+), Put GEX (-)
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

# Import configuration
from config.settings import (
    DATA_SERVER_URL,
    NIFTY_TOKEN,
    NIFTY_LOT_SIZE,
    STRIKE_INTERVAL,
    RISK_FREE_RATE,
    TRADING_DAYS_PER_YEAR,
    TRADING_MINUTES_PER_DAY
)

# Local override (this dashboard needs more strikes)
NUM_STRIKES = 15  # +/- 15 strikes for GEX dashboard

# Global storage
option_data = {}
spot_price = 0
futures_price = 0
current_expiry = ""
option_tokens = {'CE': {}, 'PE': {}}
strikes = []
gex_data = {}
previous_gex = {}
atm_iv = 0.15  # Default ATM IV (will be calculated)


# ============== WEBSITE-STYLE FUNCTIONS ==============

def norm_cdf(x):
    """Standard normal CDF"""
    return (1.0 + math.erf(x / math.sqrt(2.0))) / 2.0


def norm_pdf(x):
    """Standard normal PDF"""
    return math.exp(-0.5 * x * x) / math.sqrt(2 * math.pi)


def calculate_time_to_expiry_minutes(expiry_str):
    """
    Calculate time to expiry in years using trading minutes
    T = remaining_minutes / (252 * 375)

    Trading day = 9:15 AM to 3:30 PM = 375 minutes
    """
    try:
        expiry_date = datetime.strptime(expiry_str, "%d%b%Y")
        # Set expiry time to 3:30 PM
        expiry_datetime = expiry_date.replace(hour=15, minute=30, second=0)
    except:
        return 0.01  # Fallback

    now = datetime.now()

    # If today is expiry day
    if now.date() == expiry_date.date():
        # Calculate remaining minutes today until 3:30 PM
        if now.hour < 9 or (now.hour == 9 and now.minute < 15):
            # Before market open - full trading day remaining
            remaining_minutes = 375
        elif now.hour >= 15 and now.minute >= 30:
            # After market close
            remaining_minutes = 1  # Minimum
        else:
            # During market hours
            market_close = now.replace(hour=15, minute=30, second=0)
            remaining_minutes = max(1, (market_close - now).total_seconds() / 60)
    else:
        # Days until expiry (excluding today)
        days_remaining = (expiry_date.date() - now.date()).days

        # Today's remaining minutes
        if now.hour < 9 or (now.hour == 9 and now.minute < 15):
            today_minutes = 375  # Full day
        elif now.hour >= 15 and now.minute >= 30:
            today_minutes = 0  # Day over
        else:
            market_close = now.replace(hour=15, minute=30, second=0)
            today_minutes = max(0, (market_close - now).total_seconds() / 60)

        # Total minutes = today's remaining + full trading days * 375
        # Note: We only count trading days (weekdays) but for simplicity using calendar days
        remaining_minutes = today_minutes + (days_remaining * TRADING_MINUTES_PER_DAY)

    # T = remaining_minutes / (252 * 375)
    T = remaining_minutes / (TRADING_DAYS_PER_YEAR * TRADING_MINUTES_PER_DAY)
    return max(T, 0.00001)  # Minimum T to avoid division by zero


def calculate_implied_dividend_yield(spot, futures, T, r):
    """
    Calculate implied dividend yield from futures price
    q = r - (ln(F/S) / T)
    """
    if T <= 0 or spot <= 0 or futures <= 0:
        return 0

    try:
        q = r - (math.log(futures / spot) / T)
        # Clamp to reasonable range
        return max(0, min(q, 0.05))  # 0% to 5%
    except:
        return 0.012  # Default 1.2%


def bs_d1_d2_with_dividend(S, K, T, r, q, sigma):
    """
    Calculate d1 and d2 for dividend-adjusted Black-Scholes
    d1 = (ln(S/K) + (r - q + 0.5*sigma^2)*T) / (sigma * sqrt(T))
    d2 = d1 - sigma * sqrt(T)
    """
    if T <= 0 or sigma <= 0 or S <= 0 or K <= 0:
        return 0, 0

    sqrt_T = math.sqrt(T)
    d1 = (math.log(S / K) + (r - q + 0.5 * sigma ** 2) * T) / (sigma * sqrt_T)
    d2 = d1 - sigma * sqrt_T
    return d1, d2


def bs_price_with_dividend(S, K, T, r, q, sigma, option_type):
    """
    Black-Scholes price with continuous dividend yield
    Call = S * e^(-qT) * N(d1) - K * e^(-rT) * N(d2)
    Put  = K * e^(-rT) * N(-d2) - S * e^(-qT) * N(-d1)
    """
    if T <= 0:
        if option_type == 'CE':
            return max(0, S - K)
        else:
            return max(0, K - S)

    d1, d2 = bs_d1_d2_with_dividend(S, K, T, r, q, sigma)

    if option_type == 'CE':
        price = S * math.exp(-q * T) * norm_cdf(d1) - K * math.exp(-r * T) * norm_cdf(d2)
    else:
        price = K * math.exp(-r * T) * norm_cdf(-d2) - S * math.exp(-q * T) * norm_cdf(-d1)

    return max(0, price)


def calculate_gamma_index(S, K, T, r, q, sigma):
    """
    Calculate Gamma using dividend-adjusted formula
    Gamma = e^(-qT) * N'(d1) / (S * sigma * sqrt(T))

    Note: Gamma is same for both Call and Put (same strike)
    """
    if T <= 0 or sigma <= 0 or S <= 0:
        return 0

    d1, _ = bs_d1_d2_with_dividend(S, K, T, r, q, sigma)
    sqrt_T = math.sqrt(T)

    gamma = math.exp(-q * T) * norm_pdf(d1) / (S * sigma * sqrt_T)
    return gamma


def implied_volatility_with_dividend(market_price, S, K, T, r, q, option_type, max_iter=100):
    """
    Calculate IV using Bisection method with dividend-adjusted BS
    """
    if T <= 0 or market_price <= 0:
        return 0

    # Calculate intrinsic value
    intrinsic = max(0, S - K) if option_type == 'CE' else max(0, K - S)

    # If market price is less than intrinsic (deep ITM)
    if market_price < intrinsic:
        return 0.01  # 1% IV

    # Bisection method
    low_vol = 0.001
    high_vol = 5.0
    tolerance = max(0.01, market_price * 0.001)

    for _ in range(max_iter):
        mid_vol = (low_vol + high_vol) / 2
        mid_price = bs_price_with_dividend(S, K, T, r, q, mid_vol, option_type)

        diff = mid_price - market_price

        if abs(diff) < tolerance:
            return mid_vol

        if diff > 0:
            high_vol = mid_vol
        else:
            low_vol = mid_vol

        if (high_vol - low_vol) < 0.0001:
            break

    return mid_vol


def get_atm_iv(spot, strikes_list, option_data_dict, option_tokens_dict, T, r, q):
    """
    Calculate ATM IV from the closest ATM strike
    Returns average of ATM Call and ATM Put IV
    """
    atm_strike = round(spot / STRIKE_INTERVAL) * STRIKE_INTERVAL

    # Get ATM Call IV
    ce_token = option_tokens_dict['CE'].get(atm_strike, {}).get('token', '')
    ce_data = option_data_dict.get(ce_token, {})
    ce_ltp = ce_data.get('ltp', 0)

    # Get ATM Put IV
    pe_token = option_tokens_dict['PE'].get(atm_strike, {}).get('token', '')
    pe_data = option_data_dict.get(pe_token, {})
    pe_ltp = pe_data.get('ltp', 0)

    ce_iv = 0.15
    pe_iv = 0.15

    if ce_ltp > 0:
        ce_iv = implied_volatility_with_dividend(ce_ltp, spot, atm_strike, T, r, q, 'CE')

    if pe_ltp > 0:
        pe_iv = implied_volatility_with_dividend(pe_ltp, spot, atm_strike, T, r, q, 'PE')

    # Average ATM IV
    if ce_iv > 0.01 and pe_iv > 0.01:
        return (ce_iv + pe_iv) / 2
    elif ce_iv > 0.01:
        return ce_iv
    elif pe_iv > 0.01:
        return pe_iv
    else:
        return 0.15  # Default


def get_iv_with_skew(strike, atm_strike, atm_iv, skew_factor=0.0008):
    """
    Apply IV skew/smile
    IV(strike) = ATM_IV + skew * (distance / 50)

    skew_factor = 0.0008 (0.08% per 50 points)
    """
    distance = abs(strike - atm_strike)
    iv_adjustment = skew_factor * (distance / 50)

    # Apply skew (both OTM calls and puts have higher IV than ATM)
    return atm_iv + iv_adjustment


def calculate_gex_web_style(gamma, oi_contracts, spot, contract_size=NIFTY_LOT_SIZE):
    """
    Calculate GEX - Website style
    GEX = Gamma * OI (contracts) * Contract_Size * Spot^2 * 0.01
    Returns value in Crores
    """
    if gamma <= 0 or oi_contracts <= 0 or spot <= 0:
        return 0

    gex = gamma * oi_contracts * contract_size * (spot ** 2) * 0.01
    return gex / 10000000  # Convert to Crores


def calculate_all_gex_web_style(spot, futures, expiry):
    """
    Calculate GEX for all strikes using website-style method

    Key differences from standard:
    1. Use futures price for forward
    2. Trading minutes for T
    3. Implied dividend yield
    4. IV skew from ATM
    5. Sign convention: Call GEX (+), Put GEX (-), Net = Call + Put
    """
    global gex_data, option_data, option_tokens, previous_gex, atm_iv

    # Calculate T using trading minutes
    T = calculate_time_to_expiry_minutes(expiry)

    # Calculate implied dividend yield
    q = calculate_implied_dividend_yield(spot, futures, T, RISK_FREE_RATE)

    # Calculate ATM IV
    atm_strike = round(spot / STRIKE_INTERVAL) * STRIKE_INTERVAL
    atm_iv = get_atm_iv(spot, strikes, option_data, option_tokens, T, RISK_FREE_RATE, q)

    gex_data = {}

    for strike in strikes:
        ce_token = option_tokens['CE'].get(strike, {}).get('token', '')
        pe_token = option_tokens['PE'].get(strike, {}).get('token', '')

        ce_data = option_data.get(ce_token, {})
        pe_data = option_data.get(pe_token, {})

        ce_ltp = ce_data.get('ltp', 0)
        pe_ltp = pe_data.get('ltp', 0)
        ce_oi_qty = ce_data.get('oi', 0)
        pe_oi_qty = pe_data.get('oi', 0)

        # Convert OI to contracts
        ce_oi = ce_oi_qty / NIFTY_LOT_SIZE
        pe_oi = pe_oi_qty / NIFTY_LOT_SIZE

        # If no OI data, use previous values
        if ce_oi == 0 and pe_oi == 0:
            if strike in previous_gex:
                gex_data[strike] = previous_gex[strike]
            continue

        # Get IV with skew
        strike_iv = get_iv_with_skew(strike, atm_strike, atm_iv)

        # Calculate IV from market (if available)
        if ce_ltp > 0:
            ce_iv = implied_volatility_with_dividend(ce_ltp, spot, strike, T, RISK_FREE_RATE, q, 'CE')
            if ce_iv > 0.01:
                strike_iv = ce_iv

        if pe_ltp > 0:
            pe_iv = implied_volatility_with_dividend(pe_ltp, spot, strike, T, RISK_FREE_RATE, q, 'PE')
            if pe_iv > 0.01 and ce_ltp <= 0:
                strike_iv = pe_iv

        # Calculate Gamma (same for CE and PE at same strike)
        gamma = calculate_gamma_index(spot, strike, T, RISK_FREE_RATE, q, strike_iv)

        # Calculate GEX with sign convention
        # Call GEX = +ve (dealers long gamma from calls)
        # Put GEX = -ve (dealers short gamma from puts)
        call_gex = calculate_gex_web_style(gamma, ce_oi, spot)
        put_gex = -calculate_gex_web_style(gamma, pe_oi, spot)  # Negative sign

        # Net GEX = Call GEX + Put GEX (with signs)
        net_gex = call_gex + put_gex

        gex_data[strike] = {
            'call_gex': call_gex,
            'put_gex': put_gex,  # Already negative
            'net_gex': net_gex,
            'call_oi': ce_oi,
            'put_oi': pe_oi,
            'gamma': gamma,
            'iv': strike_iv,
            'T': T,
            'q': q
        }

        previous_gex[strike] = gex_data[strike]

    return gex_data


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


def fetch_futures_from_server():
    """Fetch futures price from data server"""
    try:
        response = requests.get(f"{DATA_SERVER_URL}/all", timeout=1)
        if response.status_code == 200:
            data = response.json()
            return data.get('futures_price', 0)
    except:
        pass
    return 0


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
    fig.suptitle('NIFTY Web-Style GEX Dashboard', fontsize=16, fontweight='bold', color='cyan')

    # Create grid
    gs = fig.add_gridspec(3, 2, height_ratios=[2, 2, 1], hspace=0.3, wspace=0.25)

    # Subplot 1: Strike-wise GEX (top left)
    ax1 = fig.add_subplot(gs[0, 0])
    ax1.set_title('GEX by Strike (Web Style)', fontsize=12, fontweight='bold')

    # Subplot 2: Net GEX horizontal (top right)
    ax2 = fig.add_subplot(gs[0, 1])
    ax2.set_title('Net GEX (Call + Put with Signs)', fontsize=12, fontweight='bold')

    # Subplot 3: OI Chart (middle left)
    ax3 = fig.add_subplot(gs[1, 0])
    ax3.set_title('Open Interest by Strike', fontsize=12, fontweight='bold')

    # Subplot 4: IV Chart (middle right)
    ax4 = fig.add_subplot(gs[1, 1])
    ax4.set_title('IV by Strike (with Skew)', fontsize=12, fontweight='bold')

    # Subplot 5: Summary bars (bottom)
    ax5 = fig.add_subplot(gs[2, :])
    ax5.set_title('Summary Totals', fontsize=12, fontweight='bold')

    plt.tight_layout()
    return fig, (ax1, ax2, ax3, ax4, ax5)


def calculate_atm_strike(spot):
    return round(spot / STRIKE_INTERVAL) * STRIKE_INTERVAL


def update_dashboard(frame, axes, expiry):
    """Update dashboard with latest data"""
    global spot_price, futures_price, gex_data, strikes, atm_iv

    ax1, ax2, ax3, ax4, ax5 = axes

    if spot_price <= 0 or not option_data:
        return

    # Use spot if futures not available
    futures_to_use = futures_price if futures_price > 0 else spot_price * 1.001

    # Recalculate GEX using web style
    calculate_all_gex_web_style(spot_price, futures_to_use, expiry)

    atm_strike = calculate_atm_strike(spot_price)

    # Calculate T for display
    T = calculate_time_to_expiry_minutes(expiry)
    q = calculate_implied_dividend_yield(spot_price, futures_to_use, T, RISK_FREE_RATE)

    # Prepare data
    sorted_strikes = sorted(strikes)
    call_gex = [gex_data.get(s, {}).get('call_gex', 0) for s in sorted_strikes]
    put_gex = [gex_data.get(s, {}).get('put_gex', 0) for s in sorted_strikes]
    net_gex = [gex_data.get(s, {}).get('net_gex', 0) for s in sorted_strikes]
    call_oi = [gex_data.get(s, {}).get('call_oi', 0) for s in sorted_strikes]
    put_oi = [gex_data.get(s, {}).get('put_oi', 0) for s in sorted_strikes]
    ivs = [gex_data.get(s, {}).get('iv', 0.15) * 100 for s in sorted_strikes]  # Convert to %

    x = np.arange(len(sorted_strikes))
    width = 0.35

    # ===== Plot 1: GEX Bar Chart =====
    ax1.clear()
    # Put GEX is negative, so we show absolute value but with different color
    ax1.bar(x - width/2, [abs(p) for p in put_gex], width, label='Put GEX (-)' , color='#4A90D9', alpha=0.8)
    ax1.bar(x + width/2, call_gex, width, label='Call GEX (+)', color='#D94A4A', alpha=0.8)
    ax1.set_xlabel('Strike')
    ax1.set_ylabel('GEX (Cr)')
    ax1.set_title(f'GEX by Strike | Spot: {spot_price:.2f} | Futures: {futures_to_use:.2f}',
                  fontsize=11, fontweight='bold')
    ax1.set_xticks(x[::2])
    ax1.set_xticklabels([str(s) for s in sorted_strikes[::2]], rotation=45, fontsize=8)
    ax1.legend(loc='upper right', fontsize=8)
    if atm_strike in sorted_strikes:
        ax1.axvline(x=sorted_strikes.index(atm_strike), color='yellow', linestyle='--', linewidth=1, alpha=0.7)
    ax1.grid(axis='y', alpha=0.3)

    # ===== Plot 2: Net GEX Horizontal =====
    ax2.clear()
    colors = ['#4A90D9' if g < 0 else '#D94A4A' for g in net_gex]
    y_pos = np.arange(len(sorted_strikes))
    ax2.barh(y_pos, net_gex, color=colors, alpha=0.8)
    ax2.set_yticks(y_pos[::2])
    ax2.set_yticklabels([str(s) for s in sorted_strikes[::2]], fontsize=8)
    ax2.set_xlabel('Net GEX (Cr)')
    ax2.set_title(f'Net GEX | T: {T:.6f} yrs | q: {q*100:.2f}%', fontsize=11, fontweight='bold')
    ax2.axvline(x=0, color='white', linewidth=0.5)
    ax2.grid(axis='x', alpha=0.3)

    # Highlight max positive and negative
    if net_gex:
        max_val = max(net_gex)
        min_val = min(net_gex)
        if max_val != min_val:
            max_idx = net_gex.index(max_val)
            min_idx = net_gex.index(min_val)
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
    if atm_strike in sorted_strikes:
        ax3.axvline(x=sorted_strikes.index(atm_strike), color='yellow', linestyle='--', linewidth=1, alpha=0.7)
    ax3.grid(axis='y', alpha=0.3)
    ax3.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x/1000:.0f}K' if x >= 1000 else f'{x:.0f}'))

    # ===== Plot 4: IV Chart (with skew) =====
    ax4.clear()
    ax4.plot(sorted_strikes, ivs, 'o-', color='#FFD700', linewidth=2, markersize=4, label='IV')
    ax4.axhline(y=atm_iv * 100, color='white', linestyle='--', linewidth=1, alpha=0.5, label=f'ATM IV: {atm_iv*100:.1f}%')
    ax4.set_xlabel('Strike')
    ax4.set_ylabel('IV (%)')
    ax4.set_title(f'Implied Volatility | ATM IV: {atm_iv*100:.1f}%', fontsize=11, fontweight='bold')
    ax4.set_xticks(sorted_strikes[::2])
    ax4.set_xticklabels([str(s) for s in sorted_strikes[::2]], rotation=45, fontsize=8)
    ax4.legend(loc='upper right', fontsize=8)
    if atm_strike in sorted_strikes:
        ax4.axvline(x=atm_strike, color='yellow', linestyle='--', linewidth=1, alpha=0.7)
    ax4.grid(axis='y', alpha=0.3)

    # ===== Plot 5: Summary Totals =====
    ax5.clear()

    total_call_gex = sum(call_gex)
    total_put_gex = sum(put_gex)  # Already negative
    total_net_gex = sum(net_gex)
    total_call_oi = sum(call_oi)
    total_put_oi = sum(put_oi)

    # Display data
    summary_text = (
        f"Call GEX: {total_call_gex:,.2f} Cr  |  "
        f"Put GEX: {total_put_gex:,.2f} Cr  |  "
        f"Net GEX: {total_net_gex:,.2f} Cr\n"
        f"Call OI: {total_call_oi:,.0f} contracts  |  "
        f"Put OI: {total_put_oi:,.0f} contracts  |  "
        f"PCR: {total_put_oi/total_call_oi:.2f}" if total_call_oi > 0 else ""
    )

    ax5.text(0.5, 0.7, summary_text, transform=ax5.transAxes, fontsize=12,
             ha='center', va='center', color='white',
             family='monospace')

    # Net GEX indicator
    net_color = '#00FF00' if total_net_gex > 0 else '#FF6600'
    net_text = f"NET GEX: {total_net_gex:,.2f} Cr"
    ax5.text(0.5, 0.3, net_text, transform=ax5.transAxes, fontsize=16,
             ha='center', va='center', color=net_color, fontweight='bold')

    # Method info
    method_text = "Method: Futures-based | Trading Minutes T | Implied Dividend | IV Skew"
    ax5.text(0.5, 0.05, method_text, transform=ax5.transAxes, fontsize=9,
             ha='center', va='center', color='gray', style='italic')

    ax5.axis('off')

    # Update timestamp
    plt.suptitle(f'NIFTY Web-Style GEX Dashboard | {datetime.now().strftime("%H:%M:%S")} | Expiry: {expiry}',
                 fontsize=14, fontweight='bold', color='cyan')


def polling_thread_func():
    """Background thread to poll data from server"""
    global spot_price, futures_price, option_data

    while True:
        try:
            # Fetch spot price
            spot_data = fetch_spot_from_server()
            if spot_data and spot_data.get('ltp', 0) > 0:
                spot_price = spot_data['ltp']

            # Fetch futures price
            futures = fetch_futures_from_server()
            if futures > 0:
                futures_price = futures

            # Fetch options data
            options_data = fetch_options_from_server()
            if options_data:
                for token, data in options_data.items():
                    if token not in option_data:
                        option_data[token] = {}
                    option_data[token].update(data)

            time.sleep(0.5)
        except Exception as e:
            time.sleep(1)


def run_web_gex_dashboard():
    """Main function to run Web-Style GEX dashboard"""
    global spot_price, futures_price, option_data, current_expiry, option_tokens, strikes

    print("=" * 70)
    print("NIFTY WEB-STYLE GEX DASHBOARD".center(70))
    print("(Using Futures, Trading Minutes, Dividend Yield)".center(70))
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

    # Get futures price
    futures_price = fetch_futures_from_server()
    if futures_price > 0:
        print(f"NIFTY Futures: {futures_price}")
    else:
        futures_price = spot_price * 1.001  # Estimate if not available
        print(f"NIFTY Futures (estimated): {futures_price:.2f}")

    atm_strike = calculate_atm_strike(spot_price)
    print(f"ATM Strike: {atm_strike}")

    # Get expiry from data server
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

    # Calculate and display time info
    T = calculate_time_to_expiry_minutes(current_expiry)
    print(f"Time to Expiry (T): {T:.6f} years ({T * 252 * 375:.0f} trading minutes)")

    # Calculate implied dividend yield
    q = calculate_implied_dividend_yield(spot_price, futures_price, T, RISK_FREE_RATE)
    print(f"Implied Dividend Yield (q): {q*100:.2f}%")

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
    print("Starting Web-Style GEX Dashboard...")
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
    run_web_gex_dashboard()
