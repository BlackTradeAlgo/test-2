#!/usr/bin/env python3
"""
NIFTY Order Flow Dashboard - Plotly Version
- Interactive charts with hover tooltips
- Real-time updates
- Better visualization
"""

import json
import threading
import time
from datetime import datetime
from collections import deque
import requests

# Plotly imports
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from dash import Dash, html, dcc, callback, Output, Input
import dash_bootstrap_components as dbc

# Data Server Configuration
DATA_SERVER_URL = "http://127.0.0.1:8888"

# Import from existing modules (only what's needed)
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
    reset_analyzer
)

from order_flow_collector import (
    classify_trade_direction,
    init_order_flow_file,
    save_order_flow_tick,
    close_order_flow_file
)

# Dashboard Configuration
UPDATE_INTERVAL = 1000  # milliseconds (1 second)
MAX_CVD_HISTORY = 100
MAX_CANDLES = 30
MAX_ALERTS = 10

# Global state
futures_symbol = ""
prev_ltp = 0
tick_count = 0
current_ltp = 0
ws_connected = False  # Used to show connection status in dashboard

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

# Data server connection status tracked via ws_connected variable


# ============== DASH APP SETUP ==============

app = Dash(
    __name__,
    external_stylesheets=[dbc.themes.DARKLY],
    suppress_callback_exceptions=True
)

app.title = "NIFTY Order Flow Dashboard"

# Layout
app.layout = dbc.Container([
    # Header
    dbc.Row([
        dbc.Col([
            html.H2("NIFTY ORDER FLOW DASHBOARD",
                   className="text-center text-info mb-2",
                   style={'fontWeight': 'bold'}),
        ], width=12)
    ]),

    # Summary Bar
    dbc.Row([
        dbc.Col([
            html.Div(id='summary-bar', className="text-center p-2 mb-3",
                    style={'backgroundColor': '#1a1a2e', 'borderRadius': '10px',
                           'border': '1px solid #333'})
        ], width=12)
    ]),

    # Main Charts Row 1
    dbc.Row([
        # Footprint Chart
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("FOOTPRINT (Volume by Price)",
                              className="text-info",
                              style={'backgroundColor': '#1a1a2e'}),
                dbc.CardBody([
                    dcc.Graph(id='footprint-chart',
                             config={'displayModeBar': True, 'scrollZoom': True},
                             style={'height': '400px'})
                ], style={'backgroundColor': '#0d0d1a', 'padding': '10px'})
            ], style={'backgroundColor': '#1a1a2e', 'border': '1px solid #333'})
        ], width=6),

        # CVD Chart
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("CVD (Cumulative Volume Delta)",
                              className="text-info",
                              style={'backgroundColor': '#1a1a2e'}),
                dbc.CardBody([
                    dcc.Graph(id='cvd-chart',
                             config={'displayModeBar': True, 'scrollZoom': True},
                             style={'height': '400px'})
                ], style={'backgroundColor': '#0d0d1a', 'padding': '10px'})
            ], style={'backgroundColor': '#1a1a2e', 'border': '1px solid #333'})
        ], width=6),
    ], className="mb-3"),

    # Main Charts Row 2
    dbc.Row([
        # Delta Bars
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("DELTA BARS (Per Candle)",
                              className="text-info",
                              style={'backgroundColor': '#1a1a2e'}),
                dbc.CardBody([
                    dcc.Graph(id='delta-chart',
                             config={'displayModeBar': True, 'scrollZoom': True},
                             style={'height': '350px'})
                ], style={'backgroundColor': '#0d0d1a', 'padding': '10px'})
            ], style={'backgroundColor': '#1a1a2e', 'border': '1px solid #333'})
        ], width=6),

        # Depth Chart
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("BID/ASK DEPTH",
                              className="text-info",
                              style={'backgroundColor': '#1a1a2e'}),
                dbc.CardBody([
                    dcc.Graph(id='depth-chart',
                             config={'displayModeBar': True},
                             style={'height': '350px'})
                ], style={'backgroundColor': '#0d0d1a', 'padding': '10px'})
            ], style={'backgroundColor': '#1a1a2e', 'border': '1px solid #333'})
        ], width=6),
    ], className="mb-3"),

    # Alerts Row
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("ALERTS",
                              className="text-warning",
                              style={'backgroundColor': '#1a1a2e'}),
                dbc.CardBody([
                    html.Div(id='alerts-panel', style={'maxHeight': '150px', 'overflowY': 'auto'})
                ], style={'backgroundColor': '#0d0d1a', 'padding': '10px'})
            ], style={'backgroundColor': '#1a1a2e', 'border': '1px solid #333'})
        ], width=12)
    ]),

    # Interval for updates
    dcc.Interval(id='interval-component', interval=UPDATE_INTERVAL, n_intervals=0),

    # Store for data
    dcc.Store(id='data-store')

], fluid=True, style={'backgroundColor': '#0d0d1a', 'minHeight': '100vh', 'padding': '20px'})


# ============== CALLBACKS ==============

@callback(
    [Output('summary-bar', 'children'),
     Output('footprint-chart', 'figure'),
     Output('cvd-chart', 'figure'),
     Output('delta-chart', 'figure'),
     Output('depth-chart', 'figure'),
     Output('alerts-panel', 'children')],
    [Input('interval-component', 'n_intervals')]
)
def update_all_charts(n):
    """Update all charts"""

    # Get current state
    state = get_current_state()

    # Summary bar
    summary = create_summary_bar(state)

    # Charts
    footprint_fig = create_footprint_chart()
    cvd_fig = create_cvd_chart()
    delta_fig = create_delta_chart()
    depth_fig = create_depth_chart()

    # Alerts
    alerts_div = create_alerts_panel()

    return summary, footprint_fig, cvd_fig, delta_fig, depth_fig, alerts_div


def create_summary_bar(state):
    """Create summary bar content"""
    cvd = state.get('cvd', 0)
    buy_vol = state.get('total_buy_volume', 0)
    sell_vol = state.get('total_sell_volume', 0)
    imbalance = state.get('imbalance_ratio', 0)

    cvd_color = '#00ff88' if cvd >= 0 else '#ff4466'

    return html.Div([
        html.Span([
            html.B("LTP: ", style={'color': '#aaa'}),
            html.Span(f"{current_ltp:.2f}", style={'color': '#fff', 'marginRight': '30px'})
        ]),
        html.Span([
            html.B("CVD: ", style={'color': '#aaa'}),
            html.Span(f"{cvd:+,.0f}", style={'color': cvd_color, 'marginRight': '30px', 'fontWeight': 'bold'})
        ]),
        html.Span([
            html.B("Buy Vol: ", style={'color': '#aaa'}),
            html.Span(f"{buy_vol:,}", style={'color': '#00ff88', 'marginRight': '30px'})
        ]),
        html.Span([
            html.B("Sell Vol: ", style={'color': '#aaa'}),
            html.Span(f"{sell_vol:,}", style={'color': '#ff4466', 'marginRight': '30px'})
        ]),
        html.Span([
            html.B("Imbalance: ", style={'color': '#aaa'}),
            html.Span(f"{imbalance:.2f}x", style={'color': '#ffaa00', 'marginRight': '30px'})
        ]),
        html.Span([
            html.B("Ticks: ", style={'color': '#aaa'}),
            html.Span(f"{tick_count:,}", style={'color': '#00aaff'})
        ]),
        html.Span([
            html.B(" | Status: ", style={'color': '#aaa'}),
            html.Span("LIVE" if ws_connected else "DISCONNECTED",
                     style={'color': '#00ff88' if ws_connected else '#ff4466'})
        ]),
    ], style={'fontSize': '14px'})


def create_footprint_chart():
    """Create footprint chart with hover"""
    footprint = get_footprint_for_display(20)

    if not footprint:
        fig = go.Figure()
        fig.add_annotation(text="Waiting for data...", x=0.5, y=0.5,
                          xref="paper", yref="paper", showarrow=False,
                          font=dict(size=16, color='gray'))
    else:
        prices = [f['price'] for f in footprint]
        buy_vols = [f['buy_vol'] for f in footprint]
        sell_vols = [f['sell_vol'] for f in footprint]
        deltas = [f['delta'] for f in footprint]

        fig = go.Figure()

        # Sell bars (negative side)
        fig.add_trace(go.Bar(
            y=prices,
            x=[-v for v in sell_vols],
            orientation='h',
            name='Sell',
            marker_color='#ff4466',
            hovertemplate='<b>Price:</b> %{y}<br>' +
                         '<b>Sell Vol:</b> %{customdata:,}<br>' +
                         '<extra></extra>',
            customdata=sell_vols
        ))

        # Buy bars (positive side)
        fig.add_trace(go.Bar(
            y=prices,
            x=buy_vols,
            orientation='h',
            name='Buy',
            marker_color='#00ff88',
            hovertemplate='<b>Price:</b> %{y}<br>' +
                         '<b>Buy Vol:</b> %{x:,}<br>' +
                         '<extra></extra>'
        ))

        # Add delta annotations
        for i, (price, delta) in enumerate(zip(prices, deltas)):
            color = '#00ff88' if delta > 0 else '#ff4466'
            fig.add_annotation(
                x=max(buy_vols) * 1.1 if max(buy_vols) > 0 else 100,
                y=price,
                text=f"{delta:+,.0f}",
                showarrow=False,
                font=dict(size=10, color=color)
            )

    fig.update_layout(
        template='plotly_dark',
        paper_bgcolor='#0d0d1a',
        plot_bgcolor='#1a1a2e',
        margin=dict(l=80, r=100, t=30, b=50),
        barmode='overlay',
        showlegend=True,
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
        xaxis=dict(
            title='Volume',
            gridcolor='#333',
            zeroline=True,
            zerolinecolor='white',
            zerolinewidth=1,
            tickfont=dict(size=10)
        ),
        yaxis=dict(
            title='Price',
            gridcolor='#333',
            tickformat='.0f',  # Full number like 26180
            tickfont=dict(size=10)
        )
    )

    return fig


def create_cvd_chart():
    """Create CVD line chart with hover"""

    if len(cvd_history) < 2:
        fig = go.Figure()
        fig.add_annotation(text="Waiting for data...", x=0.5, y=0.5,
                          xref="paper", yref="paper", showarrow=False,
                          font=dict(size=16, color='gray'))
    else:
        cvd_values = list(cvd_history)
        time_values = list(time_history)
        price_values = list(price_history)

        # Determine color based on trend
        color = '#00ff88' if cvd_values[-1] >= 0 else '#ff4466'

        fig = go.Figure()

        fig.add_trace(go.Scatter(
            x=list(range(len(cvd_values))),
            y=cvd_values,
            mode='lines',
            name='CVD',
            line=dict(color=color, width=2),
            fill='tozeroy',
            fillcolor=f'rgba({"0,255,136" if cvd_values[-1] >= 0 else "255,68,102"}, 0.2)',
            hovertemplate='<b>Time:</b> %{customdata[0]}<br>' +
                         '<b>CVD:</b> %{y:+,.0f}<br>' +
                         '<b>Price:</b> %{customdata[1]:.2f}<br>' +
                         '<extra></extra>',
            customdata=list(zip(time_values, price_values))
        ))

        # Add zero line
        fig.add_hline(y=0, line_dash="dash", line_color="white", opacity=0.5)

        # Add current CVD annotation
        current_cvd = cvd_values[-1]
        fig.add_annotation(
            x=len(cvd_values) - 1,
            y=current_cvd,
            text=f"CVD: {current_cvd:+,.0f}",
            showarrow=True,
            arrowhead=2,
            arrowcolor=color,
            font=dict(size=12, color=color, family='Arial Black')
        )

    fig.update_layout(
        template='plotly_dark',
        paper_bgcolor='#0d0d1a',
        plot_bgcolor='#1a1a2e',
        margin=dict(l=70, r=30, t=30, b=50),
        showlegend=False,
        xaxis=dict(
            title='',
            gridcolor='#333',
            showticklabels=False
        ),
        yaxis=dict(
            title='CVD',
            gridcolor='#333',
            tickformat=',d',  # Full number with commas
            tickfont=dict(size=10)
        )
    )

    return fig


def create_delta_chart():
    """Create delta bars chart with hover"""
    candles = get_all_candles()

    if not candles:
        fig = go.Figure()
        fig.add_annotation(text="Waiting for candles...", x=0.5, y=0.5,
                          xref="paper", yref="paper", showarrow=False,
                          font=dict(size=16, color='gray'))
    else:
        # Get last N candles
        sorted_candles = sorted(candles.items())[-MAX_CANDLES:]

        times = [c[0] for c in sorted_candles]
        deltas = [c[1]['delta'] for c in sorted_candles]
        buy_vols = [c[1]['buy_vol'] for c in sorted_candles]
        sell_vols = [c[1]['sell_vol'] for c in sorted_candles]
        opens = [c[1]['open'] for c in sorted_candles]
        closes = [c[1]['close'] for c in sorted_candles]

        colors = ['#00ff88' if d >= 0 else '#ff4466' for d in deltas]

        fig = go.Figure()

        fig.add_trace(go.Bar(
            x=times,
            y=deltas,
            marker_color=colors,
            hovertemplate='<b>Time:</b> %{x}<br>' +
                         '<b>Delta:</b> %{y:+,.0f}<br>' +
                         '<b>Buy Vol:</b> %{customdata[0]:,}<br>' +
                         '<b>Sell Vol:</b> %{customdata[1]:,}<br>' +
                         '<b>Open:</b> %{customdata[2]:.2f}<br>' +
                         '<b>Close:</b> %{customdata[3]:.2f}<br>' +
                         '<extra></extra>',
            customdata=list(zip(buy_vols, sell_vols, opens, closes))
        ))

        # Add zero line
        fig.add_hline(y=0, line_color="white", line_width=1)

    fig.update_layout(
        template='plotly_dark',
        paper_bgcolor='#0d0d1a',
        plot_bgcolor='#1a1a2e',
        margin=dict(l=70, r=20, t=30, b=60),
        showlegend=False,
        xaxis=dict(
            title='',
            gridcolor='#333',
            tickangle=-45,
            tickfont=dict(size=9)
        ),
        yaxis=dict(
            title='Delta',
            gridcolor='#333',
            tickformat=',d',  # Full number with commas
            tickfont=dict(size=10)
        )
    )

    return fig


def create_depth_chart():
    """Create bid/ask depth chart - simple ladder style"""
    bids = current_depth.get('bids', [])[:5]
    asks = current_depth.get('asks', [])[:5]
    bid_qty = current_depth.get('bid_qty', [])[:5]
    ask_qty = current_depth.get('ask_qty', [])[:5]

    fig = go.Figure()

    if not bids or not asks or len(bids) == 0 or len(asks) == 0:
        fig.add_annotation(text="Waiting for depth...", x=0.5, y=0.5,
                          xref="paper", yref="paper", showarrow=False,
                          font=dict(size=16, color='gray'))
        fig.update_layout(
            template='plotly_dark',
            paper_bgcolor='#0d0d1a',
            plot_bgcolor='#1a1a2e',
            margin=dict(l=30, r=30, t=50, b=30)
        )
        return fig

    try:
        # Best bid/ask
        best_bid = bids[0] if bids else 0
        best_ask = asks[0] if asks else 0
        spread = best_ask - best_bid

        # Create simple table-like display with bars
        # Row format: BID_QTY | BID_PRICE | ASK_PRICE | ASK_QTY

        # Prepare data - show 5 levels each
        levels = min(5, len(bids), len(asks))

        y_labels = []
        bid_values = []
        ask_values = []

        for i in range(levels):
            bid_price = bids[i] if i < len(bids) else 0
            ask_price = asks[i] if i < len(asks) else 0
            b_qty = bid_qty[i] if i < len(bid_qty) else 0
            a_qty = ask_qty[i] if i < len(ask_qty) else 0

            y_labels.append(f"L{i+1}")
            bid_values.append(b_qty)
            ask_values.append(a_qty)

        # Bids (green bars going left)
        fig.add_trace(go.Bar(
            y=y_labels,
            x=[-v for v in bid_values],
            orientation='h',
            marker_color='#00ff88',
            name='Bids',
            text=[f"{bids[i]:.0f} ({bid_values[i]:,})" for i in range(levels)],
            textposition='inside',
            textfont=dict(color='black', size=10),
            hovertemplate='<b>BID Level %{y}</b><br>Qty: %{customdata:,}<extra></extra>',
            customdata=bid_values
        ))

        # Asks (red bars going right)
        fig.add_trace(go.Bar(
            y=y_labels,
            x=ask_values,
            orientation='h',
            marker_color='#ff4466',
            name='Asks',
            text=[f"{asks[i]:.0f} ({ask_values[i]:,})" for i in range(levels)],
            textposition='inside',
            textfont=dict(color='white', size=10),
            hovertemplate='<b>ASK Level %{y}</b><br>Qty: %{x:,}<extra></extra>'
        ))

        fig.update_layout(
            template='plotly_dark',
            paper_bgcolor='#0d0d1a',
            plot_bgcolor='#1a1a2e',
            margin=dict(l=20, r=20, t=50, b=30),
            showlegend=True,
            legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='center', x=0.5),
            barmode='overlay',
            xaxis=dict(
                title='',
                gridcolor='#333',
                zeroline=True,
                zerolinecolor='yellow',
                zerolinewidth=2,
                tickfont=dict(size=9)
            ),
            yaxis=dict(
                title='',
                gridcolor='#333',
                tickfont=dict(size=10)
            ),
            title=dict(
                text=f"Best Bid: {best_bid:.0f} | Spread: {spread:.0f} | Best Ask: {best_ask:.0f}",
                font=dict(size=11, color='#00aaff'),
                x=0.5
            )
        )

    except Exception as e:
        fig.add_annotation(text=f"Error: {str(e)}", x=0.5, y=0.5,
                          xref="paper", yref="paper", showarrow=False,
                          font=dict(size=12, color='red'))
        fig.update_layout(
            template='plotly_dark',
            paper_bgcolor='#0d0d1a',
            plot_bgcolor='#1a1a2e'
        )

    return fig


def create_alerts_panel():
    """Create alerts panel"""
    if not alert_history:
        return html.Div("No alerts yet...", style={'color': 'gray', 'textAlign': 'center'})

    alerts_list = []
    for alert in reversed(list(alert_history)):
        if alert.severity == "CRITICAL":
            color = '#ff4466'
            icon = "🚨"
        elif alert.severity == "WARNING":
            color = '#ffaa00'
            icon = "⚠️"
        else:
            color = '#00aaff'
            icon = "ℹ️"

        alerts_list.append(
            html.Div([
                html.Span(f"{icon} [{alert.timestamp}] ", style={'color': '#888'}),
                html.Span(f"{alert.alert_type}: ", style={'color': color, 'fontWeight': 'bold'}),
                html.Span(f"{alert.details} ", style={'color': '#fff'}),
                html.Span(f"@ {alert.price:.2f}", style={'color': '#aaa'})
            ], style={'marginBottom': '5px', 'fontSize': '12px'})
        )

    return html.Div(alerts_list)


# ============== DATA POLLING ==============

def on_tick(parsed_data):
    """Process incoming tick"""
    global prev_ltp, tick_count, current_depth, current_ltp

    tick_count += 1
    timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]

    ltp = parsed_data.get('ltp', 0)
    ltq = parsed_data.get('ltq', 0)
    current_ltp = ltp

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
    global futures_symbol, ws_connected

    last_ltp = 0
    last_ltq = 0

    while True:
        try:
            tick_data = fetch_tick_from_server()
            if tick_data and tick_data.get('ltp', 0) > 0:
                ws_connected = True
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
            else:
                ws_connected = False

            time.sleep(0.1)  # 100ms polling interval
        except Exception as e:
            ws_connected = False
            time.sleep(0.5)


def initialize_and_run():
    """Initialize everything and run dashboard"""
    global futures_symbol

    print("=" * 70)
    print("NIFTY ORDER FLOW DASHBOARD - PLOTLY VERSION".center(70))
    print("(Using Central Data Server)".center(70))
    print("=" * 70)

    # Check data server
    print("Checking data server...")
    if not check_data_server():
        print("\nERROR: Data server not running!")
        print("Please start data_server.py first:")
        print("  python3 data_server.py")
        print("\nThen run this dashboard again.")
        return False

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

    # Start polling thread
    print("Starting data polling...")
    poll_thread = threading.Thread(target=polling_thread_func, daemon=True)
    poll_thread.start()

    # Wait for first data
    time.sleep(1)

    return True


def cleanup():
    """Cleanup on exit"""
    print("\nShutting down...")

    close_order_flow_file()
    close_delta_files()
    close_alerts_file()

    print(f"Total ticks processed: {tick_count}")
    print("Done.")


# ============== MAIN ==============

if __name__ == "__main__":
    import atexit

    # Register cleanup
    atexit.register(cleanup)

    # Initialize
    if initialize_and_run():
        print("\n" + "=" * 70)
        print("Dashboard starting at: http://127.0.0.1:8050".center(70))
        print("Press Ctrl+C to stop".center(70))
        print("=" * 70 + "\n")

        # Run Dash app
        app.run(debug=False, host='127.0.0.1', port=8050)
    else:
        print("Initialization failed!")
