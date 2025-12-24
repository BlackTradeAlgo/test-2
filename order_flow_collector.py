#!/usr/bin/env python3
"""
NIFTY Order Flow Collector
- Collects NIFTY Futures ticks with Bid/Ask data
- Classifies trade direction (BUY/SELL)
- Saves tick-by-tick order flow data to CSV
"""

import json
import struct
import threading
import time
import os
import csv
from datetime import datetime
import websocket

# Import from existing nifty_option_chain.py
from nifty_option_chain import (
    CREDENTIALS,
    NIFTY_LOT_SIZE,
    login,
    load_all_tokens,
    get_nearest_futures_token,
    parse_snapquote_packet,
    parse_ltp_packet
)

# Data Storage Configuration
DATA_BASE_PATH = "/Users/harsh/Desktop/test 1/data"

# Global state
futures_token = None
futures_symbol = ""
last_direction = "BUY"  # Default for first tick
tick_count = 0

# File writer
order_flow_writer = None


def classify_trade_direction(ltp, best_bids, best_asks, prev_ltp):
    """
    Classify trade as BUY or SELL based on bid/ask

    Logic:
    - LTP >= Best Ask → BUYER initiated (lifted offer)
    - LTP <= Best Bid → SELLER initiated (hit bid)
    - Otherwise → Use tick rule (uptick=BUY, downtick=SELL)
    """
    global last_direction

    # Get best bid and ask (first element = best price)
    best_bid = best_bids[0] if best_bids else 0
    best_ask = best_asks[0] if best_asks else 0

    direction = last_direction  # Default to previous

    if best_ask > 0 and ltp >= best_ask:
        direction = "BUY"
    elif best_bid > 0 and ltp <= best_bid:
        direction = "SELL"
    elif prev_ltp > 0:
        # Tick rule fallback
        if ltp > prev_ltp:
            direction = "BUY"
        elif ltp < prev_ltp:
            direction = "SELL"
        # If equal, keep last direction

    last_direction = direction
    return direction


def create_order_flow_folder():
    """Create folder for order flow data"""
    today = datetime.now().strftime("%Y-%m-%d")
    folder = os.path.join(DATA_BASE_PATH, today)
    os.makedirs(folder, exist_ok=True)
    return folder


def init_order_flow_file(folder):
    """Initialize order flow CSV file"""
    global order_flow_writer

    filepath = os.path.join(folder, "order_flow_ticks.csv")
    file_has_data = os.path.exists(filepath) and os.path.getsize(filepath) > 0

    file_handle = open(filepath, 'a', newline='', buffering=1)
    writer = csv.writer(file_handle)

    if not file_has_data:
        writer.writerow([
            'timestamp', 'symbol', 'ltp', 'ltq', 'direction',
            'best_bid', 'best_ask', 'bid_qty', 'ask_qty',
            'total_buy_qty', 'total_sell_qty', 'volume', 'oi'
        ])
        file_handle.flush()

    order_flow_writer = {'writer': writer, 'handle': file_handle}
    return filepath


def save_order_flow_tick(timestamp, symbol, data, direction):
    """Save order flow tick to CSV"""
    global order_flow_writer

    if order_flow_writer is None:
        return

    # Get best bid/ask (first element)
    best_bid = data.get('best_bids', [0])[0] if data.get('best_bids') else 0
    best_ask = data.get('best_asks', [0])[0] if data.get('best_asks') else 0
    bid_qty = data.get('bid_qty', [0])[0] if data.get('bid_qty') else 0
    ask_qty = data.get('ask_qty', [0])[0] if data.get('ask_qty') else 0

    order_flow_writer['writer'].writerow([
        timestamp,
        symbol,
        f"{data.get('ltp', 0):.2f}",
        data.get('ltq', 0),
        direction,
        f"{best_bid:.2f}",
        f"{best_ask:.2f}",
        bid_qty,
        ask_qty,
        data.get('total_buy_qty', 0),
        data.get('total_sell_qty', 0),
        data.get('volume', 0),
        int(data.get('oi', 0) / NIFTY_LOT_SIZE)
    ])
    order_flow_writer['handle'].flush()


def close_order_flow_file():
    """Close order flow file"""
    global order_flow_writer

    if order_flow_writer:
        try:
            order_flow_writer['handle'].close()
        except:
            pass
        order_flow_writer = None


def display_tick(data, direction, symbol):
    """Display tick in terminal"""
    global tick_count
    tick_count += 1

    ltp = data.get('ltp', 0)
    ltq = data.get('ltq', 0)
    best_bid = data.get('best_bids', [0])[0] if data.get('best_bids') else 0
    best_ask = data.get('best_asks', [0])[0] if data.get('best_asks') else 0
    total_buy = data.get('total_buy_qty', 0)
    total_sell = data.get('total_sell_qty', 0)

    # Color codes
    GREEN = '\033[92m'
    RED = '\033[91m'
    RESET = '\033[0m'

    dir_color = GREEN if direction == "BUY" else RED

    # Clear line and print
    print(f"\r[{tick_count:>6}] {symbol} | LTP: {ltp:>10.2f} | Qty: {ltq:>6} | "
          f"{dir_color}{direction:>4}{RESET} | "
          f"Bid: {best_bid:>10.2f} | Ask: {best_ask:>10.2f} | "
          f"TotBuy: {total_buy:>10} | TotSell: {total_sell:>10}", end="")


def run_order_flow_collector():
    """Main function to run order flow collector"""
    global futures_token, futures_symbol

    print("=" * 70)
    print("NIFTY ORDER FLOW COLLECTOR".center(70))
    print("=" * 70)

    # Login
    obj, auth_token, feed_token = login()
    if not obj:
        print("Login failed!")
        return

    # Load tokens
    print("Loading tokens...")
    all_tokens = load_all_tokens()

    # Get NIFTY Futures token
    futures_token, futures_symbol = get_nearest_futures_token(all_tokens)
    if not futures_token:
        print("Failed to get NIFTY Futures token!")
        return

    print(f"Tracking: {futures_symbol} (Token: {futures_token})")

    # Initialize data storage
    folder = create_order_flow_folder()
    filepath = init_order_flow_file(folder)
    print(f"Saving to: {filepath}")

    # Previous LTP for tick rule
    prev_ltp = [0]

    # WebSocket callbacks
    def on_message(ws, message):
        parsed = parse_snapquote_packet(message)
        if not parsed:
            parsed = parse_ltp_packet(message)

        if parsed and parsed['token'] == futures_token:
            timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]

            # Classify direction
            direction = classify_trade_direction(
                parsed.get('ltp', 0),
                parsed.get('best_bids', []),
                parsed.get('best_asks', []),
                prev_ltp[0]
            )

            # Update prev_ltp
            prev_ltp[0] = parsed.get('ltp', 0)

            # Save tick
            save_order_flow_tick(timestamp, futures_symbol, parsed, direction)

            # Display
            display_tick(parsed, direction, futures_symbol)

    def on_error(ws, error):
        if 'Connection closed' not in str(error):
            print(f"\nWebSocket Error: {error}")

    def on_close(ws, code, msg):
        print("\nWebSocket closed")

    def on_open(ws):
        print("\nWebSocket connected!")
        print("-" * 70)

        # Subscribe to NIFTY Futures with SnapQuote mode
        subscribe = {
            'correlationID': 'order_flow',
            'action': 1,
            'params': {
                'mode': 3,  # SnapQuote for Bid/Ask data
                'tokenList': [
                    {'exchangeType': 2, 'tokens': [futures_token]}  # NFO = 2
                ]
            }
        }
        ws.send(json.dumps(subscribe))
        print(f"Subscribed to {futures_symbol}")
        print("-" * 70)

    # WebSocket URL
    ws_url = f"wss://smartapisocket.angelone.in/smart-stream?clientCode={CREDENTIALS['client_id']}&feedToken={feed_token}&apiKey={CREDENTIALS['api_key']}"

    ws = websocket.WebSocketApp(
        ws_url,
        on_open=on_open,
        on_message=on_message,
        on_error=on_error,
        on_close=on_close
    )

    # Start WebSocket
    ws_thread = threading.Thread(target=ws.run_forever)
    ws_thread.daemon = True
    ws_thread.start()

    # Keep running
    print("\nPress Ctrl+C to stop...\n")
    try:
        while True:
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\n\nStopping...")
        ws.close()
        close_order_flow_file()
        obj.terminateSession(CREDENTIALS["client_id"])
        print(f"Total ticks collected: {tick_count}")
        print("Done.")


if __name__ == "__main__":
    run_order_flow_collector()
