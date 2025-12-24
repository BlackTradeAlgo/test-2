#!/usr/bin/env python3
"""
NIFTY Trading System - Main Entry Point
Unified launcher for all components.
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def show_help():
    """Display available commands"""
    print("""
NIFTY Trading System
====================

Usage: python main.py <command>

Commands:
  server              Start the data server (port 9999)
  option-chain        Start NIFTY Option Chain (terminal display)
  gex                 Start GEX dashboard (Matplotlib)
  gex-web             Start GEX dashboard (Web style)
  orderflow           Start Order Flow dashboard (Matplotlib)
  orderflow-plotly    Start Order Flow dashboard (Plotly/Web)
  test                Run quick system test

Examples:
  python main.py server
  python main.py option-chain
  python main.py gex-web
  python main.py orderflow-plotly
""")


def run_server():
    """Start the data server"""
    print("Starting Data Server...")
    from core.data_server import run_data_server
    run_data_server()


def run_option_chain():
    """Start NIFTY Option Chain (terminal display)"""
    print("Starting NIFTY Option Chain...")
    from nifty_option_chain import run_option_chain as run_oc
    run_oc()


def run_gex_matplotlib():
    """Start GEX Matplotlib dashboard"""
    print("Starting GEX Dashboard (Matplotlib)...")
    from dashboards.gex_matplotlib import run_gex_dashboard
    run_gex_dashboard()


def run_gex_web():
    """Start GEX Web dashboard"""
    print("Starting GEX Dashboard (Web)...")
    from dashboards.gex_web import run_web_gex_dashboard
    run_web_gex_dashboard()


def run_orderflow_matplotlib():
    """Start Order Flow Matplotlib dashboard"""
    print("Starting Order Flow Dashboard (Matplotlib)...")
    from dashboards.orderflow_matplotlib import run_dashboard
    run_dashboard()


def run_orderflow_plotly():
    """Start Order Flow Plotly dashboard"""
    print("Starting Order Flow Dashboard (Plotly)...")
    from dashboards.orderflow_plotly import app, cleanup, initialize_and_run
    import atexit
    atexit.register(cleanup)
    if initialize_and_run():
        print("\nDashboard at: http://127.0.0.1:8051")
        app.run(debug=False, host='127.0.0.1', port=8051)
    else:
        print("Initialization failed!")


def run_test():
    """Quick system test"""
    print("Running System Test...")
    print("=" * 50)

    # Test config
    from config.settings import NIFTY_TOKEN, SERVER_PORT
    print(f"Config: NIFTY_TOKEN={NIFTY_TOKEN}, PORT={SERVER_PORT}")

    # Test utils
    from utils.helpers import get_today_folder, get_timestamp
    print(f"Utils: Today={get_today_folder()}, Time={get_timestamp()}")

    # Test core
    from core.greeks import calculate_delta
    delta = calculate_delta(26000, 26000, 7/365, 0.065, 0.15, 'CE')
    print(f"Core: Delta={delta:.4f}")

    # Test analysis
    from analysis.volume_delta import process_tick, reset_engine
    reset_engine()
    state = process_tick('BUY', 100, 26000, '09:15:00.000')
    print(f"Analysis: CVD={state['cvd']}")

    print("=" * 50)
    print("All tests passed!")


def main():
    """Main entry point"""
    if len(sys.argv) < 2:
        show_help()
        return

    command = sys.argv[1].lower()

    commands = {
        'server': run_server,
        'option-chain': run_option_chain,
        'gex': run_gex_matplotlib,
        'gex-web': run_gex_web,
        'orderflow': run_orderflow_matplotlib,
        'orderflow-plotly': run_orderflow_plotly,
        'test': run_test,
        'help': show_help,
        '-h': show_help,
        '--help': show_help,
    }

    if command in commands:
        commands[command]()
    else:
        print(f"Unknown command: {command}")
        show_help()


if __name__ == "__main__":
    main()
