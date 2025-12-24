#!/usr/bin/env python3
"""
NIFTY Order Flow Dashboard
- Real-time visualization of order flow data
- Footprint Chart, CVD, Delta Bars, Depth, Alerts
"""

import json
import threading
import time
from datetime import datetime
from collections import deque
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
import matplotlib.patches as mpatches
import numpy as np
import requests

# Data Server Configuration
DATA_SERVER_URL = "http://127.0.0.1:8888"

# Import from existing modules (only what's needed now)
from nifty_option_chain import NIFTY_LOT_SIZE

from volume_delta_engine import (
    process_tick,
    get_current_state,
    get_footprint_for_display,
    get_all_candles,
    init_delta_files,
    close_delta_files,
    reset_engine
)

from order_flow_analyzer import (
    analyze_tick,
    init_alerts_file,
    save_alert,
    close_alerts_file,
    display_alert,
    reset_analyzer
)

from order_flow_collector import (
    classify_trade_direction,
    init_order_flow_file,
    save_order_flow_tick,
    close_order_flow_file
)

# Dashboard Configuration
UPDATE_INTERVAL = 500  # milliseconds
MAX_CVD_HISTORY = 100  # Number of CVD points to display
MAX_CANDLES = 30  # Number of candles to display
MAX_ALERTS = 5  # Number of alerts to show

# Global state
futures_symbol = ""
prev_ltp = 0
tick_count = 0

# History for charts
cvd_history = deque(maxlen=MAX_CVD_HISTORY)
time_history = deque(maxlen=MAX_CVD_HISTORY)
price_history = deque(maxlen=MAX_CVD_HISTORY)
alert_history = deque(maxlen=MAX_ALERTS)

# Current bid/ask depth
current_depth = {
    'bids': [],
    'asks': [],
    'bid_qty': [],
    'ask_qty': []
}


def setup_dashboard():
    """Setup matplotlib dashboard with 5 subplots"""
    plt.style.use('dark_background')
    fig = plt.figure(figsize=(16, 10))
    fig.suptitle('NIFTY ORDER FLOW DASHBOARD', fontsize=14, fontweight='bold', color='white')

    # Create grid layout
    # Row 1: Footprint (left), CVD (right)
    # Row 2: Delta Bars (left), Depth (right)
    # Row 3: Alerts (full width)

    ax_footprint = plt.subplot2grid((3, 2), (0, 0))
    ax_cvd = plt.subplot2grid((3, 2), (0, 1))
    ax_delta = plt.subplot2grid((3, 2), (1, 0))
    ax_depth = plt.subplot2grid((3, 2), (1, 1))
    ax_alerts = plt.subplot2grid((3, 2), (2, 0), colspan=2)

    # Style axes
    for ax in [ax_footprint, ax_cvd, ax_delta, ax_depth, ax_alerts]:
        ax.set_facecolor('#1a1a2e')
        ax.tick_params(colors='white', labelsize=8)
        for spine in ax.spines.values():
            spine.set_color('#333355')

    plt.tight_layout(rect=[0, 0, 1, 0.96])

    return fig, ax_footprint, ax_cvd, ax_delta, ax_depth, ax_alerts


def update_footprint_chart(ax):
    """Update footprint chart"""
    ax.clear()
    ax.set_title('FOOTPRINT (Volume by Price)', fontsize=10, color='cyan')
    ax.set_xlabel('Volume', fontsize=8)
    ax.set_ylabel('Price', fontsize=8)

    footprint = get_footprint_for_display(15)

    if not footprint:
        ax.text(0.5, 0.5, 'Waiting for data...', ha='center', va='center',
                transform=ax.transAxes, color='gray', fontsize=12)
        return

    prices = [f['price'] for f in footprint]
    buy_vols = [f['buy_vol'] for f in footprint]
    sell_vols = [-f['sell_vol'] for f in footprint]  # Negative for left side

    y_pos = np.arange(len(prices))

    # Buy bars (right side, green)
    ax.barh(y_pos, buy_vols, color='#00ff88', alpha=0.8, label='Buy')
    # Sell bars (left side, red)
    ax.barh(y_pos, sell_vols, color='#ff4466', alpha=0.8, label='Sell')

    # Price labels
    ax.set_yticks(y_pos)
    ax.set_yticklabels([f'{p:.0f}' for p in prices], fontsize=7)

    # Delta labels on bars
    for i, f in enumerate(footprint):
        delta = f['delta']
        color = '#00ff88' if delta > 0 else '#ff4466'
        x_pos = max(f['buy_vol'], abs(f['sell_vol'])) + 100
        ax.text(x_pos, i, f'{delta:+.0f}', va='center', fontsize=7, color=color)

    ax.axvline(x=0, color='white', linewidth=0.5)
    ax.legend(loc='upper right', fontsize=7)
    ax.set_facecolor('#1a1a2e')


def update_cvd_chart(ax):
    """Update CVD line chart"""
    ax.clear()
    ax.set_title('CVD (Cumulative Volume Delta)', fontsize=10, color='cyan')
    ax.set_xlabel('Time', fontsize=8)
    ax.set_ylabel('CVD', fontsize=8)

    if len(cvd_history) < 2:
        ax.text(0.5, 0.5, 'Waiting for data...', ha='center', va='center',
                transform=ax.transAxes, color='gray', fontsize=12)
        return

    cvd_values = list(cvd_history)
    time_values = list(range(len(cvd_values)))

    # Color based on trend
    if len(cvd_values) >= 2:
        if cvd_values[-1] > cvd_values[-2]:
            color = '#00ff88'
        else:
            color = '#ff4466'
    else:
        color = 'white'

    ax.plot(time_values, cvd_values, color=color, linewidth=2)
    ax.fill_between(time_values, cvd_values, alpha=0.3, color=color)

    # Add current CVD value
    current_cvd = cvd_values[-1] if cvd_values else 0
    ax.axhline(y=0, color='white', linewidth=0.5, linestyle='--', alpha=0.5)

    cvd_text = f'CVD: {current_cvd:+,.0f}'
    ax.text(0.02, 0.95, cvd_text, transform=ax.transAxes, fontsize=10,
            color=color, fontweight='bold', va='top')

    ax.set_facecolor('#1a1a2e')


def update_delta_bars(ax):
    """Update delta bars chart"""
    ax.clear()
    ax.set_title('DELTA BARS (Per Candle)', fontsize=10, color='cyan')
    ax.set_xlabel('Candle', fontsize=8)
    ax.set_ylabel('Delta', fontsize=8)

    candles = get_all_candles()

    if not candles:
        ax.text(0.5, 0.5, 'Waiting for candles...', ha='center', va='center',
                transform=ax.transAxes, color='gray', fontsize=12)
        return

    # Get last N candles
    sorted_candles = sorted(candles.items())[-MAX_CANDLES:]

    times = [c[0] for c in sorted_candles]
    deltas = [c[1]['delta'] for c in sorted_candles]

    colors = ['#00ff88' if d > 0 else '#ff4466' for d in deltas]

    x_pos = np.arange(len(times))
    ax.bar(x_pos, deltas, color=colors, alpha=0.8)

    ax.axhline(y=0, color='white', linewidth=0.5)

    # X-axis labels (show every 5th)
    ax.set_xticks(x_pos[::5])
    ax.set_xticklabels([times[i] for i in range(0, len(times), 5)], rotation=45, fontsize=7)

    # Current delta
    if deltas:
        current_delta = deltas[-1]
        color = '#00ff88' if current_delta > 0 else '#ff4466'
        ax.text(0.98, 0.95, f'Δ: {current_delta:+,.0f}', transform=ax.transAxes,
                fontsize=10, color=color, fontweight='bold', va='top', ha='right')

    ax.set_facecolor('#1a1a2e')


def update_depth_chart(ax):
    """Update bid/ask depth chart"""
    ax.clear()
    ax.set_title('BID/ASK DEPTH', fontsize=10, color='cyan')

    bids = current_depth.get('bids', [])
    asks = current_depth.get('asks', [])
    bid_qty = current_depth.get('bid_qty', [])
    ask_qty = current_depth.get('ask_qty', [])

    if not bids or not asks:
        ax.text(0.5, 0.5, 'Waiting for depth...', ha='center', va='center',
                transform=ax.transAxes, color='gray', fontsize=12)
        return

    # Normalize quantities for display
    max_qty = max(max(bid_qty) if bid_qty else 1, max(ask_qty) if ask_qty else 1)

    # Create depth visualization
    y_positions = np.arange(5)

    # Bid bars (left side)
    bid_widths = [q / max_qty for q in bid_qty[:5]]
    ax.barh(y_positions, [-w for w in bid_widths], color='#00ff88', alpha=0.8, height=0.6)

    # Ask bars (right side)
    ask_widths = [q / max_qty for q in ask_qty[:5]]
    ax.barh(y_positions, ask_widths, color='#ff4466', alpha=0.8, height=0.6)

    # Labels
    for i in range(min(5, len(bids))):
        # Bid labels (left)
        ax.text(-0.05, i, f'{bids[i]:.0f}', ha='right', va='center', fontsize=8, color='#00ff88')
        ax.text(-bid_widths[i] - 0.1, i, f'{bid_qty[i]:,}', ha='right', va='center', fontsize=7, color='white')

    for i in range(min(5, len(asks))):
        # Ask labels (right)
        ax.text(0.05, i, f'{asks[i]:.0f}', ha='left', va='center', fontsize=8, color='#ff4466')
        ax.text(ask_widths[i] + 0.1, i, f'{ask_qty[i]:,}', ha='left', va='center', fontsize=7, color='white')

    ax.axvline(x=0, color='yellow', linewidth=2)
    ax.set_xlim(-1.5, 1.5)
    ax.set_ylim(-0.5, 4.5)
    ax.set_yticks([])
    ax.set_xticks([])

    # Legend
    ax.text(-1.4, 4.8, 'BIDS', fontsize=9, color='#00ff88', fontweight='bold')
    ax.text(1.0, 4.8, 'ASKS', fontsize=9, color='#ff4466', fontweight='bold')

    ax.set_facecolor('#1a1a2e')


def update_alerts_panel(ax):
    """Update alerts panel"""
    ax.clear()
    ax.set_title('ALERTS & SUMMARY', fontsize=10, color='cyan')
    ax.axis('off')

    # Get current state
    state = get_current_state()

    # Summary line
    buy_vol = state.get('total_buy_volume', 0)
    sell_vol = state.get('total_sell_volume', 0)
    cvd = state.get('cvd', 0)
    imbalance = state.get('imbalance_ratio', 0)

    summary = f"CVD: {cvd:+,.0f}  |  Buy Vol: {buy_vol:,}  |  Sell Vol: {sell_vol:,}  |  Imbalance: {imbalance:.2f}x  |  Ticks: {tick_count}"

    cvd_color = '#00ff88' if cvd > 0 else '#ff4466'
    ax.text(0.5, 0.85, summary, ha='center', va='top', transform=ax.transAxes,
            fontsize=10, color='white', fontweight='bold',
            bbox=dict(boxstyle='round', facecolor='#333355', alpha=0.8))

    # Alerts
    if alert_history:
        y_pos = 0.65
        for alert in list(alert_history)[-5:]:
            if alert.severity == "CRITICAL":
                color = '#ff4466'
            elif alert.severity == "WARNING":
                color = '#ffaa00'
            else:
                color = '#00aaff'

            alert_text = f"[{alert.timestamp}] {alert.alert_type}: {alert.details}"
            ax.text(0.02, y_pos, alert_text, ha='left', va='top', transform=ax.transAxes,
                    fontsize=8, color=color)
            y_pos -= 0.12
    else:
        ax.text(0.5, 0.4, 'No alerts yet', ha='center', va='center',
                transform=ax.transAxes, color='gray', fontsize=10)

    ax.set_facecolor('#1a1a2e')


def animate(frame, ax_footprint, ax_cvd, ax_delta, ax_depth, ax_alerts):
    """Animation update function"""
    update_footprint_chart(ax_footprint)
    update_cvd_chart(ax_cvd)
    update_delta_bars(ax_delta)
    update_depth_chart(ax_depth)
    update_alerts_panel(ax_alerts)


def on_tick(parsed_data):
    """Process incoming tick"""
    global prev_ltp, tick_count, current_depth

    tick_count += 1
    timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]

    ltp = parsed_data.get('ltp', 0)
    ltq = parsed_data.get('ltq', 0)

    # Classify direction
    direction = classify_trade_direction(
        ltp,
        parsed_data.get('best_bids', []),
        parsed_data.get('best_asks', []),
        prev_ltp
    )
    prev_ltp = ltp

    # Update depth
    current_depth = {
        'bids': parsed_data.get('best_bids', []),
        'asks': parsed_data.get('best_asks', []),
        'bid_qty': parsed_data.get('bid_qty', []),
        'ask_qty': parsed_data.get('ask_qty', [])
    }

    # Process tick in delta engine
    state = process_tick(direction, ltq, ltp, timestamp)

    # Update history for charts
    cvd_history.append(state['cvd'])
    price_history.append(ltp)
    time_history.append(timestamp)

    # Analyze for alerts
    tick_data = {
        'ltp': ltp,
        'ltq': ltq,
        'direction': direction,
        'best_bids': parsed_data.get('best_bids', []),
        'best_asks': parsed_data.get('best_asks', []),
        'bid_qty': parsed_data.get('bid_qty', []),
        'ask_qty': parsed_data.get('ask_qty', [])
    }

    alerts = analyze_tick(tick_data, state, get_footprint_for_display())

    for alert in alerts:
        alert_history.append(alert)
        save_alert(alert)
        # Only display critical/warning alerts
        if alert.severity in ["CRITICAL", "WARNING"]:
            display_alert(alert)

    # Save tick data
    save_order_flow_tick(timestamp, futures_symbol, parsed_data, direction)


def check_data_server():
    """Check if data server is running"""
    try:
        response = requests.get(f"{DATA_SERVER_URL}/health", timeout=2)
        if response.status_code == 200:
            return True
    except:
        pass
    return False


def fetch_tick_from_server():
    """Fetch latest tick from data server"""
    try:
        response = requests.get(f"{DATA_SERVER_URL}/tick", timeout=1)
        if response.status_code == 200:
            return response.json()
    except:
        pass
    return None


def polling_thread_func():
    """Background thread to poll data from server"""
    global futures_symbol

    last_ltp = 0
    last_ltq = 0

    while True:
        try:
            tick_data = fetch_tick_from_server()
            if tick_data and tick_data.get('ltp', 0) > 0:
                current_ltp = tick_data.get('ltp', 0)
                current_ltq = tick_data.get('ltq', 0)

                # Skip if data is same (stale/market closed)
                if current_ltp == last_ltp and current_ltq == last_ltq:
                    time.sleep(0.1)
                    continue

                # Update last values
                last_ltp = current_ltp
                last_ltq = current_ltq

                # Format data like WebSocket parsed data
                parsed_data = {
                    'token': tick_data.get('token', ''),
                    'ltp': current_ltp,
                    'ltq': current_ltq,
                    'best_bids': tick_data.get('best_bids', []),
                    'best_asks': tick_data.get('best_asks', []),
                    'bid_qty': tick_data.get('bid_qty', []),
                    'ask_qty': tick_data.get('ask_qty', []),
                    'total_buy_qty': tick_data.get('total_buy_qty', 0),
                    'total_sell_qty': tick_data.get('total_sell_qty', 0),
                    'volume': tick_data.get('volume', 0),
                    'oi': tick_data.get('oi', 0)
                }
                futures_symbol = tick_data.get('symbol', 'NIFTY FUT')
                on_tick(parsed_data)

            time.sleep(0.1)  # 100ms polling interval
        except Exception as e:
            time.sleep(0.5)


def run_dashboard():
    """Main function to run the dashboard"""
    global futures_symbol

    print("=" * 70)
    print("NIFTY ORDER FLOW DASHBOARD".center(70))
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

    # Get futures symbol from server
    try:
        response = requests.get(f"{DATA_SERVER_URL}/futures", timeout=2)
        if response.status_code == 200:
            futures_data = response.json()
            futures_symbol = futures_data.get('symbol', 'NIFTY FUT')
            print(f"Tracking: {futures_symbol}")
    except:
        futures_symbol = "NIFTY FUT"

    # Initialize files
    print("Initializing data files...")
    today_folder = datetime.now().strftime("%Y-%m-%d")
    folder = f"/Users/harsh/Desktop/test 1/data/{today_folder}"

    init_order_flow_file(folder)
    init_delta_files(folder)
    init_alerts_file(folder)

    # Reset engines
    reset_engine()
    reset_analyzer()

    print("Setting up dashboard...")

    # Setup matplotlib
    fig, ax_footprint, ax_cvd, ax_delta, ax_depth, ax_alerts = setup_dashboard()

    # Start polling thread
    poll_thread = threading.Thread(target=polling_thread_func, daemon=True)
    poll_thread.start()

    print("Starting dashboard... Close window to exit.")
    print("-" * 70)

    # Start animation
    ani = FuncAnimation(
        fig,
        animate,
        fargs=(ax_footprint, ax_cvd, ax_delta, ax_depth, ax_alerts),
        interval=UPDATE_INTERVAL,
        cache_frame_data=False
    )

    try:
        plt.show()
    except KeyboardInterrupt:
        pass
    finally:
        print("\nShutting down...")
        close_order_flow_file()
        close_delta_files()
        close_alerts_file()
        print(f"Total ticks processed: {tick_count}")
        print("Done.")


if __name__ == "__main__":
    run_dashboard()
