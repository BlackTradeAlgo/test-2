#!/usr/bin/env python3
"""
NIFTY Central Data Server
- Single WebSocket connection to Angel One
- Broadcasts data to local dashboards
- Prevents 429 Too Many Requests error

Run this FIRST, then run any dashboard.
"""

import json
import struct
import threading
import time
from datetime import datetime, timedelta
from collections import defaultdict
import websocket
from flask import Flask, jsonify
from flask_cors import CORS

# Import from nifty_option_chain.py
from nifty_option_chain import (
    CREDENTIALS,
    NIFTY_TOKEN,
    NIFTY_LOT_SIZE,
    login,
    load_all_tokens,
    get_nearest_futures_token,
    get_current_expiry,
    calculate_atm_strike,
    parse_snapquote_packet,
    parse_ltp_packet
)

# Server Configuration
SERVER_PORT = 8888
UPDATE_INTERVAL = 0.1  # 100ms minimum between broadcasts

# Global data storage (shared with all dashboards)
data_store = {
    'spot': {
        'token': NIFTY_TOKEN,
        'ltp': 0,
        'close': 0,
        'open': 0,
        'high': 0,
        'low': 0,
        'last_update': ''
    },
    'futures': {
        'token': '',
        'symbol': '',
        'ltp': 0,
        'close': 0,
        'open': 0,
        'high': 0,
        'low': 0,
        'oi': 0,
        'volume': 0,
        'last_update': ''
    },
    'options': {},  # token -> data dict
    'depth': {
        'best_bids': [],
        'best_asks': [],
        'bid_qty': [],
        'ask_qty': []
    },
    'status': {
        'connected': False,
        'last_tick': '',
        'tick_count': 0,
        'subscribed_tokens': 0
    },
    'expiry': ''  # Current expiry date (from token data)
}

# Token mappings
token_to_info = {}  # token -> {'type': 'CE/PE/FUT/SPOT', 'strike': xxx, 'symbol': 'xxx'}

# Flask app for HTTP API
app = Flask(__name__)
CORS(app)  # Allow cross-origin requests

# ============== FLASK API ENDPOINTS ==============

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'ok',
        'connected': data_store['status']['connected'],
        'tick_count': data_store['status']['tick_count'],
        'last_tick': data_store['status']['last_tick']
    })

@app.route('/spot', methods=['GET'])
def get_spot():
    """Get NIFTY spot data"""
    return jsonify(data_store['spot'])

@app.route('/futures', methods=['GET'])
def get_futures():
    """Get NIFTY futures data"""
    return jsonify(data_store['futures'])

@app.route('/options', methods=['GET'])
def get_options():
    """Get all options data"""
    return jsonify(data_store['options'])

@app.route('/option/<token>', methods=['GET'])
def get_option(token):
    """Get specific option data by token"""
    return jsonify(data_store['options'].get(token, {}))

@app.route('/depth', methods=['GET'])
def get_depth():
    """Get bid/ask depth data"""
    return jsonify(data_store['depth'])

@app.route('/all', methods=['GET'])
def get_all():
    """Get all data at once"""
    return jsonify(data_store)

@app.route('/tick', methods=['GET'])
def get_tick():
    """Get latest tick data for order flow dashboards"""
    # Return futures tick with depth (for order flow analysis)
    futures_data = data_store['futures'].copy()
    futures_data['best_bids'] = data_store['depth'].get('best_bids', [])
    futures_data['best_asks'] = data_store['depth'].get('best_asks', [])
    futures_data['bid_qty'] = data_store['depth'].get('bid_qty', [])
    futures_data['ask_qty'] = data_store['depth'].get('ask_qty', [])
    futures_data['ltq'] = data_store['futures'].get('ltq', 0)
    futures_data['total_buy_qty'] = data_store['futures'].get('total_buy_qty', 0)
    futures_data['total_sell_qty'] = data_store['futures'].get('total_sell_qty', 0)
    return jsonify(futures_data)

@app.route('/status', methods=['GET'])
def get_status():
    """Get server status"""
    return jsonify(data_store['status'])


# ============== ANGEL ONE WEBSOCKET ==============

def parse_best_5_data(data):
    """Parse Best 5 Bid/Ask data from bytes"""
    bids = []
    asks = []
    bid_qty = []
    ask_qty = []

    try:
        for i in range(10):
            offset = i * 20
            if offset + 20 > len(data):
                break

            flag = struct.unpack('<H', data[offset:offset+2])[0]
            qty = struct.unpack('<q', data[offset+2:offset+10])[0]
            price = struct.unpack('<q', data[offset+10:offset+18])[0] / 100

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


def parse_full_snapquote(data):
    """Parse SnapQuote with Best 5 depth data"""
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

        # Parse Best 5 if available
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


def update_data_store(parsed):
    """Update central data store with parsed tick"""
    global data_store

    token = parsed.get('token', '')
    timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]

    data_store['status']['tick_count'] += 1
    data_store['status']['last_tick'] = timestamp

    # Check token type
    if token == NIFTY_TOKEN:
        # Spot data
        data_store['spot']['ltp'] = parsed.get('ltp', 0)
        if parsed.get('close', 0) > 0:
            data_store['spot']['close'] = parsed['close']
        if parsed.get('open', 0) > 0:
            data_store['spot']['open'] = parsed['open']
        if parsed.get('high', 0) > 0:
            data_store['spot']['high'] = parsed['high']
        if parsed.get('low', 0) > 0:
            data_store['spot']['low'] = parsed['low']
        data_store['spot']['last_update'] = timestamp

    elif token == data_store['futures']['token']:
        # Futures data
        data_store['futures']['ltp'] = parsed.get('ltp', 0)
        data_store['futures']['ltq'] = parsed.get('ltq', 0)
        data_store['futures']['total_buy_qty'] = parsed.get('total_buy_qty', 0)
        data_store['futures']['total_sell_qty'] = parsed.get('total_sell_qty', 0)
        if parsed.get('close', 0) > 0:
            data_store['futures']['close'] = parsed['close']
        if parsed.get('open', 0) > 0:
            data_store['futures']['open'] = parsed['open']
        if parsed.get('high', 0) > 0:
            data_store['futures']['high'] = parsed['high']
        if parsed.get('low', 0) > 0:
            data_store['futures']['low'] = parsed['low']
        if parsed.get('oi', 0) > 0:
            data_store['futures']['oi'] = parsed['oi']
        if parsed.get('volume', 0) > 0:
            data_store['futures']['volume'] = parsed['volume']
        data_store['futures']['last_update'] = timestamp

        # Update depth from futures (for order flow)
        if parsed.get('best_bids'):
            data_store['depth']['best_bids'] = parsed['best_bids']
            data_store['depth']['best_asks'] = parsed['best_asks']
            data_store['depth']['bid_qty'] = parsed['bid_qty']
            data_store['depth']['ask_qty'] = parsed['ask_qty']

    else:
        # Option data
        if token not in data_store['options']:
            data_store['options'][token] = {}

        data_store['options'][token].update({
            'ltp': parsed.get('ltp', 0),
            'ltq': parsed.get('ltq', 0),
            'open': parsed.get('open', 0),
            'high': parsed.get('high', 0),
            'low': parsed.get('low', 0),
            'close': parsed.get('close', 0),
            'oi': parsed.get('oi', 0),
            'volume': parsed.get('volume', 0),
            'last_update': timestamp
        })

        # Add token info if available
        if token in token_to_info:
            data_store['options'][token].update(token_to_info[token])


def start_angel_websocket(feed_token, ws_tokens, futures_token):
    """Start WebSocket connection to Angel One"""
    global data_store

    def on_message(ws, message):
        # Try SnapQuote first
        parsed = parse_full_snapquote(message)
        if not parsed:
            parsed = parse_snapquote_packet(message)
        if not parsed:
            parsed = parse_ltp_packet(message)

        if parsed:
            update_data_store(parsed)

    def on_error(ws, error):
        data_store['status']['connected'] = False
        if 'Connection closed' not in str(error):
            print(f"WebSocket Error: {error}")

    def on_close(ws, code, msg):
        data_store['status']['connected'] = False
        print("WebSocket closed")

    def on_open(ws):
        data_store['status']['connected'] = True
        print("WebSocket connected to Angel One!")

        # Separate tokens by exchange
        nfo_tokens = [t for t in ws_tokens if t != NIFTY_TOKEN]

        # Subscribe to NFO tokens (Options + Futures) with SnapQuote mode
        if nfo_tokens:
            subscribe_nfo = {
                'correlationID': 'data_server_nfo',
                'action': 1,
                'params': {
                    'mode': 3,  # SnapQuote for full data
                    'tokenList': [
                        {'exchangeType': 2, 'tokens': nfo_tokens}  # NFO = 2
                    ]
                }
            }
            ws.send(json.dumps(subscribe_nfo))
            print(f"Subscribed to {len(nfo_tokens)} NFO tokens")

        # Subscribe to NIFTY spot with LTP mode
        subscribe_spot = {
            'correlationID': 'data_server_spot',
            'action': 1,
            'params': {
                'mode': 1,  # LTP mode for spot
                'tokenList': [
                    {'exchangeType': 1, 'tokens': [NIFTY_TOKEN]}  # NSE = 1
                ]
            }
        }
        ws.send(json.dumps(subscribe_spot))
        print("Subscribed to NIFTY Spot")

        data_store['status']['subscribed_tokens'] = len(ws_tokens)

    # WebSocket URL
    ws_url = f"wss://smartapisocket.angelone.in/smart-stream?clientCode={CREDENTIALS['client_id']}&feedToken={feed_token}&apiKey={CREDENTIALS['api_key']}"

    ws = websocket.WebSocketApp(
        ws_url,
        on_open=on_open,
        on_message=on_message,
        on_error=on_error,
        on_close=on_close
    )

    # Run forever with reconnect
    while True:
        try:
            ws.run_forever()
        except Exception as e:
            print(f"WebSocket exception: {e}")

        print("Reconnecting in 5 seconds...")
        time.sleep(5)


def load_option_tokens_for_server(all_tokens, expiry, atm_strike, num_strikes=15):
    """Load option tokens for server (wider range)"""
    global token_to_info

    strikes = []
    for i in range(-num_strikes, num_strikes + 1):
        strikes.append(atm_strike + (i * 50))  # NIFTY strike interval = 50

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
                    token_to_info[token['token']] = {
                        'type': 'CE',
                        'strike': strike,
                        'symbol': symbol
                    }
                elif symbol.endswith('PE'):
                    option_tokens['PE'][strike] = {
                        'token': token['token'],
                        'symbol': symbol
                    }
                    token_to_info[token['token']] = {
                        'type': 'PE',
                        'strike': strike,
                        'symbol': symbol
                    }
        except:
            continue

    return option_tokens, strikes


def run_data_server():
    """Main function to run the data server"""
    global data_store

    print("=" * 70)
    print("NIFTY CENTRAL DATA SERVER".center(70))
    print("=" * 70)
    print("This server provides data to all dashboards.")
    print("Run this FIRST, then start any dashboard.")
    print("=" * 70)

    # Login to Angel One
    obj, auth_token, feed_token = login()
    if not obj:
        print("Login failed!")
        return

    # Get NIFTY spot price
    from nifty_option_chain import get_nifty_spot
    spot_price = get_nifty_spot(obj)
    if not spot_price:
        print("Failed to get NIFTY spot price")
        return

    print(f"NIFTY Spot: {spot_price}")
    atm_strike = calculate_atm_strike(spot_price)
    print(f"ATM Strike: {atm_strike}")

    # Store initial spot
    data_store['spot']['ltp'] = spot_price

    # Load all tokens
    print("Loading tokens...")
    all_tokens = load_all_tokens()

    # Get expiry
    expiry = get_current_expiry(all_tokens)
    print(f"Expiry: {expiry}")

    # Save expiry to data_store for dashboards
    data_store['expiry'] = expiry

    if not expiry:
        print("No valid expiry found!")
        return

    # Get futures token
    futures_token, futures_symbol = get_nearest_futures_token(all_tokens)
    print(f"Futures: {futures_symbol} (Token: {futures_token})")

    # Store futures info
    data_store['futures']['token'] = futures_token
    data_store['futures']['symbol'] = futures_symbol

    # Load option tokens (wider range for GEX dashboard)
    option_tokens, strikes = load_option_tokens_for_server(all_tokens, expiry, atm_strike, num_strikes=15)
    print(f"Loaded {len(option_tokens['CE'])} CE + {len(option_tokens['PE'])} PE options")

    # Prepare WebSocket token list
    ws_tokens = [NIFTY_TOKEN]  # Spot
    ws_tokens.append(futures_token)  # Futures

    for strike in strikes:
        if strike in option_tokens['CE']:
            ws_tokens.append(option_tokens['CE'][strike]['token'])
        if strike in option_tokens['PE']:
            ws_tokens.append(option_tokens['PE'][strike]['token'])

    print(f"Total tokens to subscribe: {len(ws_tokens)}")

    # Start Angel One WebSocket in background thread
    print("\nStarting Angel One WebSocket...")
    ws_thread = threading.Thread(
        target=start_angel_websocket,
        args=(feed_token, ws_tokens, futures_token),
        daemon=True
    )
    ws_thread.start()

    # Wait for connection
    time.sleep(3)

    # Start Flask server
    print(f"\n{'=' * 70}")
    print(f"DATA SERVER RUNNING".center(70))
    print(f"{'=' * 70}")
    print(f"HTTP API: http://127.0.0.1:{SERVER_PORT}".center(70))
    print(f"{'=' * 70}")
    print("\nEndpoints:")
    print(f"  /health  - Server health check")
    print(f"  /spot    - NIFTY spot data")
    print(f"  /futures - NIFTY futures data")
    print(f"  /options - All options data")
    print(f"  /depth   - Bid/Ask depth")
    print(f"  /tick    - Latest tick (for order flow)")
    print(f"  /all     - All data combined")
    print(f"  /status  - Server status")
    print(f"\n{'=' * 70}")
    print("Press Ctrl+C to stop server")
    print(f"{'=' * 70}\n")

    try:
        # Run Flask server (blocking)
        app.run(host='127.0.0.1', port=SERVER_PORT, debug=False, threaded=True)
    except KeyboardInterrupt:
        print("\n\nShutting down...")
    finally:
        obj.terminateSession(CREDENTIALS["client_id"])
        print("Logged out from Angel One.")
        print("Server stopped.")


if __name__ == "__main__":
    run_data_server()
