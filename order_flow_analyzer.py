#!/usr/bin/env python3
"""
NIFTY Order Flow Analyzer
- Big Block Detection (>50 lots)
- Absorption Pattern Detection
- Imbalance Alerts
- CVD Divergence Detection
- Stacked Orders Detection
"""

import os
import csv
from datetime import datetime
from collections import deque

# Data Storage Configuration
DATA_BASE_PATH = "/Users/harsh/Desktop/test 1/data"

# NIFTY Configuration
NIFTY_LOT_SIZE = 75

# Detection Thresholds (can be adjusted)
BIG_BLOCK_THRESHOLD = 50 * NIFTY_LOT_SIZE  # 50 lots = 3750 qty
IMBALANCE_THRESHOLD = 2.5  # 2.5x ratio
ABSORPTION_PRICE_RANGE = 5  # Points
ABSORPTION_VOLUME_THRESHOLD = 10000  # Minimum volume
STACKED_ORDERS_THRESHOLD = 3  # Minimum levels with high qty
STACKED_QTY_THRESHOLD = 5000  # Qty per level to consider "stacked"

# Alert history (to avoid duplicates)
recent_alerts = deque(maxlen=100)

# Price and CVD history for divergence detection
price_history = deque(maxlen=20)  # Last 20 data points
cvd_history = deque(maxlen=20)

# File writer
alerts_writer = None


class Alert:
    """Alert data structure"""
    def __init__(self, alert_type, direction, price, details, severity="INFO"):
        self.timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        self.alert_type = alert_type
        self.direction = direction
        self.price = price
        self.details = details
        self.severity = severity  # INFO, WARNING, CRITICAL

    def __str__(self):
        return f"[{self.severity}] {self.alert_type}: {self.details} @ {self.price:.2f}"

    def to_dict(self):
        return {
            'timestamp': self.timestamp,
            'alert_type': self.alert_type,
            'direction': self.direction,
            'price': self.price,
            'details': self.details,
            'severity': self.severity
        }


# ============== DETECTION FUNCTIONS ==============

def detect_big_block(quantity, direction, price):
    """
    Detect large trades (big blocks)

    Args:
        quantity: Trade quantity
        direction: "BUY" or "SELL"
        price: Trade price

    Returns:
        Alert or None
    """
    if quantity >= BIG_BLOCK_THRESHOLD:
        lots = quantity // NIFTY_LOT_SIZE
        severity = "CRITICAL" if lots >= 100 else "WARNING"

        alert = Alert(
            alert_type="BIG_BLOCK",
            direction=direction,
            price=price,
            details=f"{direction} {lots} lots ({quantity} qty)",
            severity=severity
        )

        # Check if similar alert was raised recently
        alert_key = f"BIG_BLOCK_{direction}_{price:.0f}"
        if alert_key not in recent_alerts:
            recent_alerts.append(alert_key)
            return alert

    return None


def detect_absorption(price_levels_data, current_price, lookback_volume):
    """
    Detect absorption pattern
    (Price stable despite heavy volume on one side)

    Args:
        price_levels_data: list of {'price': x, 'buy_vol': y, 'sell_vol': z, ...}
        current_price: Current LTP
        lookback_volume: Recent volume data

    Returns:
        Alert or None
    """
    if not price_levels_data:
        return None

    # Get volume in narrow price range around current price
    range_low = current_price - ABSORPTION_PRICE_RANGE
    range_high = current_price + ABSORPTION_PRICE_RANGE

    buy_vol_in_range = 0
    sell_vol_in_range = 0

    # price_levels_data is a list of dicts from get_footprint_for_display()
    for item in price_levels_data:
        price = item.get('price', 0)
        if range_low <= price <= range_high:
            buy_vol_in_range += item.get('buy_vol', 0)
            sell_vol_in_range += item.get('sell_vol', 0)

    total_vol = buy_vol_in_range + sell_vol_in_range

    if total_vol < ABSORPTION_VOLUME_THRESHOLD:
        return None

    # Check for absorption: heavy volume but price not moving
    if sell_vol_in_range > buy_vol_in_range * 1.5:
        # Heavy selling but price stable = buyers absorbing
        alert = Alert(
            alert_type="ABSORPTION",
            direction="BUY_ABSORBING",
            price=current_price,
            details=f"Buyers absorbing sell pressure. Sell:{sell_vol_in_range} vs Buy:{buy_vol_in_range}",
            severity="WARNING"
        )
        return alert

    elif buy_vol_in_range > sell_vol_in_range * 1.5:
        # Heavy buying but price stable = sellers absorbing
        alert = Alert(
            alert_type="ABSORPTION",
            direction="SELL_ABSORBING",
            price=current_price,
            details=f"Sellers absorbing buy pressure. Buy:{buy_vol_in_range} vs Sell:{sell_vol_in_range}",
            severity="WARNING"
        )
        return alert

    return None


def detect_imbalance(buy_volume, sell_volume, price):
    """
    Detect significant buy/sell imbalance

    Args:
        buy_volume: Total buy volume
        sell_volume: Total sell volume
        price: Current price

    Returns:
        Alert or None
    """
    if buy_volume == 0 and sell_volume == 0:
        return None

    if sell_volume == 0 and buy_volume > 0:
        ratio = float('inf')
        direction = "BUY"
    elif buy_volume == 0 and sell_volume > 0:
        ratio = float('inf')
        direction = "SELL"
    else:
        buy_ratio = buy_volume / sell_volume
        sell_ratio = sell_volume / buy_volume

        if buy_ratio >= IMBALANCE_THRESHOLD:
            ratio = buy_ratio
            direction = "BUY"
        elif sell_ratio >= IMBALANCE_THRESHOLD:
            ratio = sell_ratio
            direction = "SELL"
        else:
            return None

    alert = Alert(
        alert_type="IMBALANCE",
        direction=direction,
        price=price,
        details=f"{direction} imbalance {ratio:.1f}x (Buy:{buy_volume} vs Sell:{sell_volume})",
        severity="INFO"
    )

    return alert


def detect_cvd_divergence(current_price, current_cvd):
    """
    Detect divergence between price and CVD

    Bullish Divergence: Price making lower lows but CVD making higher lows
    Bearish Divergence: Price making higher highs but CVD making lower highs

    Args:
        current_price: Current price
        current_cvd: Current CVD value

    Returns:
        Alert or None
    """
    global price_history, cvd_history

    # Add to history
    price_history.append(current_price)
    cvd_history.append(current_cvd)

    # Need at least 10 points
    if len(price_history) < 10:
        return None

    # Compare first half vs second half
    half = len(price_history) // 2

    price_first_half = list(price_history)[:half]
    price_second_half = list(price_history)[half:]
    cvd_first_half = list(cvd_history)[:half]
    cvd_second_half = list(cvd_history)[half:]

    price_trend = sum(price_second_half) / len(price_second_half) - sum(price_first_half) / len(price_first_half)
    cvd_trend = sum(cvd_second_half) / len(cvd_second_half) - sum(cvd_first_half) / len(cvd_first_half)

    # Bearish divergence: price up but CVD down
    if price_trend > 10 and cvd_trend < -1000:
        alert_key = "DIVERGENCE_BEARISH"
        if alert_key not in recent_alerts:
            recent_alerts.append(alert_key)
            return Alert(
                alert_type="CVD_DIVERGENCE",
                direction="BEARISH",
                price=current_price,
                details=f"Price rising but CVD falling. Potential weakness.",
                severity="WARNING"
            )

    # Bullish divergence: price down but CVD up
    elif price_trend < -10 and cvd_trend > 1000:
        alert_key = "DIVERGENCE_BULLISH"
        if alert_key not in recent_alerts:
            recent_alerts.append(alert_key)
            return Alert(
                alert_type="CVD_DIVERGENCE",
                direction="BULLISH",
                price=current_price,
                details=f"Price falling but CVD rising. Potential strength.",
                severity="WARNING"
            )

    return None


def detect_stacked_orders(bid_prices, bid_quantities, ask_prices, ask_quantities):
    """
    Detect stacked orders (multiple levels with high quantity)

    Args:
        bid_prices: List of best bid prices
        bid_quantities: List of bid quantities
        ask_prices: List of best ask prices
        ask_quantities: List of ask quantities

    Returns:
        Alert or None
    """
    # Check stacked bids
    stacked_bids = sum(1 for qty in bid_quantities if qty >= STACKED_QTY_THRESHOLD)
    if stacked_bids >= STACKED_ORDERS_THRESHOLD:
        total_qty = sum(bid_quantities)
        avg_price = bid_prices[0] if bid_prices else 0

        alert = Alert(
            alert_type="STACKED_ORDERS",
            direction="BID",
            price=avg_price,
            details=f"Stacked bids: {stacked_bids} levels with {total_qty} total qty",
            severity="INFO"
        )
        return alert

    # Check stacked asks
    stacked_asks = sum(1 for qty in ask_quantities if qty >= STACKED_QTY_THRESHOLD)
    if stacked_asks >= STACKED_ORDERS_THRESHOLD:
        total_qty = sum(ask_quantities)
        avg_price = ask_prices[0] if ask_prices else 0

        alert = Alert(
            alert_type="STACKED_ORDERS",
            direction="ASK",
            price=avg_price,
            details=f"Stacked asks: {stacked_asks} levels with {total_qty} total qty",
            severity="INFO"
        )
        return alert

    return None


def detect_rapid_price_move(price_history_local, threshold=20):
    """
    Detect rapid price movement

    Args:
        price_history_local: Recent prices
        threshold: Points movement to trigger alert

    Returns:
        Alert or None
    """
    if len(price_history_local) < 5:
        return None

    recent_prices = list(price_history_local)[-5:]
    price_move = recent_prices[-1] - recent_prices[0]

    if abs(price_move) >= threshold:
        direction = "UP" if price_move > 0 else "DOWN"
        alert = Alert(
            alert_type="RAPID_MOVE",
            direction=direction,
            price=recent_prices[-1],
            details=f"Rapid {direction} move: {price_move:+.2f} points in 5 ticks",
            severity="INFO"
        )
        return alert

    return None


# ============== MAIN ANALYSIS FUNCTION ==============

def analyze_tick(tick_data, delta_state, footprint_data=None):
    """
    Main analysis function - runs all detections

    Args:
        tick_data: dict with ltp, ltq, direction, best_bids, best_asks, etc.
        delta_state: dict from volume_delta_engine
        footprint_data: optional footprint data

    Returns:
        List of Alert objects
    """
    alerts = []

    ltp = tick_data.get('ltp', 0)
    ltq = tick_data.get('ltq', 0)
    direction = tick_data.get('direction', '')

    # 1. Big Block Detection
    big_block = detect_big_block(ltq, direction, ltp)
    if big_block:
        alerts.append(big_block)

    # 2. Imbalance Detection (from delta state)
    buy_vol = delta_state.get('total_buy_volume', 0)
    sell_vol = delta_state.get('total_sell_volume', 0)
    imbalance = detect_imbalance(buy_vol, sell_vol, ltp)
    if imbalance:
        alerts.append(imbalance)

    # 3. CVD Divergence Detection
    cvd = delta_state.get('cvd', 0)
    divergence = detect_cvd_divergence(ltp, cvd)
    if divergence:
        alerts.append(divergence)

    # 4. Stacked Orders Detection
    stacked = detect_stacked_orders(
        tick_data.get('best_bids', []),
        tick_data.get('bid_qty', []),
        tick_data.get('best_asks', []),
        tick_data.get('ask_qty', [])
    )
    if stacked:
        alerts.append(stacked)

    # 5. Absorption Detection (if footprint data available)
    if footprint_data:
        absorption = detect_absorption(footprint_data, ltp, buy_vol + sell_vol)
        if absorption:
            alerts.append(absorption)

    return alerts


# ============== FILE SAVING ==============

def init_alerts_file(folder=None):
    """Initialize alerts CSV file"""
    global alerts_writer

    if folder is None:
        today = datetime.now().strftime("%Y-%m-%d")
        folder = os.path.join(DATA_BASE_PATH, today)

    os.makedirs(folder, exist_ok=True)

    filepath = os.path.join(folder, "alerts.csv")
    file_has_data = os.path.exists(filepath) and os.path.getsize(filepath) > 0

    file_handle = open(filepath, 'a', newline='', buffering=1)
    writer = csv.writer(file_handle)

    if not file_has_data:
        writer.writerow([
            'timestamp', 'alert_type', 'direction', 'price', 'details', 'severity'
        ])
        file_handle.flush()

    alerts_writer = {'writer': writer, 'handle': file_handle}
    return filepath


def save_alert(alert):
    """Save alert to CSV"""
    global alerts_writer

    if alerts_writer is None:
        return

    alerts_writer['writer'].writerow([
        alert.timestamp,
        alert.alert_type,
        alert.direction,
        f"{alert.price:.2f}",
        alert.details,
        alert.severity
    ])
    alerts_writer['handle'].flush()


def close_alerts_file():
    """Close alerts file"""
    global alerts_writer

    if alerts_writer:
        try:
            alerts_writer['handle'].close()
        except:
            pass
        alerts_writer = None


# ============== DISPLAY ==============

def display_alert(alert):
    """Display alert in terminal with colors"""
    # Color codes
    RED = '\033[91m'
    YELLOW = '\033[93m'
    GREEN = '\033[92m'
    CYAN = '\033[96m'
    RESET = '\033[0m'

    if alert.severity == "CRITICAL":
        color = RED
    elif alert.severity == "WARNING":
        color = YELLOW
    else:
        color = CYAN

    print(f"\n{color}{'='*60}")
    print(f"  ALERT: {alert.alert_type}")
    print(f"  {alert.details}")
    print(f"  Price: {alert.price:.2f} | Direction: {alert.direction}")
    print(f"{'='*60}{RESET}\n")


def reset_analyzer():
    """Reset analyzer state"""
    global recent_alerts, price_history, cvd_history
    recent_alerts.clear()
    price_history.clear()
    cvd_history.clear()


if __name__ == "__main__":
    # Test mode
    print("Order Flow Analyzer - Test Mode")
    print("-" * 40)

    # Initialize alerts file
    init_alerts_file()

    # Test big block
    alert = detect_big_block(5000, "BUY", 26100.50)
    if alert:
        print(f"Big Block Alert: {alert}")
        display_alert(alert)
        save_alert(alert)

    # Test imbalance
    alert = detect_imbalance(15000, 5000, 26100.50)
    if alert:
        print(f"Imbalance Alert: {alert}")
        display_alert(alert)
        save_alert(alert)

    # Test stacked orders
    alert = detect_stacked_orders(
        [26100, 26099, 26098, 26097, 26096],
        [6000, 7000, 5500, 6200, 4000],
        [26101, 26102, 26103, 26104, 26105],
        [1000, 1200, 800, 900, 1100]
    )
    if alert:
        print(f"Stacked Alert: {alert}")
        display_alert(alert)
        save_alert(alert)

    # Close file
    close_alerts_file()
    print("\nTest complete. Check data folder for alerts.csv")
