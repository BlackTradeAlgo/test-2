#!/usr/bin/env python3
"""
NIFTY Volume Delta Engine
- Calculates Delta (Buy Volume - Sell Volume)
- Tracks Cumulative Volume Delta (CVD)
- Aggregates into 1-minute candles
- Generates footprint data per price level
"""

import os
import csv
from datetime import datetime
from collections import defaultdict

# Data Storage Configuration
DATA_BASE_PATH = "/Users/harsh/Desktop/test 1/data"

# NIFTY lot size
NIFTY_LOT_SIZE = 75

# Global state
cvd = 0  # Cumulative Volume Delta
total_buy_volume = 0
total_sell_volume = 0

# Per-minute candle data
# Key: minute string "HH:MM", Value: candle dict
candle_data = {}
current_minute = ""

# Footprint data: volume at each price level
# Key: price (rounded), Value: {'buy': qty, 'sell': qty}
footprint_data = defaultdict(lambda: {'buy': 0, 'sell': 0})

# File writers
delta_candle_writer = None
footprint_writer = None


def reset_engine():
    """Reset all engine state"""
    global cvd, total_buy_volume, total_sell_volume
    global candle_data, current_minute, footprint_data

    cvd = 0
    total_buy_volume = 0
    total_sell_volume = 0
    candle_data = {}
    current_minute = ""
    footprint_data = defaultdict(lambda: {'buy': 0, 'sell': 0})


def process_tick(direction, quantity, price, timestamp):
    """
    Process a single tick and update all metrics

    Args:
        direction: "BUY" or "SELL"
        quantity: Trade quantity (LTQ)
        price: Trade price (LTP)
        timestamp: Tick timestamp string "HH:MM:SS.mmm"

    Returns:
        dict with current state
    """
    global cvd, total_buy_volume, total_sell_volume
    global candle_data, current_minute, footprint_data

    # Update cumulative volumes
    if direction == "BUY":
        total_buy_volume += quantity
        cvd += quantity
    else:
        total_sell_volume += quantity
        cvd -= quantity

    # Round price to nearest point for footprint
    price_level = round(price)

    # Update footprint
    if direction == "BUY":
        footprint_data[price_level]['buy'] += quantity
    else:
        footprint_data[price_level]['sell'] += quantity

    # Get minute key for candle aggregation
    minute_key = timestamp[:5]  # "HH:MM"

    # Initialize new candle if minute changed
    if minute_key != current_minute:
        # Save previous candle if exists
        if current_minute and current_minute in candle_data:
            save_candle(current_minute)

        # Start new candle
        current_minute = minute_key
        candle_data[minute_key] = {
            'open': price,
            'high': price,
            'low': price,
            'close': price,
            'buy_vol': 0,
            'sell_vol': 0,
            'delta': 0,
            'cvd': cvd,
            'tick_count': 0
        }

    # Update current candle
    candle = candle_data[minute_key]
    candle['high'] = max(candle['high'], price)
    candle['low'] = min(candle['low'], price)
    candle['close'] = price
    candle['tick_count'] += 1

    if direction == "BUY":
        candle['buy_vol'] += quantity
    else:
        candle['sell_vol'] += quantity

    candle['delta'] = candle['buy_vol'] - candle['sell_vol']
    candle['cvd'] = cvd

    return get_current_state()


def get_current_state():
    """Get current engine state"""
    global cvd, total_buy_volume, total_sell_volume, current_minute, candle_data

    current_candle = candle_data.get(current_minute, {})

    return {
        'cvd': cvd,
        'total_buy_volume': total_buy_volume,
        'total_sell_volume': total_sell_volume,
        'net_delta': total_buy_volume - total_sell_volume,
        'current_candle': current_candle,
        'imbalance_ratio': (total_buy_volume / total_sell_volume) if total_sell_volume > 0 else 0
    }


def get_candle(minute_key):
    """Get candle data for specific minute"""
    return candle_data.get(minute_key, None)


def get_all_candles():
    """Get all candles"""
    return candle_data.copy()


def get_footprint_data():
    """Get footprint data (volume at each price level)"""
    return dict(footprint_data)


def get_footprint_for_display(num_levels=20):
    """
    Get footprint data formatted for display

    Returns list of dicts sorted by price descending
    """
    if not footprint_data:
        return []

    result = []
    for price, volumes in sorted(footprint_data.items(), reverse=True):
        delta = volumes['buy'] - volumes['sell']
        total = volumes['buy'] + volumes['sell']
        imbalance = (volumes['buy'] / volumes['sell']) if volumes['sell'] > 0 else float('inf')

        result.append({
            'price': price,
            'buy_vol': volumes['buy'],
            'sell_vol': volumes['sell'],
            'delta': delta,
            'total': total,
            'imbalance': imbalance
        })

    # Return top N levels by total volume
    result.sort(key=lambda x: x['total'], reverse=True)
    return result[:num_levels]


def calculate_imbalance(buy_vol, sell_vol, threshold=2.0):
    """
    Calculate if there's a significant imbalance

    Returns:
        tuple: (has_imbalance, direction, ratio)
    """
    if sell_vol == 0 and buy_vol > 0:
        return (True, "BUY", float('inf'))
    if buy_vol == 0 and sell_vol > 0:
        return (True, "SELL", float('inf'))
    if sell_vol == 0 and buy_vol == 0:
        return (False, None, 0)

    ratio = buy_vol / sell_vol

    if ratio >= threshold:
        return (True, "BUY", ratio)
    elif ratio <= (1 / threshold):
        return (True, "SELL", 1 / ratio)

    return (False, None, ratio)


# ============== FILE SAVING ==============

def init_delta_files(folder=None):
    """Initialize CSV files for delta candles and footprint"""
    global delta_candle_writer, footprint_writer

    if folder is None:
        today = datetime.now().strftime("%Y-%m-%d")
        folder = os.path.join(DATA_BASE_PATH, today)

    os.makedirs(folder, exist_ok=True)

    # Delta candles file
    candle_path = os.path.join(folder, "delta_candles.csv")
    candle_has_data = os.path.exists(candle_path) and os.path.getsize(candle_path) > 0

    candle_handle = open(candle_path, 'a', newline='', buffering=1)
    candle_csv = csv.writer(candle_handle)

    if not candle_has_data:
        candle_csv.writerow([
            'timestamp', 'open', 'high', 'low', 'close',
            'buy_vol', 'sell_vol', 'delta', 'imbalance_ratio', 'cvd', 'tick_count'
        ])
        candle_handle.flush()

    delta_candle_writer = {'writer': candle_csv, 'handle': candle_handle}

    # Footprint file
    footprint_path = os.path.join(folder, "footprint_data.csv")
    footprint_has_data = os.path.exists(footprint_path) and os.path.getsize(footprint_path) > 0

    footprint_handle = open(footprint_path, 'a', newline='', buffering=1)
    footprint_csv = csv.writer(footprint_handle)

    if not footprint_has_data:
        footprint_csv.writerow([
            'timestamp', 'price_level', 'buy_vol', 'sell_vol', 'delta'
        ])
        footprint_handle.flush()

    footprint_writer = {'writer': footprint_csv, 'handle': footprint_handle}

    return candle_path, footprint_path


def save_candle(minute_key):
    """Save completed candle to CSV"""
    global delta_candle_writer, candle_data

    if delta_candle_writer is None:
        return

    candle = candle_data.get(minute_key)
    if not candle:
        return

    buy_vol = candle['buy_vol']
    sell_vol = candle['sell_vol']
    imbalance = (buy_vol / sell_vol) if sell_vol > 0 else 0

    today = datetime.now().strftime("%Y-%m-%d")
    timestamp = f"{today} {minute_key}:00"

    delta_candle_writer['writer'].writerow([
        timestamp,
        f"{candle['open']:.2f}",
        f"{candle['high']:.2f}",
        f"{candle['low']:.2f}",
        f"{candle['close']:.2f}",
        buy_vol,
        sell_vol,
        candle['delta'],
        f"{imbalance:.2f}",
        candle['cvd'],
        candle['tick_count']
    ])
    delta_candle_writer['handle'].flush()


def save_footprint_snapshot(timestamp=None):
    """Save current footprint data to CSV"""
    global footprint_writer, footprint_data

    if footprint_writer is None:
        return

    if timestamp is None:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    for price, volumes in footprint_data.items():
        delta = volumes['buy'] - volumes['sell']
        footprint_writer['writer'].writerow([
            timestamp,
            price,
            volumes['buy'],
            volumes['sell'],
            delta
        ])

    footprint_writer['handle'].flush()


def close_delta_files():
    """Close all delta files"""
    global delta_candle_writer, footprint_writer, current_minute

    # Save last candle if exists
    if current_minute and current_minute in candle_data:
        save_candle(current_minute)

    # Save final footprint snapshot
    save_footprint_snapshot()

    if delta_candle_writer:
        try:
            delta_candle_writer['handle'].close()
        except:
            pass
        delta_candle_writer = None

    if footprint_writer:
        try:
            footprint_writer['handle'].close()
        except:
            pass
        footprint_writer = None


# ============== DISPLAY ==============

def display_state():
    """Display current state in terminal"""
    state = get_current_state()

    print("\n" + "=" * 60)
    print("VOLUME DELTA ENGINE STATE".center(60))
    print("=" * 60)
    print(f"CVD: {state['cvd']:>15}")
    print(f"Total Buy Volume: {state['total_buy_volume']:>15}")
    print(f"Total Sell Volume: {state['total_sell_volume']:>15}")
    print(f"Net Delta: {state['net_delta']:>15}")
    print(f"Imbalance Ratio: {state['imbalance_ratio']:>15.2f}")
    print("=" * 60)

    if state['current_candle']:
        c = state['current_candle']
        print(f"\nCurrent Candle ({current_minute}):")
        print(f"  OHLC: {c['open']:.2f} / {c['high']:.2f} / {c['low']:.2f} / {c['close']:.2f}")
        print(f"  Buy Vol: {c['buy_vol']} | Sell Vol: {c['sell_vol']} | Delta: {c['delta']}")


def display_footprint(num_levels=10):
    """Display footprint data"""
    footprint = get_footprint_for_display(num_levels)

    if not footprint:
        print("No footprint data yet")
        return

    print("\n" + "=" * 60)
    print("FOOTPRINT (Top Volume Levels)".center(60))
    print("=" * 60)
    print(f"{'Price':>10} | {'Buy':>10} | {'Sell':>10} | {'Delta':>10}")
    print("-" * 60)

    for level in footprint:
        delta_str = f"+{level['delta']}" if level['delta'] > 0 else str(level['delta'])
        print(f"{level['price']:>10} | {level['buy_vol']:>10} | {level['sell_vol']:>10} | {delta_str:>10}")


if __name__ == "__main__":
    # Test mode
    print("Volume Delta Engine - Test Mode")
    print("-" * 40)

    # Initialize files
    init_delta_files()

    # Simulate some ticks
    test_ticks = [
        ("BUY", 150, 26100.50, "09:15:01.123"),
        ("BUY", 75, 26101.00, "09:15:02.456"),
        ("SELL", 225, 26099.00, "09:15:03.789"),
        ("BUY", 300, 26102.00, "09:15:10.123"),
        ("SELL", 150, 26100.00, "09:15:15.456"),
        ("BUY", 75, 26105.00, "09:16:01.123"),  # New minute
        ("SELL", 150, 26103.00, "09:16:05.456"),
    ]

    for direction, qty, price, ts in test_ticks:
        state = process_tick(direction, qty, price, ts)
        print(f"Tick: {direction} {qty} @ {price} -> CVD: {state['cvd']}")

    # Display state
    display_state()
    display_footprint()

    # Close files
    close_delta_files()
    print("\nTest complete. Check data folder for CSV files.")
