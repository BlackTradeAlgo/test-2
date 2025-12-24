# Claude Project Rules – NIFTY Intraday Only

These rules are **strict and mandatory** for this trading project.

---

## 1. Project Scope (Non-Negotiable)

- Instrument: **NIFTY only**
- Trading type: **Intraday only**
- No SENSEX, BANKNIFTY, stocks, or positional trades

If anything goes beyond NIFTY intraday → **STOP and ask**.

---

## 2. General Behavior

- Do not assume anything
- Do not change existing logic without approval
- Do not suggest alternative architectures or “better approaches”
- Explain first → get confirmation → then implement

---

## 3. Error Handling (Very Important)

If **any error occurs**, follow **only this path**:

1. Identify the exact root cause  
2. Specify file and location  
3. Propose a **minimal fix**  
4. Preserve the existing flow  
5. Implement **only after approval**

❌ No rewrites  
❌ No shortcuts  
❌ No redesigns  

**Rule:** Fix the problem, do not change the system.

---

## 4. Angel One API Safety

- Do not touch login, auth, tokens, or credentials
- Do not change WebSocket modes or subscriptions
- Do not hardcode secrets

Angel One integration is **already working and must remain unchanged**.

---

## 5. Files & Code Changes

- Do not auto-create or overwrite files
- Always propose file name + purpose first
- Modify only what is explicitly approved

---

## 6. Trading & ML Rules

- No live trading logic without permission
- No ML models unless explicitly requested
- Do not change thresholds, labels, or risk logic on your own

---

## 7. Assumptions Are Forbidden

Never assume:
- Lot size
- Market hours
- Margin or brokerage
- Exchange rules

If information is missing → **ask first**.

---

## Final Rule

This is a **production-focused NIFTY intraday system**, not an experiment.

**Stability > New ideas**  
**Fix > Redesign**
