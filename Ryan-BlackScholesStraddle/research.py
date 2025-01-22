#Black-Scholes Implied Volatility Calculation
import math
from scipy.stats import norm
from scipy.optimize import brentq
from datetime import datetime, timedelta

class OptionRight:
    Call = "call"
    Put = "put"

class OptionContract:
    def __init__(self, strike, expiry, right, bid_price, ask_price):
        self.Strike = strike
        self.Expiry = expiry
        self.Right = right
        self.BidPrice = bid_price
        self.AskPrice = ask_price

def calculate_iv(contract, underlying_price, current_time):
    market_price = (contract.BidPrice + contract.AskPrice) / 2
    if market_price <= 0:
        return None

    T = (contract.Expiry - current_time).days / 365.0
    if T <= 0:
        print("Skipping contract with non-positive time to expiry")
        return None

    def bs_price(sigma):
        d1 = (math.log(underlying_price / contract.Strike) + (0.01 + 0.5 * sigma**2) * T) / (sigma * math.sqrt(T))
        d2 = d1 - sigma * math.sqrt(T)
        if contract.Right == OptionRight.Call:
            return underlying_price * norm.cdf(d1) - contract.Strike * math.exp(-0.01 * T) * norm.cdf(d2)
        else: 
            return contract.Strike * math.exp(-0.01 * T) * norm.cdf(-d2) - underlying_price * norm.cdf(-d1)

    try:
        return brentq(lambda sigma: bs_price(sigma) - market_price, 0.01, 2)
    except ValueError:
        return None

if __name__ == "__main__":
    expiry_date = datetime.now() + timedelta(days=30)  
    current_time = datetime.now()
    option_contract = OptionContract(strike=170, expiry=expiry_date, right=OptionRight.Call, bid_price=5, ask_price=6)
    underlying_price = 175 

    iv = calculate_iv(option_contract, underlying_price, current_time)
    print(f"Calculated IV: {iv:.2%}")

# Straddle Example
import numpy as np
import matplotlib.pyplot as plt

strike_price = 100
premium_call = 2
premium_put = 2
prices = np.arange(80, 121, 1)

payoffs = [max(price - strike_price, 0) - premium_call + max(strike_price - price, 0) - premium_put for price in prices]

plt.figure(figsize=(10, 6))
plt.plot(prices, payoffs, label='Straddle Payoff')
plt.axhline(0, color='red', linestyle='--')
plt.title('Straddle Strategy Payoff at Expiration')
plt.xlabel('Stock Price at Expiration')
plt.ylabel('Profit / Loss')
plt.legend()
plt.grid(True)
plt.show()
