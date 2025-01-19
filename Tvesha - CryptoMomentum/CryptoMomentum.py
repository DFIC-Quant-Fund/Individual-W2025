# region imports
from AlgorithmImports import *
from QuantConnect.DataSource import *
from QuantConnect.Data.UniverseSelection import *
# endregion


class CryptoMomentum(QCAlgorithm):
    def Initialize(self):
        self.SetStartDate(2024, 1,1)  # Set Start Date
        self.SetEndDate(2025, 1, 1)
        self.SetCash(100000)  # Set Strategy Cash

        self.SetBenchmark("SPY")
        # SET UNIVERSE BASED ON MARKET CAP - top 25 (update weekly)
        # Configure brokerage and security initializer
        self.SetBrokerageModel(BrokerageName.Kraken, AccountType.Cash)
        self.SetSecurityInitializer(BrokerageModelSecurityInitializer(self.BrokerageModel, FuncSecuritySeeder(self.GetLastKnownPrice)))

        # Universe settings 
        self.UniverseSettings.Resolution = Resolution.Daily
        self.UniverseSettings.Asynchronous = True
        # The asynchronous setting is a bool that defines whether or not LEAN can run universe selection asynchronously
        # utilizing concurrent execution to increase the speed of your algorithm.

        # Add crypto universe with a selection filter
        self.AddUniverse(CryptoUniverse.Kraken(self.UniverseSelectionFilter))
        # Indicator dictionaries 
        self.rsi = {}
        self.ema_short = {}
        self.ema_long = {}
        self.macd = {}
        self.entry_prices = {}

    def UniverseSelectionFilter(self, universe_day: List[CryptoUniverse]) -> List[Symbol]:
        # only want top 25 traded based on volume - to ensure liquidty for momentum algo 
        return [crypto.Symbol for crypto in sorted(universe_day, key=lambda x: x.VolumeInUsd, reverse=True)[:25]]

    def OnData(self, data):
        # Warm Up is a great way to prepare your algorithm and its indicators for trading.
        # if self.IsWarmingUp:
        #     return
        
        # Sell securities that are no longer in the universe
        for symbol in list(self.entry_prices.keys()):
            if symbol not in self.ActiveSecurities.Keys:
                self.Debug(f"Selling {symbol} as it is no longer in the top 25.")
                self.Liquidate(symbol)
                del self.entry_prices[symbol]

    
        for symbol in self.ActiveSecurities.Keys:
            # no data, move on
            if not data.Bars.ContainsKey(symbol):
                continue

            # Retrieve indicator values
            current_price = data.Bars[symbol].Close
            # RSI 
            rsi_value = self.rsi[symbol].Current.Value 
            # EMA
            ema_short_value = self.ema_short[symbol].Current.Value 
            ema_long_value = self.ema_long[symbol].Current.Value 
            # MACD 
            macd = self.macd[symbol]
            # The MACD line represents the distance between a shorter moving average and a longer moving average
            macd_line = macd.Current.Value
            #  9-day EMA of the MACD series
            signal_line = macd.Signal.Current.Value
            histogram = macd_line - signal_line

            # Exit Condition
            if self.entry_prices.get(symbol) is not None:  # Already holding
                if (
                    ema_short_value < ema_long_value  # Bearish crossover
                    or macd_line < signal_line and histogram < 0
# macd less than signal and negative - bear trend 
                ):
                    self.Debug(f"Selling {symbol}")
                    self.Liquidate(symbol)
                    self.entry_prices[symbol] = None

            # Entry Condition
            if (
                self.entry_prices.get(symbol) is None and  # Not already holding
                ema_short_value > ema_long_value and  # Bullish crossover
                rsi_value is not None and 55 <= rsi_value <= 65 and  # RSI in range
                macd_line > signal_line and histogram > 0
# macd more than signal and positive - bull trend 
            ):
                self.Debug(f"Buying {symbol}")
                self.SetHoldings(symbol, 0.15)  # Allocate 15% of the portfolio
                self.entry_prices[symbol] = current_price

    def OnSecuritiesChanged(self, changes: SecurityChanges):
            for security in changes.AddedSecurities:
                symbol = security.Symbol

                # Initialize indicators for the symbol
                self.rsi[symbol] = self.RSI(symbol, 14, MovingAverageType.Simple, Resolution.Daily)
                self.ema_short[symbol] = self.EMA(symbol, 12, Resolution.Daily)
                self.ema_long[symbol] = self.EMA(symbol, 26, Resolution.Daily)
                self.macd[symbol] = self.MACD(symbol, 12, 26, 9, MovingAverageType.Exponential, Resolution.Daily)
