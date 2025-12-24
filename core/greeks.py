"""
NIFTY Trading System - Black-Scholes Greeks Calculator
Calculates IV, Delta, Gamma, Theta, Vega for options.

Supports both:
- Standard Black-Scholes (without dividend)
- Dividend-Adjusted Black-Scholes (with dividend yield q)

For NIFTY/BANKNIFTY, use dividend-adjusted functions for accuracy.
"""

import math


# ============== COMMON FUNCTIONS ==============

def norm_cdf(x):
    """Standard normal cumulative distribution function"""
    return (1.0 + math.erf(x / math.sqrt(2.0))) / 2.0


def norm_pdf(x):
    """Standard normal probability density function"""
    return math.exp(-0.5 * x * x) / math.sqrt(2 * math.pi)


# ============== DIVIDEND YIELD CALCULATION ==============

def calculate_implied_dividend_yield(spot, futures, T, r):
    """
    Calculate implied dividend yield from futures price
    q = r - (ln(F/S) / T)

    Args:
        spot: Current spot price
        futures: Current futures price
        T: Time to expiry in years
        r: Risk-free rate (e.g., 0.065 for 6.5%)

    Returns:
        Implied dividend yield (e.g., 0.012 for 1.2%)
    """
    if T <= 0 or spot <= 0 or futures <= 0:
        return 0.012  # Default 1.2%

    try:
        q = r - (math.log(futures / spot) / T)
        # Clamp to reasonable range (0% to 5%)
        return max(0, min(q, 0.05))
    except:
        return 0.012  # Default 1.2%


# ============== DIVIDEND-ADJUSTED BLACK-SCHOLES (RECOMMENDED) ==============

def calculate_d1_d2_div(S, K, T, r, q, sigma):
    """
    Calculate d1 and d2 for dividend-adjusted Black-Scholes
    d1 = (ln(S/K) + (r - q + 0.5*sigma^2)*T) / (sigma * sqrt(T))
    d2 = d1 - sigma * sqrt(T)

    Args:
        S: Spot price
        K: Strike price
        T: Time to expiry in years
        r: Risk-free rate
        q: Dividend yield
        sigma: Volatility
    """
    if T <= 0 or sigma <= 0 or S <= 0 or K <= 0:
        return 0, 0

    sqrt_T = math.sqrt(T)
    d1 = (math.log(S / K) + (r - q + 0.5 * sigma ** 2) * T) / (sigma * sqrt_T)
    d2 = d1 - sigma * sqrt_T
    return d1, d2


def bs_price_div(S, K, T, r, q, sigma, option_type):
    """
    Black-Scholes price with continuous dividend yield
    Call = S * e^(-qT) * N(d1) - K * e^(-rT) * N(d2)
    Put  = K * e^(-rT) * N(-d2) - S * e^(-qT) * N(-d1)
    """
    if T <= 0:
        if option_type == 'CE':
            return max(0, S - K)
        else:
            return max(0, K - S)

    d1, d2 = calculate_d1_d2_div(S, K, T, r, q, sigma)

    if option_type == 'CE':
        price = S * math.exp(-q * T) * norm_cdf(d1) - K * math.exp(-r * T) * norm_cdf(d2)
    else:
        price = K * math.exp(-r * T) * norm_cdf(-d2) - S * math.exp(-q * T) * norm_cdf(-d1)

    return max(0, price)


def implied_volatility_div(market_price, S, K, T, r, q, option_type, max_iter=100):
    """
    Calculate IV using Bisection method with dividend-adjusted BS

    Args:
        market_price: Current option market price
        S: Spot price
        K: Strike price
        T: Time to expiry in years
        r: Risk-free rate
        q: Dividend yield
        option_type: 'CE' or 'PE'
        max_iter: Maximum iterations

    Returns:
        Implied volatility (e.g., 0.15 for 15%)
    """
    if T <= 0 or market_price <= 0:
        return 0

    # Calculate intrinsic value
    intrinsic = max(0, S - K) if option_type == 'CE' else max(0, K - S)

    # If market price is less than intrinsic (deep ITM)
    if market_price < intrinsic:
        return 0.01  # 1% IV

    # Bisection method
    low_vol = 0.001
    high_vol = 5.0
    tolerance = max(0.01, market_price * 0.001)

    for _ in range(max_iter):
        mid_vol = (low_vol + high_vol) / 2
        mid_price = bs_price_div(S, K, T, r, q, mid_vol, option_type)

        diff = mid_price - market_price

        if abs(diff) < tolerance:
            return mid_vol

        if diff > 0:
            high_vol = mid_vol
        else:
            low_vol = mid_vol

        if (high_vol - low_vol) < 0.0001:
            break

    return mid_vol


def calculate_delta_div(S, K, T, r, q, sigma, option_type):
    """
    Calculate Delta with dividend adjustment
    Call Delta = e^(-qT) * N(d1)
    Put Delta  = e^(-qT) * (N(d1) - 1)
    """
    if T <= 0 or sigma <= 0:
        if option_type == 'CE':
            return 1.0 if S > K else 0.0
        else:
            return -1.0 if S < K else 0.0

    d1, _ = calculate_d1_d2_div(S, K, T, r, q, sigma)

    if option_type == 'CE':
        return math.exp(-q * T) * norm_cdf(d1)
    else:
        return math.exp(-q * T) * (norm_cdf(d1) - 1)


def calculate_gamma_div(S, K, T, r, q, sigma):
    """
    Calculate Gamma with dividend adjustment
    Gamma = e^(-qT) * N'(d1) / (S * sigma * sqrt(T))

    Note: Gamma is same for both Call and Put
    """
    if T <= 0 or sigma <= 0 or S <= 0:
        return 0

    d1, _ = calculate_d1_d2_div(S, K, T, r, q, sigma)
    sqrt_T = math.sqrt(T)

    gamma = math.exp(-q * T) * norm_pdf(d1) / (S * sigma * sqrt_T)
    return gamma


def calculate_theta_div(S, K, T, r, q, sigma, option_type):
    """
    Calculate Theta with dividend adjustment (per day)
    """
    if T <= 0 or sigma <= 0:
        return 0

    d1, d2 = calculate_d1_d2_div(S, K, T, r, q, sigma)
    sqrt_T = math.sqrt(T)

    # First term (same for call and put)
    term1 = -(S * math.exp(-q * T) * norm_pdf(d1) * sigma) / (2 * sqrt_T)

    if option_type == 'CE':
        term2 = q * S * math.exp(-q * T) * norm_cdf(d1)
        term3 = -r * K * math.exp(-r * T) * norm_cdf(d2)
    else:
        term2 = -q * S * math.exp(-q * T) * norm_cdf(-d1)
        term3 = r * K * math.exp(-r * T) * norm_cdf(-d2)

    return (term1 + term2 + term3) / 365  # Per day


def calculate_vega_div(S, K, T, r, q, sigma):
    """
    Calculate Vega with dividend adjustment (per 1% IV change)
    Vega = S * e^(-qT) * sqrt(T) * N'(d1)

    Note: Vega is same for both Call and Put
    """
    if T <= 0 or sigma <= 0:
        return 0

    d1, _ = calculate_d1_d2_div(S, K, T, r, q, sigma)
    vega = S * math.exp(-q * T) * math.sqrt(T) * norm_pdf(d1) / 100  # Per 1% change
    return vega


# ============== STANDARD BLACK-SCHOLES (BACKWARD COMPATIBILITY) ==============

def calculate_d1_d2(S, K, T, r, sigma):
    """Calculate d1 and d2 for standard Black-Scholes (no dividend)"""
    if T <= 0 or sigma <= 0:
        return 0, 0
    d1 = (math.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * math.sqrt(T))
    d2 = d1 - sigma * math.sqrt(T)
    return d1, d2


def bs_price(S, K, T, r, sigma, option_type):
    """Black-Scholes option price (no dividend)"""
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
    """Calculate IV using Bisection method (no dividend)"""
    if T <= 0 or market_price <= 0:
        return 0

    intrinsic = max(0, S - K) if option_type == 'CE' else max(0, K - S)

    if market_price < intrinsic:
        return 0.01

    low_vol = 0.001
    high_vol = 5.0
    tolerance = max(0.01, market_price * 0.001)

    for _ in range(max_iter):
        mid_vol = (low_vol + high_vol) / 2
        mid_price = bs_price(S, K, T, r, mid_vol, option_type)

        diff = mid_price - market_price

        if abs(diff) < tolerance:
            return mid_vol

        if diff > 0:
            high_vol = mid_vol
        else:
            low_vol = mid_vol

        if (high_vol - low_vol) < 0.0001:
            break

    return mid_vol


def calculate_delta(S, K, T, r, sigma, option_type):
    """Calculate Delta (no dividend)"""
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
    """Calculate Gamma (no dividend, same for CE and PE)"""
    if T <= 0 or sigma <= 0:
        return 0

    d1, _ = calculate_d1_d2(S, K, T, r, sigma)
    return norm_pdf(d1) / (S * sigma * math.sqrt(T))


def calculate_theta(S, K, T, r, sigma, option_type):
    """Calculate Theta per day (no dividend)"""
    if T <= 0 or sigma <= 0:
        return 0

    d1, d2 = calculate_d1_d2(S, K, T, r, sigma)

    term1 = -(S * norm_pdf(d1) * sigma) / (2 * math.sqrt(T))

    if option_type == 'CE':
        term2 = -r * K * math.exp(-r * T) * norm_cdf(d2)
    else:
        term2 = r * K * math.exp(-r * T) * norm_cdf(-d2)

    return (term1 + term2) / 365


def calculate_vega(S, K, T, r, sigma):
    """Calculate Vega per 1% IV change (no dividend, same for CE and PE)"""
    if T <= 0 or sigma <= 0:
        return 0

    d1, _ = calculate_d1_d2(S, K, T, r, sigma)
    return S * norm_pdf(d1) * math.sqrt(T) / 100


# ============== ALIASES FOR BACKWARD COMPATIBILITY ==============

# gex_web.py uses these names
bs_d1_d2_with_dividend = calculate_d1_d2_div
bs_price_with_dividend = bs_price_div
implied_volatility_with_dividend = implied_volatility_div
calculate_gamma_index = calculate_gamma_div
