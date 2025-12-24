"""
NIFTY Trading System - Black-Scholes Greeks Calculator
Calculates IV, Delta, Gamma, Theta, Vega for options.
"""

import math


def norm_cdf(x):
    """Standard normal cumulative distribution function"""
    return (1.0 + math.erf(x / math.sqrt(2.0))) / 2.0


def norm_pdf(x):
    """Standard normal probability density function"""
    return math.exp(-0.5 * x * x) / math.sqrt(2 * math.pi)


def calculate_d1_d2(S, K, T, r, sigma):
    """Calculate d1 and d2 for Black-Scholes"""
    if T <= 0 or sigma <= 0:
        return 0, 0
    d1 = (math.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * math.sqrt(T))
    d2 = d1 - sigma * math.sqrt(T)
    return d1, d2


def bs_price(S, K, T, r, sigma, option_type):
    """Black-Scholes option price"""
    if T <= 0:
        if option_type == 'CE':
            return max(0, S - K)
        else:
            return max(0, K - S)

    d1, d2 = calculate_d1_d2(S, K, T, r, sigma)

    if option_type == 'CE':
        price = S * norm_cdf(d1) - K * math.exp(-r * T) * norm_cdf(d2)
    else:
        price = K * math.exp(-r * T) * norm_cdf(-d2) - S * norm_cdf(-d1)

    return price


def implied_volatility(market_price, S, K, T, r, option_type, max_iter=100):
    """Calculate implied volatility using Bisection method (guaranteed convergence)"""
    if T <= 0 or market_price <= 0:
        return 0

    # Calculate intrinsic value
    intrinsic = max(0, S - K) if option_type == 'CE' else max(0, K - S)

    # If market price is less than intrinsic (deep ITM, negative time value)
    if market_price < intrinsic:
        return 0.01  # 1% IV for deep ITM (Gamma will be ~0)

    # Bisection method: guaranteed to converge
    low_vol = 0.001   # 0.1% IV (lower bound for better precision)
    high_vol = 5.0    # 500% IV (higher bound for edge cases)

    # Adaptive tolerance based on price magnitude
    tolerance = max(0.01, market_price * 0.001)  # 0.1% of price or min 0.01

    for _ in range(max_iter):
        mid_vol = (low_vol + high_vol) / 2
        mid_price = bs_price(S, K, T, r, mid_vol, option_type)

        diff = mid_price - market_price

        if abs(diff) < tolerance:
            return mid_vol

        if diff > 0:
            # Price too high, reduce IV
            high_vol = mid_vol
        else:
            # Price too low, increase IV
            low_vol = mid_vol

        # Check if range is small enough (IV precision)
        if (high_vol - low_vol) < 0.0001:
            break

    return mid_vol


def calculate_delta(S, K, T, r, sigma, option_type):
    """Calculate Delta"""
    if T <= 0 or sigma <= 0:
        if option_type == 'CE':
            return 1.0 if S > K else 0.0
        else:
            return -1.0 if S < K else 0.0

    d1, _ = calculate_d1_d2(S, K, T, r, sigma)

    if option_type == 'CE':
        return norm_cdf(d1)
    else:
        return norm_cdf(d1) - 1


def calculate_gamma(S, K, T, r, sigma):
    """Calculate Gamma (same for CE and PE)"""
    if T <= 0 or sigma <= 0:
        return 0

    d1, _ = calculate_d1_d2(S, K, T, r, sigma)
    return norm_pdf(d1) / (S * sigma * math.sqrt(T))


def calculate_theta(S, K, T, r, sigma, option_type):
    """Calculate Theta (per day)"""
    if T <= 0 or sigma <= 0:
        return 0

    d1, d2 = calculate_d1_d2(S, K, T, r, sigma)

    term1 = -(S * norm_pdf(d1) * sigma) / (2 * math.sqrt(T))

    if option_type == 'CE':
        term2 = -r * K * math.exp(-r * T) * norm_cdf(d2)
    else:
        term2 = r * K * math.exp(-r * T) * norm_cdf(-d2)

    return (term1 + term2) / 365  # Per day


def calculate_vega(S, K, T, r, sigma):
    """Calculate Vega (same for CE and PE)"""
    if T <= 0 or sigma <= 0:
        return 0

    d1, _ = calculate_d1_d2(S, K, T, r, sigma)
    return S * norm_pdf(d1) * math.sqrt(T) / 100  # Per 1% change
