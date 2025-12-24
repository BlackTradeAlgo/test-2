# NIFTY Futuristic Trading Terminal - Lovable Guide

Complete step-by-step guide to create a professional futuristic trading dashboard using Lovable.dev

---

## Table of Contents

1. [Dashboard Preview](#dashboard-preview)
2. [Lovable Setup](#step-1-lovable-setup)
3. [Prompt 1: Base Layout + Header](#step-2-prompt-1---base-layout--futuristic-header)
4. [Prompt 2: Option Chain Panel](#step-3-prompt-2---option-chain-panel)
5. [Prompt 3: GEX Panel](#step-4-prompt-3---gex-visualization-panel)
6. [Prompt 4: Order Flow Panel](#step-5-prompt-4---order-flow-panel)
7. [Prompt 5: CVD & Alerts Panel](#step-6-prompt-5---cvd-analytics--alerts-panel)
8. [Polish Prompts](#step-7-polish-prompts---futuristic-effects)
9. [Setup & Running](#step-8-complete-setup--running)
10. [Checklist & Tips](#complete-checklist)

---

## Dashboard Preview

```
╔══════════════════════════════════════════════════════════════════════════════════╗
║  ◉ NIFTY COMMAND CENTER                           ⚡ LIVE    🔔    ⚙️    14:32:45 ║
╠══════════════════════════════════════════════════════════════════════════════════╣
║  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ║
║  │   SPOT      │ │  FUTURES    │ │    ATM      │ │    CVD      │ │   NET GEX   │ ║
║  │  23,856.45  │ │  23,872.30  │ │   23,850    │ │  +12,450    │ │  +6.5 Cr    │ ║
║  │   ▲ +0.45%  │ │   ▲ +0.52%  │ │             │ │     ▲       │ │   BULLISH   │ ║
║  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘ ║
╠══════════════════════════════════════════════════════════════════════════════════╣
║                                                                                   ║
║  ┌─────────────────────────────────────────┐  ┌────────────────────────────────┐ ║
║  │          OPTION CHAIN                    │  │         GEX EXPOSURE           │ ║
║  │  ════════════════════════════════════   │  │  ═══════════════════════════   │ ║
║  │  CE OI  │ CE LTP │STRIKE│ PE LTP│ PE OI │  │  PUT GEX ◄──────►  CALL GEX   │ ║
║  │  ──────────────────────────────────────  │  │  ████████       ████████████  │ ║
║  │  45.2K  │ 245.30 │23700 │ 45.60 │ 32.1K │  │  ██████████     ██████████    │ ║
║  │  52.8K  │ 198.45 │23750 │ 68.90 │ 48.3K │  │  ████████████   ████████      │ ║
║  │  68.4K  │ 156.20 │23800 │ 98.35 │ 62.7K │  │  ██████████████ ██████        │ ║
║  │ ●89.2K● │●118.60●│█23850█│●134.80│●78.4K●│  │  ████████████   ████████████  │ ║
║  │  72.1K  │  84.30 │23900 │ 178.50│ 58.9K │  │  ██████████     ██████████████│ ║
║  │  58.6K  │  56.75 │23950 │ 225.60│ 42.5K │  │  ████████       ████████████  │ ║
║  │  41.3K  │  34.20 │24000 │ 285.40│ 35.8K │  │                                │ ║
║  └─────────────────────────────────────────┘  └────────────────────────────────┘ ║
║                                                                                   ║
║  ┌──────────────────────────────────┐  ┌─────────────────────────────────────────┐║
║  │      ORDER FLOW - FOOTPRINT      │  │              CVD + DELTA                │║
║  │  ════════════════════════════    │  │  ═══════════════════════════════════   │║
║  │  SELL     │ PRICE │     BUY      │  │         ╱╲    CVD CHART                │║
║  │  ████████ │23875  │ ████         │  │        ╱  ╲  ╱╲                        │║
║  │  ██████   │23870  │ ████████████ │  │   ╱╲  ╱    ╲╱  ╲    ╱╲                 │║
║  │  ████     │23865█ │ ██████████   │  │  ╱  ╲╱          ╲  ╱  ╲                │║
║  │  ██████████│23860 │ ██████       │  │ ╱                ╲╱                    │║
║  │  ████████ │23855  │ ████████     │  ├─────────────────────────────────────────┤║
║  │                                   │  │  ▌▐▌▐ ▌▐▌  DELTA BARS  ▌ ▐▌▐▌▐        │║
║  │  BID DEPTH    │    ASK DEPTH     │  │  █ ██ █  █               █  ███        │║
║  │  ████████████ │ ████████████     │  │  █ ██ █  █     ▄▄▄       █  ███  ▄▄    │║
║  │  23869: 4,500 │ 23871: 3,800     │  │ ▄█▄██▄█▄▄█▄▄▄▄████▄▄▄▄▄▄▄█▄▄███▄████▄  │║
║  └──────────────────────────────────┘  └─────────────────────────────────────────┘║
║                                                                                   ║
║  ┌────────────────────────────────────────────────────────────────────────────────┐║
║  │  🔴 14:32:40 BIG BLOCK: BUY 4,500 @ 23871  │  KEY LEVELS: Max Pain 23800 │     │║
║  │  🟠 14:31:15 IMBALANCE: Buy/Sell 3.2x     │  Highest CE OI: 24000        │     │║
║  │  🔵 14:30:02 HIGH VOLUME: 25K in 1-min    │  Highest PE OI: 23500        │     │║
║  └────────────────────────────────────────────────────────────────────────────────┘║
╚══════════════════════════════════════════════════════════════════════════════════╝
```

---

## Step 1: Lovable Setup

```
1. Browser mein jao: https://lovable.dev
2. "Get Started" ya "Sign Up" click karo
3. Google ya GitHub se login karo (easy hai)
4. Free tier mein ~100 credits milte hain
5. "Create new project" click karo
6. Name: "NIFTY Futuristic Terminal"
7. Blank template select karo
```

---

## Step 2: Prompt 1 - Base Layout + Futuristic Header

Lovable mein yeh prompt paste karo:

```
Create an ultra-futuristic NIFTY Trading Command Center with React, TypeScript, and Tailwind CSS.

## DESIGN VISION:
Think Sci-Fi movie trading terminal meets Bloomberg Terminal. Inspired by:
- Cyberpunk 2077 UI
- Iron Man's JARVIS interface
- Blade Runner control panels

## COLOR PALETTE:
- Background: Deep space black with subtle grid (#0a0a0f)
- Primary accent: Electric cyan (#00fff5)
- Secondary accent: Neon magenta (#ff00ff)
- Bullish/Buy: Matrix green (#00ff88)
- Bearish/Sell: Danger red (#ff3366)
- Warning: Electric orange (#ff9500)
- Text primary: Pure white (#ffffff)
- Text secondary: Steel gray (#8892a0)
- Borders: Glowing cyan with transparency (#00fff520)
- Card backgrounds: Dark glass effect (#12121a with backdrop-blur)

## TYPOGRAPHY:
- Headers: "Orbitron" or "Rajdhani" (futuristic font)
- Numbers: "JetBrains Mono" or "Fira Code" (monospace)
- Import from Google Fonts

## GLOBAL EFFECTS:
- Subtle scan line overlay (CSS animation)
- Glowing borders on hover
- Pulse animations on live data
- Glassmorphism cards (backdrop-blur + transparency)
- Gradient text for important values
- Corner brackets on cards (sci-fi style)

## LAYOUT STRUCTURE:

### Top Bar (60px, fixed):
- Left: Glowing logo with pulse effect
- Center: "NIFTY COMMAND CENTER" in Orbitron font with gradient
- Right: Live indicator (blinking dot), notification bell, settings, digital clock

### Stats Bar (80px):
5 stat cards in a row with glass effect:
- SPOT price with change %
- FUTURES price with change %
- ATM Strike
- CVD value with arrow
- NET GEX with bullish/bearish label

Each card features:
- Subtle glow effect matching the value (green for positive, red for negative)
- Number counting animation on change
- Corner brackets decoration
- Label in small caps above the value

### Main Grid (remaining height):
- 2 rows, 2 columns
- Gap: 16px
- Each panel has glowing border and glass background

## CARD COMPONENT DESIGN:
```jsx
<div className="relative bg-[#12121a]/80 backdrop-blur-xl border border-cyan-500/20 rounded-lg overflow-hidden">
  {/* Corner decorations */}
  <div className="absolute top-0 left-0 w-4 h-4 border-l-2 border-t-2 border-cyan-400" />
  <div className="absolute top-0 right-0 w-4 h-4 border-r-2 border-t-2 border-cyan-400" />
  <div className="absolute bottom-0 left-0 w-4 h-4 border-l-2 border-b-2 border-cyan-400" />
  <div className="absolute bottom-0 right-0 w-4 h-4 border-r-2 border-b-2 border-cyan-400" />

  {/* Header */}
  <div className="px-4 py-2 border-b border-cyan-500/20 bg-gradient-to-r from-cyan-500/10 to-transparent">
    <h2 className="text-cyan-400 font-orbitron text-sm tracking-wider">PANEL TITLE</h2>
  </div>

  {/* Content */}
  <div className="p-4">
    {/* Panel content */}
  </div>
</div>
```

## API INTEGRATION:
Base URL: http://127.0.0.1:8888

Fetch every 500ms:
- GET /all → Complete data
- GET /tick → Order flow tick

## PLACEHOLDER PANELS:
For now, create 4 placeholder panels:
1. Top-Left: "OPTION CHAIN"
2. Top-Right: "GEX EXPOSURE"
3. Bottom-Left: "ORDER FLOW"
4. Bottom-Right: "CVD & ANALYTICS"

Each placeholder should show "Loading data..." with a spinning cyan loader.

## CSS ANIMATIONS:
```css
/* Scan line effect */
@keyframes scanline {
  0% { transform: translateY(-100%); }
  100% { transform: translateY(100vh); }
}

/* Glow pulse */
@keyframes glowPulse {
  0%, 100% { box-shadow: 0 0 5px #00fff5, 0 0 10px #00fff5; }
  50% { box-shadow: 0 0 20px #00fff5, 0 0 30px #00fff5; }
}

/* Number flash on change */
@keyframes flash {
  0% { background: rgba(0, 255, 136, 0.3); }
  100% { background: transparent; }
}
```

## RESPONSIVE:
- Desktop first (1920x1080 optimal)
- Tablet: Stack panels vertically
- Hide scan line effect on mobile

Create this foundation first. We will add each panel's content in subsequent prompts.
```

---

## Step 3: Prompt 2 - Option Chain Panel

Jab base layout ban jaye, yeh prompt do:

```
Now implement the OPTION CHAIN panel (top-left) with futuristic design.

## OPTION CHAIN LAYOUT:

```
┌─────────────────────────────────────────────────────────────────┐
│ ◈ OPTION CHAIN                              Expiry: 26DEC2024  │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ═══════════════ CALLS ═══════════════ │ ═══════ PUTS ═══════  │
│                                         │                       │
│   OI     │  LTP  │  IV  │ STRIKE │  IV  │  LTP  │   OI         │
│  ─────────────────────────────────────────────────────────────  │
│   45.2K  │ 245.3 │ 14.2 │ 23700  │ 15.1 │  45.6 │  32.1K       │
│   52.8K  │ 198.4 │ 13.8 │ 23750  │ 14.5 │  68.9 │  48.3K       │
│   68.4K  │ 156.2 │ 13.2 │ 23800  │ 13.9 │  98.3 │  62.7K       │
│  ●89.2K● │●118.6●│●12.8●│█23850█ │●13.2●│●134.8●│ ●78.4K●      │ ← ATM ROW
│   72.1K  │  84.3 │ 13.5 │ 23900  │ 14.1 │ 178.5 │  58.9K       │
│   58.6K  │  56.7 │ 14.0 │ 23950  │ 14.8 │ 225.6 │  42.5K       │
│   41.3K  │  34.2 │ 14.6 │ 24000  │ 15.5 │ 285.4 │  35.8K       │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│  Total CE OI: 428.2K  │  PCR: 0.85  │  Total PE OI: 358.7K     │
└─────────────────────────────────────────────────────────────────┘
```

## VISUAL FEATURES:

### Column Headers:
- Gradient underline (cyan to transparent)
- "CALLS" label on left with red tint
- "PUTS" label on right with blue tint

### Strike Column (Center):
- Larger font size
- ATM strike highlighted with:
  - Glowing yellow/gold border
  - Pulsing background animation
  - "ATM" badge next to it

### OI Columns:
- Show OI in thousands (K format)
- Background bar showing relative OI:
  - CE OI: Red gradient bar (width = % of max OI)
  - PE OI: Blue gradient bar
- Highest OI strike has extra glow effect

### LTP Columns:
- Flash green on price up, red on price down
- Monospace font for alignment

### IV Columns:
- Color gradient based on IV level:
  - Low IV (< 12%): Blue
  - Normal IV (12-15%): White
  - High IV (> 15%): Orange/Red
- Small trend arrow (▲/▼) if IV changed

### ITM/OTM Coloring:
- ITM strikes: Slightly brighter background
- OTM strikes: Normal background
- For Calls: ITM = strike < spot
- For Puts: ITM = strike > spot

### Row Hover Effect:
- Entire row gets cyan glow on hover
- Show tooltip with detailed Greeks (Delta, Gamma, Theta, Vega)

### Summary Bar (Bottom):
- Glass effect background
- Three sections:
  - Total CE OI with red accent
  - PCR (Put-Call Ratio) - large, centered
  - Total PE OI with blue accent

## DATA STRUCTURE:
From GET /options endpoint:
```javascript
{
  "token123": {
    "strike": 23850,
    "type": "CE",
    "ltp": 118.6,
    "oi": 892000,  // Raw OI, divide by 75 for contracts
    "volume": 45000,
    "close": 115.2
  },
  // ... more options
}
```

## CALCULATIONS:
- ATM Strike = Math.round(spotPrice / 50) * 50
- OI in K = oi / 1000
- OI in contracts = oi / 75
- PCR = Total Put OI / Total Call OI
- LTP Change = ltp - close
- Change % = ((ltp - close) / close) * 100

## DISPLAY:
- Show ±7 strikes around ATM (15 total rows)
- Sort strikes in ascending order
- Update every 500ms

## INTERACTIVITY:
- Click on any row to see detailed option info in a modal
- Scroll to see more strikes if needed
- Pin button to keep specific strikes visible

## CODE STRUCTURE:
```typescript
interface OptionData {
  strike: number;
  ce: { ltp: number; oi: number; iv: number; change: number; } | null;
  pe: { ltp: number; oi: number; iv: number; change: number; } | null;
  isATM: boolean;
  isITM_CE: boolean;
  isITM_PE: boolean;
}

// Process raw options into organized rows
function processOptions(rawOptions: Record<string, any>, spotPrice: number): OptionData[]
```

Implement this option chain with all the futuristic styling from the base design.
```

---

## Step 4: Prompt 3 - GEX Visualization Panel

```
Now implement the GEX EXPOSURE panel (top-right) with stunning futuristic visualization.

## GEX PANEL LAYOUT:

```
┌────────────────────────────────────────────────────────────────┐
│ ◈ GAMMA EXPOSURE (GEX)                      Net: +6.52 Cr 🟢   │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│           PUT GEX (-ve)    │    CALL GEX (+ve)                │
│                            │                                   │
│  23700  ████████           │            ██████████████  +2.8   │
│  23750  ██████████████     │         █████████████████  +1.9   │
│  23800  ████████████████████│       ████████████████    +0.5   │
│ █23850█ ██████████████████ │████████████████████████████ +3.2  │ ← ATM
│  23900  ████████████████   │      ██████████████████████ +2.1  │
│  23950  ████████████       │            ████████████████ +1.8  │
│  24000  ████████           │               █████████████ +1.4  │
│                            │                                   │
│         ◄── -8.5 Cr        │        +15.0 Cr ──►              │
│                            │                                   │
├────────────────────────────────────────────────────────────────┤
│                      GEX SUMMARY                               │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐               │
│  │ CALL GEX   │  │  PUT GEX   │  │  NET GEX   │               │
│  │  +15.02 Cr │  │  -8.50 Cr  │  │  +6.52 Cr  │               │
│  │    ▲       │  │     ▼      │  │  BULLISH   │               │
│  └────────────┘  └────────────┘  └────────────┘               │
├────────────────────────────────────────────────────────────────┤
│  GAMMA WALL: 23800 (Support)  │  GAMMA FLIP: 23825            │
└────────────────────────────────────────────────────────────────┘
```

## VISUAL FEATURES:

### Horizontal Bar Chart:
- Strike prices on Y-axis (left side)
- Zero line in the middle (glowing white line)
- PUT GEX bars extend LEFT (blue/cyan color)
- CALL GEX bars extend RIGHT (red/magenta color)
- Net GEX value shown at the end of each row

### Bar Styling:
- Gradient fill (dark to bright towards tip)
- Glow effect on bars
- Animated growth when data updates
- Width proportional to GEX value

### ATM Strike Highlight:
- Golden/yellow border around the row
- Pulsing animation
- Larger strike number

### Max GEX Strikes:
- Highest positive GEX: Extra green glow
- Highest negative GEX: Extra red glow

### Interactive Features:
- Hover on bar: Show exact GEX value in tooltip
- Click on strike: Highlight corresponding row in Option Chain

### GEX Summary Cards:
Three glass cards at bottom:
1. **CALL GEX**: Red accent, total call GEX in Crores
2. **PUT GEX**: Blue accent, total put GEX in Crores (shown as negative)
3. **NET GEX**:
   - Green if positive (bullish)
   - Red if negative (bearish)
   - Large font, prominent display
   - Label showing "BULLISH" or "BEARISH"

### Key Levels Bar:
- **Gamma Wall**: Strike with highest absolute GEX (acts as support/resistance)
- **Gamma Flip**: Strike where cumulative GEX changes sign

## GEX CALCULATION:
```typescript
// GEX = Gamma × OI × Spot² × 0.01 × Contract_Size
// Result in Crores (divide by 10000000)

interface GEXData {
  strike: number;
  callGEX: number;  // Positive
  putGEX: number;   // Negative (store as negative)
  netGEX: number;   // callGEX + putGEX
}

// Gamma calculation (simplified - use IV from option data)
function calculateGamma(spot: number, strike: number, T: number, iv: number): number {
  // Black-Scholes gamma formula
  const d1 = (Math.log(spot / strike) + (0.065 + 0.5 * iv * iv) * T) / (iv * Math.sqrt(T));
  const gamma = Math.exp(-d1 * d1 / 2) / (spot * iv * Math.sqrt(2 * Math.PI * T));
  return gamma;
}

function calculateGEX(gamma: number, oi: number, spot: number): number {
  const LOT_SIZE = 75;
  const oiContracts = oi / LOT_SIZE;
  const gex = gamma * oiContracts * LOT_SIZE * spot * spot * 0.01;
  return gex / 10000000; // Convert to Crores
}
```

## DATA PROCESSING:
From /options endpoint, for each strike:
1. Get CE data (OI, LTP, IV if available)
2. Get PE data (OI, LTP, IV if available)
3. Calculate gamma for both
4. Calculate GEX:
   - Call GEX = positive
   - Put GEX = negative
5. Net GEX = Call GEX + Put GEX

## CHART LIBRARY:
Use recharts BarChart with:
- Horizontal layout (layout="vertical")
- Two bar series (Put GEX negative, Call GEX positive)
- Custom bar shape with gradient
- Reference line at x=0

## ANIMATION:
- Bars animate width on data change
- Net GEX value has counting animation
- Summary cards pulse when value changes significantly

## RESPONSIVE:
- On smaller screens, show fewer strikes
- Summary cards stack vertically on mobile

Implement this GEX panel with the futuristic styling.
```

---

## Step 5: Prompt 4 - Order Flow Panel

```
Now implement the ORDER FLOW panel (bottom-left) with futuristic footprint chart and depth visualization.

## ORDER FLOW PANEL LAYOUT:

```
┌────────────────────────────────────────────────────────────────┐
│ ◈ ORDER FLOW                                   Ticks: 12,456   │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│  ══════════════ FOOTPRINT CHART ══════════════                │
│                                                                │
│    SELL VOL    │  PRICE  │    BUY VOL    │   DELTA            │
│  ──────────────────────────────────────────────────────        │
│   ████████████ │  23880  │  ████         │   -850   🔴        │
│   ████████     │  23875  │  ████████████ │   +420   🟢        │
│   ██████       │  23870  │  ████████████████│ +1,250 🟢       │
│   ████         │ █23865█ │  ██████████████│ +980   🟢  ◄ LTP  │
│   ██████████   │  23860  │  ████████     │   -320   🔴        │
│   ████████████ │  23855  │  ██████       │   -680   🔴        │
│                                                                │
├────────────────────────────────────────────────────────────────┤
│  ══════════════ BID/ASK DEPTH ══════════════                  │
│                                                                │
│   ████████████████ 4,500 │ 23869 ║ 23871 │ 3,800 ████████████ │
│   ██████████████   3,200 │ 23868 ║ 23872 │ 2,950 ██████████   │
│   ████████████     2,800 │ 23867 ║ 23873 │ 2,400 ████████     │
│   ██████████       2,100 │ 23866 ║ 23874 │ 1,950 ██████       │
│   ████████         1,600 │ 23865 ║ 23875 │ 1,700 ████         │
│                                                                │
│   TOTAL BID: 14,200      ║      TOTAL ASK: 12,800             │
│                          ║                                     │
│   ████████████████████████║██████████████████████              │
│         BID PRESSURE      ║      ASK PRESSURE                  │
└────────────────────────────────────────────────────────────────┘
```

## FOOTPRINT CHART FEATURES:

### Price Ladder (Center):
- Current LTP highlighted with:
  - Glowing yellow border
  - Pulsing animation
  - "◄ LTP" indicator
- Price levels in monospace font
- Show 10-12 price levels around LTP

### Volume Bars:
- SELL bars (left): Red gradient, extend left
- BUY bars (right): Green gradient, extend right
- Bar width proportional to volume
- Glow effect on high volume

### Delta Column:
- Delta = Buy Volume - Sell Volume
- Positive delta: Green text with 🟢
- Negative delta: Red text with 🔴
- Large absolute delta: Extra bright/glow

### Volume Imbalance Highlighting:
- If Buy > 2x Sell: Green highlight on row
- If Sell > 2x Buy: Red highlight on row
- Add small "IMBALANCE" tag

### Animation:
- New volume appears with flash effect
- Bars animate smoothly on update

## BID/ASK DEPTH FEATURES:

### Split View:
- Left side: BIDS (green)
- Right side: ASKS (red)
- Center divider: Glowing yellow line

### Each Level Shows:
- Quantity (number)
- Price
- Proportional bar

### Visual Hierarchy:
- Level 1 (best bid/ask): Largest, brightest
- Deeper levels: Progressively smaller/dimmer

### Totals Bar:
- Total Bid Quantity vs Total Ask Quantity
- Single bar showing proportion
- Green portion = bid dominance
- Red portion = ask dominance

### Spread Indicator:
- Show bid-ask spread
- Color: Green if tight (< 2), Yellow if normal, Red if wide

## DATA SOURCE:
GET /tick returns:
```javascript
{
  ltp: 23865,
  ltq: 150,  // Last traded quantity
  best_bids: [23869, 23868, 23867, 23866, 23865],
  best_asks: [23871, 23872, 23873, 23874, 23875],
  bid_qty: [4500, 3200, 2800, 2100, 1600],
  ask_qty: [3800, 2950, 2400, 1950, 1700],
  total_buy_qty: 125000,
  total_sell_qty: 118000
}
```

## ORDER FLOW LOGIC:

### Trade Direction Classification:
```typescript
function classifyTrade(ltp: number, bids: number[], asks: number[], prevLtp: number): 'BUY' | 'SELL' {
  if (ltp >= asks[0]) return 'BUY';   // Lifted offer
  if (ltp <= bids[0]) return 'SELL';  // Hit bid
  // Tick rule fallback
  return ltp > prevLtp ? 'BUY' : 'SELL';
}
```

### Footprint Aggregation:
```typescript
interface FootprintLevel {
  price: number;
  buyVolume: number;
  sellVolume: number;
  delta: number;
}

// Aggregate by price level, keep last N levels
```

### State Management:
```typescript
// Use useRef for mutable state that doesn't trigger re-render
const footprintRef = useRef<Map<number, FootprintLevel>>(new Map());
const prevLtpRef = useRef<number>(0);
```

## POLLING:
- Fetch /tick every 100ms
- Only process if LTP or LTQ changed
- Aggregate into footprint levels

## PERFORMANCE:
- Use virtualization if many price levels
- Debounce UI updates to 200ms
- Use CSS transforms for animations (GPU accelerated)

## COLORS:
- Bid/Buy: #00ff88 (matrix green)
- Ask/Sell: #ff3366 (danger red)
- LTP highlight: #ffd700 (gold)
- Imbalance: Extra saturation of respective color

Implement this order flow panel with all the futuristic effects.
```

---

## Step 6: Prompt 5 - CVD, Analytics & Alerts Panel

```
Now implement the CVD & ANALYTICS panel (bottom-right) with charts and alerts feed.

## PANEL LAYOUT:

```
┌────────────────────────────────────────────────────────────────┐
│ ◈ CVD & ANALYTICS                           CVD: +12,450 ▲    │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│  ══════════════ CVD LINE CHART ══════════════                 │
│                                                                │
│     +15K ┤                              ╱╲                     │
│     +10K ┤              ╱╲    ╱╲      ╱  ╲    ╱               │
│      +5K ┤       ╱╲   ╱  ╲  ╱  ╲    ╱    ╲  ╱                │
│        0 ┼──────────────────────────────────────────          │
│      -5K ┤  ╲  ╱                                               │
│     -10K ┤   ╲╱                                                │
│          └──────────────────────────────────────────►         │
│            09:15    10:00    11:00    12:00    13:00          │
│                                                                │
│  CVD: +12,450  │  Buy Vol: 1.25L  │  Sell Vol: 1.12L         │
│                                                                │
├────────────────────────────────────────────────────────────────┤
│  ══════════════ DELTA BARS ══════════════                     │
│                                                                │
│      ▐▌  ▐▌▐▌    ▐▌       ▐▌   ▐▌                             │
│      ▐▌  ▐▌▐▌    ▐▌   ▄   ▐▌   ▐▌  ▐▌                         │
│  ▄▄  ▐▌▄▄▐▌▐▌ ▄▄ ▐▌ ▄██▄  ▐▌▄▄▄▐▌▄▄▐▌▄▄                      │
│  ██████████████████████████████████████████                   │
│  ▀▀      ▀▀        ▀▀                 ▀▀                      │
│      ▐▌          ▐▌                                           │
│                                                                │
│  Current Δ: +850  │  Avg Δ: +420  │  Max Δ: +2,450           │
│                                                                │
├────────────────────────────────────────────────────────────────┤
│  ══════════════ LIVE ALERTS ══════════════                    │
│                                                                │
│  🔴 14:32:40  BIG BLOCK                                       │
│     BUY 4,500 qty @ 23871 (60 lots)                           │
│                                                                │
│  🟠 14:31:15  IMBALANCE DETECTED                              │
│     Buy/Sell Ratio: 3.2x at 23865                             │
│                                                                │
│  🔵 14:30:02  HIGH VOLUME CANDLE                              │
│     1-min volume: 25,000 (3x average)                         │
│                                                                │
│  🟢 14:28:45  CVD DIVERGENCE                                  │
│     Price up but CVD down - potential reversal                │
│                                                                │
├────────────────────────────────────────────────────────────────┤
│  KEY LEVELS  │  Max Pain: 23800  │  HCE: 24000  │  HPE: 23500 │
└────────────────────────────────────────────────────────────────┘
```

## CVD LINE CHART FEATURES:

### Chart Design:
- Area chart with gradient fill
- Fill color: Green when CVD > 0, Red when CVD < 0
- Line color: Bright green/red based on current direction
- Smooth curve (tension: 0.4)

### Zero Line:
- Horizontal dashed line at y=0
- White color with low opacity
- Acts as reference

### Y-Axis:
- Dynamic scale based on CVD range
- Format: +10K, -5K, etc.
- Grid lines with low opacity

### X-Axis:
- Time labels (HH:MM format)
- Show last 2 hours of data
- Current time at right edge

### Current CVD Indicator:
- Large value in corner
- Arrow (▲/▼) showing direction
- Color matches trend

### CVD Stats Bar:
- CVD Value
- Total Buy Volume
- Total Sell Volume
- Format large numbers: 1,25,000 → 1.25L

## DELTA BARS FEATURES:

### Bar Chart:
- Each bar = 1 minute candle's delta
- Positive delta: Green bar above zero
- Negative delta: Red bar below zero
- Show last 30 bars

### Current Bar:
- Highlighted with brighter color
- Animated as it updates

### Stats:
- Current Delta
- Average Delta
- Max Delta (absolute)

## ALERTS FEED FEATURES:

### Alert Types:
1. **BIG BLOCK** 🔴 (CRITICAL)
   - Triggered when ltq > 3750 (50 lots)
   - Show: Direction, Qty, Price, Lots

2. **IMBALANCE** 🟠 (WARNING)
   - Triggered when buy/sell ratio > 2.5
   - Show: Ratio, Price level

3. **HIGH VOLUME** 🔵 (INFO)
   - Triggered when 1-min volume > 3x average
   - Show: Volume, Multiple of average

4. **CVD DIVERGENCE** 🟢 (INFO)
   - Price moving up but CVD down (or vice versa)
   - Show: Divergence type, Implication

### Alert Display:
- Newest alerts at top
- Show last 4-5 alerts
- Auto-scroll on new alert
- Fade effect for older alerts

### Alert Animation:
- New alert slides in from top
- Brief flash/glow effect
- Sound option (toggleable)

### Alert Structure:
```typescript
interface Alert {
  id: string;
  timestamp: string;
  type: 'BIG_BLOCK' | 'IMBALANCE' | 'HIGH_VOLUME' | 'CVD_DIVERGENCE';
  severity: 'CRITICAL' | 'WARNING' | 'INFO';
  message: string;
  details: string;
}
```

## KEY LEVELS BAR:
- Max Pain: Strike where option writers have minimum loss
- HCE (Highest Call OI): Strong resistance
- HPE (Highest Put OI): Strong support
- Each value in a small badge

## DATA MANAGEMENT:

### CVD Tracking:
```typescript
const [cvdHistory, setCvdHistory] = useState<{time: string, value: number}[]>([]);
const [currentCVD, setCurrentCVD] = useState(0);
const [buyVolume, setBuyVolume] = useState(0);
const [sellVolume, setSellVolume] = useState(0);

// On each tick
function processTick(tick: TickData, direction: 'BUY' | 'SELL') {
  const qty = tick.ltq;
  if (direction === 'BUY') {
    setBuyVolume(prev => prev + qty);
    setCurrentCVD(prev => prev + qty);
  } else {
    setSellVolume(prev => prev + qty);
    setCurrentCVD(prev => prev - qty);
  }

  // Add to history every second
  setCvdHistory(prev => [...prev.slice(-200), {
    time: new Date().toLocaleTimeString(),
    value: currentCVD
  }]);
}
```

### Delta Bars:
```typescript
interface DeltaCandle {
  time: string;
  buyVol: number;
  sellVol: number;
  delta: number;
}

// Aggregate by minute
const deltaCandles = useRef<Map<string, DeltaCandle>>(new Map());
```

### Alert Generation:
```typescript
function checkForAlerts(tick: TickData, state: OrderFlowState): Alert[] {
  const alerts: Alert[] = [];

  // Big block check
  if (tick.ltq > 3750) {
    alerts.push({
      type: 'BIG_BLOCK',
      severity: 'CRITICAL',
      // ...
    });
  }

  // Imbalance check
  const ratio = Math.max(state.buyVol, state.sellVol) / Math.min(state.buyVol, state.sellVol);
  if (ratio > 2.5) {
    alerts.push({
      type: 'IMBALANCE',
      severity: 'WARNING',
      // ...
    });
  }

  return alerts;
}
```

## CHARTS:
Use recharts:
- AreaChart for CVD
- BarChart for Delta
- Custom gradient definitions
- Responsive container

Implement this CVD & Analytics panel with futuristic styling.
```

---

## Step 7: Polish Prompts - Futuristic Effects

### Polish Prompt 1: Scan Lines & CRT Effect

```
Add a subtle CRT monitor / sci-fi scan line effect to the entire dashboard:

1. Create a full-screen overlay with scan lines:
```css
.scanlines::before {
  content: "";
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: repeating-linear-gradient(
    0deg,
    rgba(0, 0, 0, 0.1) 0px,
    rgba(0, 0, 0, 0.1) 1px,
    transparent 1px,
    transparent 2px
  );
  pointer-events: none;
  z-index: 9999;
  animation: scanMove 8s linear infinite;
}

@keyframes scanMove {
  0% { transform: translateY(0); }
  100% { transform: translateY(4px); }
}
```

2. Add subtle screen flicker:
```css
@keyframes flicker {
  0%, 100% { opacity: 1; }
  92% { opacity: 1; }
  93% { opacity: 0.95; }
  94% { opacity: 1; }
}
```

3. Add vignette effect (darker corners):
```css
.vignette::after {
  content: "";
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: radial-gradient(ellipse at center, transparent 60%, rgba(0,0,0,0.4) 100%);
  pointer-events: none;
}
```

4. Add toggle to disable effects for performance (button in header).

Make it subtle - we want sci-fi feel, not annoying.
```

---

### Polish Prompt 2: Sound Effects

```
Add optional sound effects for alerts and important events:

1. Create a SoundManager utility:
```typescript
class SoundManager {
  private enabled: boolean = false;
  private audioContext: AudioContext | null = null;

  toggle() { this.enabled = !this.enabled; }

  playBeep(frequency: number = 800, duration: number = 100) {
    if (!this.enabled) return;
    // Web Audio API beep
  }

  playAlert(type: 'critical' | 'warning' | 'info') {
    if (!this.enabled) return;
    const frequencies = {
      critical: [800, 600, 800],  // Triple beep
      warning: [600, 400],         // Double beep
      info: [500]                  // Single beep
    };
    // Play sequence
  }
}
```

2. Add sound toggle button in header (🔔 icon):
   - Muted by default
   - Click to enable
   - Visual indicator (crossed out when muted)

3. Trigger sounds:
   - BIG_BLOCK alert: Critical sound
   - IMBALANCE alert: Warning sound
   - Price breakout: Info sound

4. Keep sounds short and non-intrusive.
```

---

### Polish Prompt 3: Keyboard Shortcuts

```
Add keyboard shortcuts for power users:

1. Shortcut mappings:
   - `1` - Focus Option Chain panel
   - `2` - Focus GEX panel
   - `3` - Focus Order Flow panel
   - `4` - Focus CVD panel
   - `Space` - Toggle sound
   - `F` - Toggle fullscreen
   - `R` - Reset/refresh data
   - `Esc` - Close any open modal
   - `+/-` - Zoom in/out on charts

2. Show shortcuts hint on `?` key press:
   - Modal with all shortcuts listed
   - Futuristic styling

3. Visual feedback:
   - Brief border glow on focused panel
   - Toast notification showing action

4. Add hint in header: "Press ? for shortcuts"
```

---

### Polish Prompt 4: Number Animations

```
Add smooth counting animations for all numeric values:

1. Create AnimatedNumber component:
```typescript
interface AnimatedNumberProps {
  value: number;
  duration?: number;
  formatFn?: (n: number) => string;
  colorChange?: boolean;  // Flash green/red on change
}

function AnimatedNumber({ value, duration = 300, formatFn, colorChange }: AnimatedNumberProps) {
  const [displayValue, setDisplayValue] = useState(value);
  const [changeColor, setChangeColor] = useState<'up' | 'down' | null>(null);

  useEffect(() => {
    // Animate from current to new value
    const start = displayValue;
    const diff = value - start;
    const startTime = Date.now();

    if (colorChange) {
      setChangeColor(diff > 0 ? 'up' : 'down');
      setTimeout(() => setChangeColor(null), 500);
    }

    const animate = () => {
      const elapsed = Date.now() - startTime;
      const progress = Math.min(elapsed / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3); // Ease out

      setDisplayValue(start + diff * eased);

      if (progress < 1) requestAnimationFrame(animate);
    };

    requestAnimationFrame(animate);
  }, [value]);

  return (
    <span className={cn(
      "transition-colors duration-200",
      changeColor === 'up' && "text-green-400",
      changeColor === 'down' && "text-red-400"
    )}>
      {formatFn ? formatFn(displayValue) : displayValue.toFixed(2)}
    </span>
  );
}
```

2. Use for:
   - Spot price
   - Futures price
   - CVD value
   - GEX totals
   - All OI values
   - All LTP values

3. Add flash effect on significant changes (> 0.1%).
```

---

### Polish Prompt 5: Connection Status & Reconnection

```
Improve connection handling with visual feedback:

1. Connection status indicator in header:
```typescript
type ConnectionStatus = 'connected' | 'connecting' | 'disconnected' | 'error';

function ConnectionIndicator({ status }: { status: ConnectionStatus }) {
  const config = {
    connected: { color: '#00ff88', label: 'LIVE', pulse: true },
    connecting: { color: '#ffd700', label: 'CONNECTING...', pulse: true },
    disconnected: { color: '#ff3366', label: 'OFFLINE', pulse: false },
    error: { color: '#ff3366', label: 'ERROR', pulse: true }
  };

  return (
    <div className="flex items-center gap-2">
      <span className={cn(
        "w-2 h-2 rounded-full",
        config[status].pulse && "animate-pulse"
      )} style={{ backgroundColor: config[status].color }} />
      <span className="text-xs font-mono">{config[status].label}</span>
    </div>
  );
}
```

2. Auto-reconnection logic:
```typescript
const reconnect = useCallback(async () => {
  setStatus('connecting');
  let attempts = 0;

  while (attempts < 5) {
    try {
      await fetch(`${API_URL}/health`);
      setStatus('connected');
      return;
    } catch {
      attempts++;
      await new Promise(r => setTimeout(r, 2000 * attempts)); // Exponential backoff
    }
  }

  setStatus('error');
}, []);
```

3. Show overlay when disconnected:
   - Semi-transparent dark overlay
   - "Reconnecting..." message with spinner
   - Retry button
   - Show last data timestamp

4. Keep UI responsive even when disconnected (show stale data with warning).
```

---

## Step 8: Complete Setup & Running

### 8.1 Download from Lovable

```
1. Jab sab prompts complete ho jayein
2. Lovable mein "Export" ya "Download" button click karo
3. ZIP file download hogi
4. Extract karo: /Users/harsh/Desktop/nifty-terminal/
```

### 8.2 Project Structure

```
/Users/harsh/Desktop/nifty-terminal/
├── src/
│   ├── components/
│   │   ├── Header.tsx
│   │   ├── OptionChain.tsx
│   │   ├── GEXPanel.tsx
│   │   ├── OrderFlowPanel.tsx
│   │   ├── CVDPanel.tsx
│   │   ├── AlertsFeed.tsx
│   │   └── ui/
│   │       ├── AnimatedNumber.tsx
│   │       ├── GlassCard.tsx
│   │       └── ConnectionIndicator.tsx
│   ├── hooks/
│   │   ├── useMarketData.ts
│   │   ├── useOrderFlow.ts
│   │   └── useAlerts.ts
│   ├── utils/
│   │   ├── calculations.ts
│   │   └── soundManager.ts
│   ├── App.tsx
│   └── main.tsx
├── public/
├── package.json
├── tailwind.config.js
└── vite.config.ts
```

### 8.3 Install Dependencies

```bash
# Terminal mein jao
cd /Users/harsh/Desktop/nifty-terminal

# Dependencies install karo
npm install

# Agar error aaye toh
npm install --legacy-peer-deps
```

### 8.4 Running Both Servers

**Terminal 1: Data Server (Backend)**
```bash
cd /Users/harsh/Desktop/test2
python3 data_server.py
```

Wait for:
```
======================================================================
                        DATA SERVER RUNNING
======================================================================
                    HTTP API: http://127.0.0.1:8888
======================================================================
```

**Terminal 2: React Dashboard (Frontend)**
```bash
cd /Users/harsh/Desktop/nifty-terminal
npm run dev
```

Wait for:
```
  VITE v5.x.x  ready in xxx ms

  ➜  Local:   http://localhost:5173/
  ➜  Network: http://192.168.x.x:5173/
```

**Browser mein open karo:**
```
http://localhost:5173
```

### 8.5 Mobile/Tablet Access

Same WiFi pe connected device mein:
```
http://192.168.x.x:5173
```
(IP address Terminal 2 mein dikhega)

### 8.6 Troubleshooting

| Problem | Solution |
|---------|----------|
| "CORS Error" | data_server.py mein `CORS(app)` hai, verify karo |
| "Connection refused" | data_server.py pehle start karo |
| "No data" | Market hours mein test karo (9:15 AM - 3:30 PM) |
| "npm error" | `npm install --legacy-peer-deps` try karo |
| "Blank screen" | Browser console check karo (F12 → Console) |

---

## Complete Checklist

### Prompt Sequence:

| Step | Prompt | Credits Est. | Time |
|------|--------|--------------|------|
| 1 | Base Layout + Header | ~15 | 2-3 min |
| 2 | Option Chain Panel | ~20 | 3-4 min |
| 3 | GEX Panel | ~20 | 3-4 min |
| 4 | Order Flow Panel | ~20 | 3-4 min |
| 5 | CVD + Alerts Panel | ~20 | 3-4 min |
| 6 | Polish: Scan Lines | ~5 | 1 min |
| 7 | Polish: Sound | ~5 | 1 min |
| 8 | Polish: Shortcuts | ~5 | 1 min |
| 9 | Polish: Animations | ~5 | 1 min |
| 10 | Polish: Connection | ~5 | 1 min |
| **Total** | | **~120** | **~25 min** |

---

## Quick Start Summary

```
Step 1: Lovable.dev pe Sign Up
Step 2: New Project → "NIFTY Futuristic Terminal"
Step 3: Prompt 1 paste karo (Base + Header)
Step 4: Prompt 2 paste karo (Option Chain)
Step 5: Prompt 3 paste karo (GEX)
Step 6: Prompt 4 paste karo (Order Flow)
Step 7: Prompt 5 paste karo (CVD + Alerts)
Step 8: Polish prompts (1-5) ek ek karke
Step 9: Download code
Step 10: npm install && npm run dev
Step 11: data_server.py bhi run karo
Step 12: Enjoy! 🎉
```

---

## Pro Tips

1. **Agar credits kam padein:**
   - Step 1-5 zaroor karo (main panels)
   - Polish prompts optional hain

2. **Lovable se zyada lena ho toh:**
   - Ek prompt mein pura panel describe karo
   - Iterative changes kam karo

3. **Bug fix ke liye:**
   - Error message copy karo
   - Lovable ko paste karo: "Fix this error: [error]"

4. **Custom changes:**
   - Lovable ka code export karke manually bhi edit kar sakte ho
   - VS Code mein open karo

---

## API Reference

### Base URL
```
http://127.0.0.1:8888
```

### Endpoints

| Endpoint | Method | Description | Response |
|----------|--------|-------------|----------|
| `/health` | GET | Server health check | `{ status, connected, tick_count }` |
| `/spot` | GET | NIFTY spot data | `{ ltp, open, high, low, close }` |
| `/futures` | GET | Futures data | `{ ltp, symbol, oi, volume, ltq }` |
| `/options` | GET | All options | `{ [token]: { strike, type, ltp, oi } }` |
| `/depth` | GET | Bid/Ask depth | `{ best_bids, best_asks, bid_qty, ask_qty }` |
| `/tick` | GET | Latest tick | `{ ltp, ltq, best_bids, best_asks, ... }` |
| `/all` | GET | Everything | Complete data object |

---

## Color Reference

| Color | Hex | Usage |
|-------|-----|-------|
| Background | `#0a0a0f` | Main background |
| Cyan | `#00fff5` | Primary accent, headers |
| Magenta | `#ff00ff` | Secondary accent |
| Green | `#00ff88` | Bullish, buy, positive |
| Red | `#ff3366` | Bearish, sell, negative |
| Orange | `#ff9500` | Warnings |
| Gold | `#ffd700` | ATM highlight |
| Glass BG | `#12121a` | Card backgrounds |

---

*Created for NIFTY Intraday Trading System*
*Last Updated: December 2024*
