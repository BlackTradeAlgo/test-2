#!/usr/bin/env python3
"""
Angel One Broker Connection Test Script
Tests REST API, WebSocket, and Token Download
"""

import pyotp
import requests
import json
import struct
import threading
import time
import websocket
from SmartApi import SmartConnect

# Angel One Credentials
CREDENTIALS = {
    "client_id": "H124854",
    "password": "4794",
    "api_key": "5dZpj3Dg",
    "totp_secret": "L2AAG25BMVUICSO52GIMMHBPOE",
    "secret_key": "91f529ef-99a2-43ad-8099-146b3808e662",
    "historical_api_key": "q6d9BTCF"
}

def generate_totp():
    """Generate TOTP token"""
    totp = pyotp.TOTP(CREDENTIALS["totp_secret"])
    return totp.now()

def connect_angel_one():
    """Connect to Angel One and return SmartConnect object"""
    print("=" * 60)
    print("ANGEL ONE CONNECTION TEST")
    print("=" * 60)

    # Initialize SmartConnect
    obj = SmartConnect(api_key=CREDENTIALS["api_key"])

    # Generate TOTP
    totp_token = generate_totp()
    print(f"\nGenerated TOTP: {totp_token}")

    # Login
    print("\n[1] Attempting Login...")
    try:
        data = obj.generateSession(
            clientCode=CREDENTIALS["client_id"],
            password=CREDENTIALS["password"],
            totp=totp_token
        )

        if data['status']:
            print("    Login SUCCESSFUL!")
            auth_token = data['data']['jwtToken']
            refresh_token = data['data']['refreshToken']
            feed_token = obj.getfeedToken()
            print(f"    JWT Token: {auth_token[:50]}...")
            print(f"    Feed Token: {feed_token}")
            return obj, auth_token, feed_token, refresh_token
        else:
            print(f"    Login FAILED: {data['message']}")
            return None, None, None, None

    except Exception as e:
        print(f"    Login ERROR: {str(e)}")
        return None, None, None, None

def test_rest_api(obj, refresh_token):
    """Test REST API endpoints"""
    print("\n" + "=" * 60)
    print("REST API TESTS")
    print("=" * 60)

    # Test 1: Get Profile
    print("\n[2] Getting User Profile...")
    try:
        profile = obj.getProfile(refresh_token)
        if profile['status']:
            print("    Profile retrieved successfully!")
            print(f"    Name: {profile['data'].get('name', 'N/A')}")
            print(f"    Email: {profile['data'].get('email', 'N/A')}")
            print(f"    Client Code: {profile['data'].get('clientcode', 'N/A')}")
            print(f"    Broker: {profile['data'].get('broker', 'N/A')}")
        else:
            print(f"    Profile FAILED: {profile.get('message', 'Unknown error')}")
    except Exception as e:
        print(f"    Profile ERROR: {str(e)}")

    # Test 2: Get RMS (Risk Management System) / Funds
    print("\n[3] Getting Funds/RMS...")
    try:
        rms = obj.rmsLimit()
        if rms['status']:
            print("    Funds retrieved successfully!")
            print(f"    Net: {rms['data'].get('net', 'N/A')}")
            print(f"    Available Cash: {rms['data'].get('availablecash', 'N/A')}")
            print(f"    Utilised: {rms['data'].get('utiliseddebits', 'N/A')}")
        else:
            print(f"    Funds FAILED: {rms.get('message', 'Unknown error')}")
    except Exception as e:
        print(f"    Funds ERROR: {str(e)}")

    # Test 3: Get Holdings
    print("\n[4] Getting Holdings...")
    try:
        holdings = obj.holding()
        if holdings['status']:
            print("    Holdings retrieved successfully!")
            if holdings['data']:
                print(f"    Total Holdings: {len(holdings['data'])}")
                for h in holdings['data'][:3]:  # Show first 3
                    print(f"      - {h.get('tradingsymbol', 'N/A')}: {h.get('quantity', 0)} qty")
            else:
                print("    No holdings found")
        else:
            print(f"    Holdings FAILED: {holdings.get('message', 'Unknown error')}")
    except Exception as e:
        print(f"    Holdings ERROR: {str(e)}")

    # Test 4: Get Positions
    print("\n[5] Getting Positions...")
    try:
        positions = obj.position()
        if positions['status']:
            print("    Positions retrieved successfully!")
            if positions['data']:
                print(f"    Total Positions: {len(positions['data'])}")
            else:
                print("    No open positions")
        else:
            print(f"    Positions FAILED: {positions.get('message', 'Unknown error')}")
    except Exception as e:
        print(f"    Positions ERROR: {str(e)}")

    # Test 5: Get Order Book
    print("\n[6] Getting Order Book...")
    try:
        orders = obj.orderBook()
        if orders['status']:
            print("    Order Book retrieved successfully!")
            if orders['data']:
                print(f"    Total Orders: {len(orders['data'])}")
            else:
                print("    No orders today")
        else:
            print(f"    Order Book FAILED: {orders.get('message', 'Unknown error')}")
    except Exception as e:
        print(f"    Order Book ERROR: {str(e)}")

    # Test 6: Get LTP (Last Traded Price) for RELIANCE
    print("\n[7] Getting LTP for RELIANCE...")
    try:
        ltp_data = obj.ltpData(
            exchange="NSE",
            tradingsymbol="RELIANCE-EQ",
            symboltoken="2885"
        )
        if ltp_data['status']:
            print("    LTP retrieved successfully!")
            print(f"    Symbol: RELIANCE-EQ")
            print(f"    LTP: {ltp_data['data'].get('ltp', 'N/A')}")
            print(f"    Open: {ltp_data['data'].get('open', 'N/A')}")
            print(f"    High: {ltp_data['data'].get('high', 'N/A')}")
            print(f"    Low: {ltp_data['data'].get('low', 'N/A')}")
            print(f"    Close: {ltp_data['data'].get('close', 'N/A')}")
        else:
            print(f"    LTP FAILED: {ltp_data.get('message', 'Unknown error')}")
    except Exception as e:
        print(f"    LTP ERROR: {str(e)}")

def download_tokens():
    """Download all instrument tokens from Angel One"""
    print("\n" + "=" * 60)
    print("DOWNLOADING ALL TOKENS")
    print("=" * 60)

    token_url = "https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json"

    print("\n[8] Downloading instrument tokens...")
    try:
        response = requests.get(token_url, timeout=60)
        if response.status_code == 200:
            tokens = response.json()
            print(f"    Download SUCCESSFUL!")
            print(f"    Total Instruments: {len(tokens)}")

            # Save to file
            token_file = "/Users/harsh/Desktop/test 1/angelone_tokens.json"
            with open(token_file, 'w') as f:
                json.dump(tokens, f, indent=2)
            print(f"    Saved to: {token_file}")

            # Show sample tokens
            print("\n    Sample Tokens (first 10):")
            print("    " + "-" * 70)
            print(f"    {'Symbol':<20} {'Token':<12} {'Exchange':<10} {'Instrument':<15}")
            print("    " + "-" * 70)

            for token in tokens[:10]:
                print(f"    {token.get('symbol', 'N/A'):<20} {token.get('token', 'N/A'):<12} {token.get('exch_seg', 'N/A'):<10} {token.get('instrumenttype', 'N/A'):<15}")

            # Count by exchange
            exchanges = {}
            for token in tokens:
                exch = token.get('exch_seg', 'Unknown')
                exchanges[exch] = exchanges.get(exch, 0) + 1

            print("\n    Tokens by Exchange:")
            for exch, count in sorted(exchanges.items()):
                print(f"      {exch}: {count}")

            return tokens
        else:
            print(f"    Download FAILED: HTTP {response.status_code}")
            return None
    except Exception as e:
        print(f"    Download ERROR: {str(e)}")
        return None

def parse_ltp_packet(data):
    """Parse LTP mode binary packet from WebSocket"""
    if len(data) < 50:
        return None
    try:
        token = data[2:27].decode('utf-8').strip('\x00')
        ltp = struct.unpack('<q', data[43:51])[0] / 100
        return {'token': token, 'ltp': ltp}
    except:
        return None

def test_websocket(obj, auth_token, feed_token):
    """Test WebSocket connection using direct websocket-client"""
    print("\n" + "=" * 60)
    print("WEBSOCKET TEST")
    print("=" * 60)

    print("\n[9] Testing WebSocket Connection...")

    ws_url = f"wss://smartapisocket.angelone.in/smart-stream?clientCode={CREDENTIALS['client_id']}&feedToken={feed_token}&apiKey={CREDENTIALS['api_key']}"

    messages = []
    ws_connected = False

    def on_message(ws, message):
        parsed = parse_ltp_packet(message)
        if parsed:
            token_names = {'2885': 'RELIANCE', '11536': 'TCS', '1594': 'INFY'}
            name = token_names.get(parsed['token'], parsed['token'])
            print(f"    TICK: {name} = Rs.{parsed['ltp']:.2f}")
            messages.append(parsed)
        if len(messages) >= 5:
            ws.close()

    def on_error(ws, error):
        print(f"    WebSocket ERROR: {error}")

    def on_close(ws, close_status_code, close_msg):
        print("    WebSocket CLOSED")

    def on_open(ws):
        nonlocal ws_connected
        ws_connected = True
        print("    WebSocket CONNECTED!")
        print("    Subscribing to: RELIANCE, TCS, INFY...")
        subscribe_request = {
            'correlationID': 'test123',
            'action': 1,
            'params': {
                'mode': 1,
                'tokenList': [{'exchangeType': 1, 'tokens': ['2885', '11536', '1594']}]
            }
        }
        ws.send(json.dumps(subscribe_request))

    try:
        ws = websocket.WebSocketApp(
            ws_url,
            on_open=on_open,
            on_message=on_message,
            on_error=on_error,
            on_close=on_close
        )

        print("    Starting WebSocket (will auto-close after 5 ticks or 10 seconds)...")

        def run_ws():
            ws.run_forever()

        ws_thread = threading.Thread(target=run_ws)
        ws_thread.daemon = True
        ws_thread.start()

        for _ in range(10):
            time.sleep(1)
            if len(messages) >= 5:
                break

        if messages:
            print(f"    Received {len(messages)} live ticks")
            print("    WebSocket Test: PASSED")
        elif ws_connected:
            print("    Connected but no data (market may be closed)")
            print("    WebSocket Test: PARTIAL")
        else:
            print("    WebSocket Test: Connection not established within timeout")

        try:
            ws.close()
        except:
            pass

    except Exception as e:
        print(f"    WebSocket ERROR: {str(e)}")

def main():
    """Main function"""
    print("\n" + "#" * 60)
    print("#" + " " * 20 + "ANGEL ONE API TESTER" + " " * 18 + "#")
    print("#" * 60)

    # Step 1: Connect and Login
    obj, auth_token, feed_token, refresh_token = connect_angel_one()

    if obj is None:
        print("\nFailed to connect. Exiting...")
        return

    # Step 2: Test REST API
    test_rest_api(obj, refresh_token)

    # Step 3: Download Tokens
    tokens = download_tokens()

    # Step 4: Test WebSocket
    test_websocket(obj, auth_token, feed_token)

    # Logout
    print("\n" + "=" * 60)
    print("CLEANUP")
    print("=" * 60)
    print("\n[10] Logging out...")
    try:
        logout = obj.terminateSession(CREDENTIALS["client_id"])
        print("    Logout successful!")
    except Exception as e:
        print(f"    Logout: {str(e)}")

    print("\n" + "#" * 60)
    print("#" + " " * 18 + "ALL TESTS COMPLETED!" + " " * 20 + "#")
    print("#" * 60 + "\n")

if __name__ == "__main__":
    main()
