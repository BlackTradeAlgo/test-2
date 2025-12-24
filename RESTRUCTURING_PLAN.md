# NIFTY Trading System - Restructuring Plan

## Safety First Approach
- Har step ke baad commit
- Har step ke baad test
- Problem aaye toh rollback

---

## Current Structure
```
/test2/
├── nifty_option_chain.py       # Core: WebSocket + Greeks
├── data_server.py              # Core: HTTP API Server
├── angelone_test.py            # Broker: API Testing
├── volume_delta_engine.py      # Analysis: CVD Engine
├── order_flow_collector.py     # Analysis: Tick Collection
├── order_flow_analyzer.py      # Analysis: Pattern Detection
├── nifty_gex_dashboard.py      # Dashboard: GEX Matplotlib
├── web_gex_dashboard.py        # Dashboard: GEX Web Style
├── order_flow_dashboard.py     # Dashboard: Order Flow Matplotlib
├── order_flow_dashboard_plotly.py  # Dashboard: Order Flow Plotly
├── data/
└── logs/
```

## Target Structure
```
/test2/
├── config/
│   ├── __init__.py
│   └── settings.py             # All constants & credentials reference
├── broker/
│   ├── __init__.py
│   └── angelone.py             # Angel One client (from angelone_test.py)
├── core/
│   ├── __init__.py
│   ├── websocket_handler.py    # WebSocket logic (from nifty_option_chain.py)
│   ├── greeks.py               # Greeks calculations (extracted)
│   └── data_server.py          # HTTP API Server
├── analysis/
│   ├── __init__.py
│   ├── order_flow.py           # Combined order flow logic
│   ├── volume_delta.py         # CVD engine
│   └── gex_calculator.py       # GEX calculations (extracted)
├── dashboards/
│   ├── __init__.py
│   ├── gex_matplotlib.py
│   ├── gex_web.py
│   ├── orderflow_matplotlib.py
│   └── orderflow_plotly.py
├── utils/
│   ├── __init__.py
│   └── helpers.py
├── data/
├── logs/
├── main.py                     # Entry point
├── requirements.txt
├── CLAUDE.md
└── README.md
```

---

## Phase-wise Execution Plan

### PHASE 1: Config Module (LOW RISK)
**Goal:** Extract all constants into one place

**Step 1.1: Create config folder**
```bash
mkdir -p config
touch config/__init__.py
```

**Step 1.2: Create settings.py**
Extract from all files:
- NIFTY_TOKEN
- NIFTY_LOT_SIZE
- STRIKE_INTERVAL
- RISK_FREE_RATE
- SERVER_PORT
- DATA_SERVER_URL
- DATA_BASE_PATH
- TRADING_DAYS_PER_YEAR
- TRADING_MINUTES_PER_DAY

**Step 1.3: Update imports in one file**
Start with `data_server.py`:
```python
from config.settings import NIFTY_TOKEN, SERVER_PORT, ...
```

**TEST:** Run `python data_server.py` - should work same as before

**COMMIT:** `git commit -m "Phase 1.1: Add config module with settings"`

---

### PHASE 2: Utils Module (LOW RISK)
**Goal:** Extract helper functions

**Step 2.1: Create utils folder**
```bash
mkdir -p utils
touch utils/__init__.py
```

**Step 2.2: Create helpers.py**
Extract common functions:
- `format_number()`
- `get_today_folder()`
- `ensure_folder_exists()`

**TEST:** Import test in Python shell

**COMMIT:** `git commit -m "Phase 2: Add utils module"`

---

### PHASE 3: Broker Module (MEDIUM RISK)
**Goal:** Isolate Angel One code

**Step 3.1: Create broker folder**
```bash
mkdir -p broker
touch broker/__init__.py
```

**Step 3.2: Move angelone_test.py**
```bash
mv angelone_test.py broker/angelone.py
```

**Step 3.3: Update imports**
In files that import from angelone_test:
```python
# Old
from angelone_test import login, ...

# New
from broker.angelone import login, ...
```

**TEST:**
1. `python broker/angelone.py` - should run tests
2. `python data_server.py` - should still work

**COMMIT:** `git commit -m "Phase 3: Move broker code to broker module"`

---

### PHASE 4: Core Module - Greeks (MEDIUM RISK)
**Goal:** Extract Greeks calculations

**Step 4.1: Create core folder**
```bash
mkdir -p core
touch core/__init__.py
```

**Step 4.2: Create greeks.py**
Extract from `nifty_option_chain.py`:
- `norm_cdf()`
- `norm_pdf()`
- `bs_call_price()`
- `bs_put_price()`
- `calculate_iv()`
- `calculate_greeks()`

**Step 4.3: Update imports in nifty_option_chain.py**
```python
from core.greeks import calculate_iv, calculate_greeks
```

**TEST:** Run `python nifty_option_chain.py` in market hours

**COMMIT:** `git commit -m "Phase 4: Extract Greeks to core module"`

---

### PHASE 5: Analysis Module (MEDIUM RISK)
**Goal:** Organize order flow code

**Step 5.1: Create analysis folder**
```bash
mkdir -p analysis
touch analysis/__init__.py
```

**Step 5.2: Move files**
```bash
mv volume_delta_engine.py analysis/volume_delta.py
mv order_flow_collector.py analysis/collector.py
mv order_flow_analyzer.py analysis/analyzer.py
```

**Step 5.3: Update all imports**
In dashboards and other files:
```python
# Old
from volume_delta_engine import process_tick, ...
from order_flow_collector import classify_trade_direction, ...
from order_flow_analyzer import analyze_tick, ...

# New
from analysis.volume_delta import process_tick, ...
from analysis.collector import classify_trade_direction, ...
from analysis.analyzer import analyze_tick, ...
```

**TEST:** Run `python order_flow_dashboard.py` in market hours

**COMMIT:** `git commit -m "Phase 5: Move analysis code to analysis module"`

---

### PHASE 6: Dashboards Module (MEDIUM RISK)
**Goal:** Organize dashboard files

**Step 6.1: Create dashboards folder**
```bash
mkdir -p dashboards
touch dashboards/__init__.py
```

**Step 6.2: Move files**
```bash
mv nifty_gex_dashboard.py dashboards/gex_matplotlib.py
mv web_gex_dashboard.py dashboards/gex_web.py
mv order_flow_dashboard.py dashboards/orderflow_matplotlib.py
mv order_flow_dashboard_plotly.py dashboards/orderflow_plotly.py
```

**Step 6.3: Update imports in each file**

**TEST:** Run each dashboard one by one

**COMMIT:** `git commit -m "Phase 6: Move dashboards to dashboards module"`

---

### PHASE 7: Core Server (HIGH RISK - CAREFUL)
**Goal:** Move data_server.py

**Step 7.1: Move file**
```bash
mv data_server.py core/data_server.py
```

**Step 7.2: Update all dashboard imports**
```python
# Check DATA_SERVER_URL is still correct
DATA_SERVER_URL = "http://127.0.0.1:8888"
```

**TEST:**
1. `python core/data_server.py`
2. All dashboards should connect

**COMMIT:** `git commit -m "Phase 7: Move data_server to core module"`

---

### PHASE 8: Main Entry Point (LOW RISK)
**Goal:** Create unified entry point

**Step 8.1: Create main.py**
```python
#!/usr/bin/env python3
"""
NIFTY Trading System - Main Entry Point
"""
import sys

def main():
    if len(sys.argv) < 2:
        print("Usage: python main.py <command>")
        print("Commands:")
        print("  server     - Start data server")
        print("  gex        - Start GEX dashboard")
        print("  orderflow  - Start Order Flow dashboard")
        return

    command = sys.argv[1]

    if command == "server":
        from core.data_server import run_data_server
        run_data_server()
    elif command == "gex":
        from dashboards.gex_web import run_web_gex_dashboard
        run_web_gex_dashboard()
    elif command == "orderflow":
        from dashboards.orderflow_matplotlib import run_dashboard
        run_dashboard()

if __name__ == "__main__":
    main()
```

**TEST:**
- `python main.py server`
- `python main.py gex`

**COMMIT:** `git commit -m "Phase 8: Add main.py entry point"`

---

## Testing Checklist (After Each Phase)

### Basic Tests:
- [ ] `python -c "from config.settings import *"` - No import error
- [ ] `python -c "from broker.angelone import login"` - No import error
- [ ] `python -c "from core.greeks import calculate_iv"` - No import error

### Functional Tests (Market Hours):
- [ ] Data server starts and shows "RUNNING"
- [ ] `/health` endpoint returns `connected: true`
- [ ] `/spot` endpoint returns valid price
- [ ] GEX dashboard shows charts
- [ ] Order flow dashboard shows footprint

### Integration Test:
- [ ] Start data_server in Terminal 1
- [ ] Start any dashboard in Terminal 2
- [ ] Dashboard receives live data
- [ ] No errors in either terminal

---

## Rollback Plan

If anything breaks:
```bash
# See what changed
git diff HEAD~1

# Undo last commit (keep changes)
git reset --soft HEAD~1

# Undo last commit (discard changes)
git reset --hard HEAD~1

# Go back to initial state
git checkout 564a352
```

---

## Timeline Estimate

| Phase | Risk | Time | Test Time |
|-------|------|------|-----------|
| 1. Config | Low | 15 min | 5 min |
| 2. Utils | Low | 10 min | 5 min |
| 3. Broker | Medium | 20 min | 10 min |
| 4. Greeks | Medium | 30 min | 15 min |
| 5. Analysis | Medium | 30 min | 15 min |
| 6. Dashboards | Medium | 30 min | 20 min |
| 7. Server | High | 20 min | 20 min |
| 8. Main | Low | 15 min | 10 min |
| **Total** | | **~3 hours** | **~1.5 hours** |

---

## Important Notes

1. **Do NOT start Phase 7 on trading day** - Server is critical
2. **Test each phase in market hours at least once**
3. **Keep old files until all tests pass**
4. **Weekend is best time for Phase 5-7**
5. **Always `git status` before commit**

---

## Current Progress

- [x] Initial commit pushed to GitHub
- [ ] Phase 1: Config Module
- [ ] Phase 2: Utils Module
- [ ] Phase 3: Broker Module
- [ ] Phase 4: Core Greeks
- [ ] Phase 5: Analysis Module
- [ ] Phase 6: Dashboards Module
- [ ] Phase 7: Core Server
- [ ] Phase 8: Main Entry Point

---

*Plan Created: December 2024*
*Repository: https://github.com/BlackTradeAlgo/test-2*
